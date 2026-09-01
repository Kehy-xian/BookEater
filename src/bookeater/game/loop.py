from __future__ import annotations

"""End-to-end local reading-feed orchestration.

This is the boundary ordinary desktop UI should call. It intentionally returns only a
player-safe receipt: no trait names, weights, thresholds, classifier evidence or internal
reason strings cross this boundary.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .evolution import resolve_evolution
from .nutrition import NUTRITION_POLICY_VERSION, apply_growth_nutrition, project_growth_nutrition
from .presentation import PublicGrowthView, generic_feed_line, public_growth_view
from bookeater.storage.sqlite_store import RevisionConflict, SQLiteGameStore


PENDING_MESSAGE = '기록은 잘 챙겨뒀다. 지금은 잠깐 우물거리는 중이라 조금 뒤에 다시 먹어볼 수 있다.'


class Analyzer(Protocol):
    def analyze(self, text: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class FeedOutcome:
    feed_id: str
    status: str
    message: str
    growth: PublicGrowthView | None

    def to_public_dict(self) -> dict[str, Any]:
        # Explicit allow-list serialization is deliberate. Adding an internal field to this
        # class later must not accidentally expose it to UI or persisted public receipts.
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


class ReadingFeedService:
    """Save first, analyze second, mutate growth only in one atomic commit.

    A local-model failure therefore cannot lose the user's note. The entry stays pending and
    can be retried after restart. A duplicated click/feed id cannot grow the monster twice.
    """

    def __init__(self, store: SQLiteGameStore, analyzer: Analyzer, *, max_revision_retries: int = 5):
        self.store = store
        self.analyzer = analyzer
        self.max_revision_retries = max(1, int(max_revision_retries))

    @staticmethod
    def _pending(feed_id: str) -> FeedOutcome:
        return FeedOutcome(str(feed_id), 'pending', PENDING_MESSAGE, None)

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
                return cached

        try:
            raw = self.analyzer.analyze(note.note_text)
            analysis: Mapping[str, Any] = raw if isinstance(raw, Mapping) else {}
            nutrition = project_growth_nutrition(note.note_text, analysis)
        except Exception as exc:  # save-first policy: keep the note pending, never lose it
            self.store.mark_pending_error(note.feed_id, type(exc).__name__)
            return self._pending(note.feed_id)

        model_version = str(analysis.get('model_version', '') or '') or None
        for _ in range(self.max_revision_retries):
            state = self.store.load_state()
            next_stats = apply_growth_nutrition(state.stats, nutrition)
            next_count = state.entry_count + 1
            decision = resolve_evolution(next_stats, next_count, current_base=state.current_base)
            view = public_growth_view(decision, previous_stage=state.stage)
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
                    current_base=decision.base_trait,
                    stage=decision.stage,
                    species=decision.species,
                    stats=next_stats,
                    public_payload=payload,
                    model_version=model_version,
                    nutrition_policy=NUTRITION_POLICY_VERSION,
                )
            except RevisionConflict:
                # Another note advanced the aggregate state. Recompute phenotype from the new
                # snapshot instead of losing either meal or overwriting a concurrent update.
                continue
            cached = outcome_from_public_dict(committed)
            return cached if cached is not None else outcome

        self.store.mark_pending_error(note.feed_id, 'revision_conflict')
        return self._pending(note.feed_id)

    def current_view(self) -> PublicGrowthView:
        state = self.store.load_state()
        decision = resolve_evolution(state.stats, state.entry_count, current_base=state.current_base)
        return public_growth_view(decision, previous_stage=state.stage)

    def retry_pending(self, *, limit: int = 50) -> list[FeedOutcome]:
        outcomes: list[FeedOutcome] = []
        for feed_id in self.store.pending_feed_ids(limit=max(0, int(limit))):
            outcomes.append(self.retry(feed_id))
        return outcomes
