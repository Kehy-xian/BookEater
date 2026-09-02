from __future__ import annotations

"""Local recommendation ranking over externally supplied *real* book candidates.

This module never creates a title. A catalog/search provider must supply concrete books first;
BookEater only reorders those candidates using the bundled semantic classifier and the local
aggregate reading profile. This preserves the product rule that recommendations cannot hallucinate
books.
"""

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Protocol


REACTION = ('사유', '탐구', '감정', '감각')
WORLD = ('상상', '모험', '자연', '사회', '어둠')
ALL_AXES = REACTION + WORLD


class Analyzer(Protocol):
    def analyze(self, text: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class BookCandidate:
    source_id: str
    title: str
    author: str
    description: str = ''
    detail_url: str | None = None
    cover_url: str | None = None
    source: str = 'catalog'

    def __post_init__(self) -> None:
        if not str(self.source_id).strip():
            raise ValueError('source_id is required')
        if not str(self.title).strip():
            raise ValueError('real candidate title is required')


@dataclass(frozen=True)
class RankedRecommendation:
    candidate: BookCandidate
    score: float
    mode: str


def _profile(stats: Mapping[str, float]) -> dict[str, float]:
    clean = {}
    for axis in ALL_AXES:
        try:
            clean[axis] = max(0.0, float(stats.get(axis, 0.0)))
        except (TypeError, ValueError):
            clean[axis] = 0.0
    top = max(clean.values(), default=0.0)
    if top <= 0:
        return clean
    return {axis: value / top for axis, value in clean.items()}


def _candidate_axes(analysis: Mapping[str, Any]) -> tuple[str, ...]:
    out: list[str] = []
    for key in ('response', 'world'):
        values = analysis.get(key, ())
        if isinstance(values, str):
            values = (values,)
        if isinstance(values, (list, tuple, set)):
            for value in values:
                axis = str(value)
                if axis in ALL_AXES and axis not in out:
                    out.append(axis)
    return tuple(out)


def _dedupe(candidates: Iterable[BookCandidate]) -> list[BookCandidate]:
    seen: set[tuple[str, str]] = set()
    out: list[BookCandidate] = []
    for item in candidates:
        key = (str(item.source).casefold(), str(item.source_id).casefold())
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def rank_real_candidates(
    candidates: Iterable[BookCandidate],
    analyzer: Analyzer,
    user_stats: Mapping[str, float],
    *,
    mode: str = 'taste',
    limit: int = 10,
) -> list[RankedRecommendation]:
    """Rank only the books supplied by a real catalog provider.

    taste: favor candidate axes already strong in the local reading profile.
    expand: favor meaningful axes that are less represented in the profile, while retaining a
    small familiarity component so expansion is adjacent rather than random.
    """
    if mode not in {'taste', 'expand'}:
        raise ValueError('mode must be taste or expand')
    if limit <= 0:
        return []

    profile = _profile(user_stats)
    ranked: list[tuple[float, int, BookCandidate]] = []
    for order, candidate in enumerate(_dedupe(candidates)):
        text = ' '.join(x for x in (candidate.title, candidate.author, candidate.description) if x).strip()
        try:
            raw = analyzer.analyze(text)
            analysis = raw if isinstance(raw, Mapping) else {}
        except Exception:
            analysis = {}
        axes = _candidate_axes(analysis)

        if not axes:
            score = 0.0
        else:
            familiar = sum(profile.get(axis, 0.0) for axis in axes) / len(axes)
            novelty = sum(1.0 - profile.get(axis, 0.0) for axis in axes) / len(axes)
            score = familiar if mode == 'taste' else novelty * 0.78 + familiar * 0.22
        # Stable source order breaks exact ties without manufacturing confidence.
        ranked.append((float(score), -order, candidate))

    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [
        RankedRecommendation(candidate=item[2], score=item[0], mode=mode)
        for item in ranked[: max(1, int(limit))]
    ]
