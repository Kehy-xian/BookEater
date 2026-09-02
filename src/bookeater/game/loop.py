from __future__ import annotations

"""End-to-end local reading-feed orchestration.

This is the boundary ordinary desktop UI should call. It intentionally returns only a
player-safe receipt: no trait names, weights, thresholds, classifier evidence or internal
reason strings cross this boundary.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .evolution import resolve_evolution
from .growth_route_resolver import GrowthRouteDecision, resolve_growth_route
from .growth_routes import get_growth_form, lineage_path
from .nutrition import (
    NUTRITION_POLICY_VERSION,
    GrowthNutrition,
    _bookkeeping_only,
    apply_growth_nutrition,
    project_growth_nutrition,
)
from .presentation import PublicGrowthView, generic_feed_line
from .route_presentation import route_public_growth_view
from bookeater.storage.sqlite_store import RevisionConflict, SQLiteGameStore


PENDING_MESSAGE = '기록은 잘 챙겨뒀다. 지금은 잠깐 우물거리는 중이라 조금 뒤에 다시 먹어볼 수 있다.'
RECENT_DECAY = 0.82
RECENT_FLOOR = 0.03


class Analyzer(Protocol):
    def analyze(self, text: str) -> Mapping[str, Any]: ...


class Encyclopedia(Protocol):
    def unlock(self, form_id: str): ...


@dataclass(frozen=True)
class FeedOutcome:
    feed_id: str
    status: str
    message: str
    growth: PublicGrowthView | None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            'feed_id': self.feed_id,
            'status': self.status,
            'message': self.message,
            'growth': self.growth.to_dict() if self.growth is not None else None,
        }


def _growth_from_dict(data: Mapping[str, Any] | None) -> PublicGrowthView | None:
    if not isinstance(data, Mapping):
        return None
    try:
        return PublicGrowthView(
            stage=max(0, int(data.get('stage', 0))),
            species=str(data.get('species', '글씨알')),
            visual_modifiers=tuple(str(x) for x in (data.get('visual_modifiers') or ())),
            tendency_hint=str(data.get('tendency_hint', '')),
            change_message=str(data.get('change_message', '')),
        )
    except (TypeError, ValueError):
        return None


def outcome_from_public_dict(payload: Mapping[str, Any] | None) -> FeedOutcome | None:
    if not isinstance(payload, Mapping):
        return None
    feed_id = str(payload.get('feed_id', '')).strip()
    status = str(payload.get('status', '')).strip()
    message = str(payload.get('message', ''))
    if not feed_id or status not in {'fed', 'pending'}:
        return None
    return FeedOutcome(feed_id, status, message, _growth_from_dict(payload.get('growth')))


def update_recent_signature(
    previous: Mapping[str, float] | None,
    nutrition: GrowthNutrition,
    *,
    decay: float = RECENT_DECAY,
) -> dict[str, float]:
    """Maintain a compact recent trajectory without storing per-note classifier diagnostics."""
    out: dict[str, float] = {}
    decay = min(0.99, max(0.0, float(decay)))
    for key, value in (previous or {}).items():
        try:
            decayed = max(0.0, float(value)) * decay
        except (TypeError, ValueError):
            continue
        if decayed >= RECENT_FLOOR:
            out[str(key)] = decayed
    for group in (nutrition.response, nutrition.world):
        for key, value in group.items():
            out[str(key)] = out.get(str(key), 0.0) + max(0.0, float(value))
    return out


class ReadingFeedService:
    """Save first, analyze second, mutate growth only in one atomic commit.

    The approved A/B/C route tree is now the single player-facing phenotype. The older reaction
    evolution helper remains only to preserve the hidden current_base field for compatibility with
    existing local databases; its old species names no longer drive UI or encyclopedia identity.
    """

    def __init__(
        self,
        store: SQLiteGameStore,
        analyzer: Analyzer,
        *,
        encyclopedia: Encyclopedia | None = None,
        max_revision_retries: int = 5,
    ):
        self.store = store
        self.analyzer = analyzer
        self.encyclopedia = encyclopedia
        self.max_revision_retries = max(1, int(max_revision_retries))

    @staticmethod
    def _pending(feed_id: str) -> FeedOutcome:
        return FeedOutcome(str(feed_id), 'pending', PENDING_MESSAGE, None)

    def _unlock_lineage(self, form_id: str) -> None:
        if self.encyclopedia is None:
            return
        try:
            for ancestor in lineage_path(form_id):
                self.encyclopedia.unlock(ancestor)
        except Exception:
            pass

    def submit(self, feed_id: str, note_text: str) -> FeedOutcome:
        note = self.store.record_note(feed_id, note_text)
        if note.status == 'fed':
            cached = outcome_from_public_dict(note.public_payload)
            if cached is not None:
                return cached
        return self.retry(feed_id)

    def retry(self, feed_id: str) -> FeedOutcome:
        note = self.store.get_note(feed_id)
        if note is None:
            raise KeyError(feed_id)
        if note.status == 'fed':
            cached = outcome_from_public_dict(note.public_payload)
            if cached is not None:
                self._unlock_lineage(self.store.load_state().form_id)
                return cached

        try:
            raw = self.analyzer.analyze(note.note_text)
            analysis: Mapping[str, Any] = raw if isinstance(raw, Mapping) else {}
            nutrition = project_growth_nutrition(note.note_text, analysis)
        except Exception as exc:
            self.store.mark_pending_error(note.feed_id, type(exc).__name__)
            return self._pending(note.feed_id)

        model_version = str(analysis.get('model_version', '') or '') or None
        for _ in range(self.max_revision_retries):
            state = self.store.load_state()
            next_stats = apply_growth_nutrition(state.stats, nutrition)
            is_bookkeeping = _bookkeeping_only(note.note_text)
            next_count = state.entry_count + (0 if is_bookkeeping else 1)
            next_recent = (
                dict(state.recent_stats)
                if is_bookkeeping
                else update_recent_signature(state.recent_stats, nutrition)
            )

            # Preserve only the legacy hidden base pointer; all public identity comes from routes.
            legacy = resolve_evolution(next_stats, next_count, current_base=state.current_base)
            route_decision = resolve_growth_route(
                next_stats,
                next_count,
                recent_stats=next_recent,
                current_form=state.form_id,
            )
            view = route_public_growth_view(
                route_decision,
                next_stats,
                previous_form=state.form_id,
            )
            outcome = FeedOutcome(
                note.feed_id,
                'fed',
                generic_feed_line(note.feed_id),
                view,
            )
            payload = outcome.to_public_dict()
            try:
                committed = self.store.commit_fed(
                    feed_id=note.feed_id,
                    expected_revision=state.revision,
                    entry_count=next_count,
                    current_base=legacy.base_trait,
                    stage=route_decision.tier,
                    species=view.species,
                    stats=next_stats,
                    public_payload=payload,
                    model_version=model_version,
                    nutrition_policy=NUTRITION_POLICY_VERSION,
                    form_id=route_decision.form_id,
                    recent_stats=next_recent,
                )
            except RevisionConflict:
                continue
            self._unlock_lineage(route_decision.form_id)
            cached = outcome_from_public_dict(committed)
            return cached if cached is not None else outcome

        self.store.mark_pending_error(note.feed_id, 'revision_conflict')
        return self._pending(note.feed_id)

    def current_view(self) -> PublicGrowthView:
        state = self.store.load_state()
        form = get_growth_form(state.form_id)
        decision = GrowthRouteDecision(
            form_id=form.form_id,
            tier=form.tier,
            delayed=False,
            internal_reason='persisted current route',
        )
        return route_public_growth_view(decision, state.stats, previous_form=state.form_id)

    def retry_pending(self, *, limit: int = 50) -> list[FeedOutcome]:
        outcomes: list[FeedOutcome] = []
        for feed_id in self.store.pending_feed_ids(limit=max(0, int(limit))):
            outcomes.append(self.retry(feed_id))
        return outcomes
