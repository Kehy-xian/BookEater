from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.services.recommendations import BookCandidate, rank_real_candidates


class FakeAnalyzer:
    def analyze(self, text):
        if '생각' in text:
            return {'response':['사유'], 'world':[]}
        if '마음' in text:
            return {'response':['감정'], 'world':[]}
        if '우주' in text:
            return {'response':[], 'world':['상상']}
        return {}


def candidates():
    return [
        BookCandidate('1', '생각의 책', '가', '생각하고 질문하는 이야기', source='test'),
        BookCandidate('2', '마음의 책', '나', '관계와 마음의 이야기', source='test'),
        BookCandidate('3', '우주의 책', '다', '낯선 우주 세계 이야기', source='test'),
    ]


def test_taste_mode_prefers_existing_profile_axes():
    ranked = rank_real_candidates(candidates(), FakeAnalyzer(), {'사유':10,'감정':1}, mode='taste')
    assert ranked[0].candidate.source_id == '1'


def test_expand_mode_prefers_less_represented_real_candidate():
    ranked = rank_real_candidates(candidates(), FakeAnalyzer(), {'사유':10,'상상':0}, mode='expand')
    assert ranked[0].candidate.source_id in {'2','3'}


def test_output_is_strict_subset_of_supplied_candidates_and_dedupes():
    supplied = candidates() + [candidates()[0]]
    ranked = rank_real_candidates(supplied, FakeAnalyzer(), {'사유':5}, limit=10)
    supplied_ids = {c.source_id for c in supplied}
    assert {r.candidate.source_id for r in ranked} <= supplied_ids
    assert len({r.candidate.source_id for r in ranked}) == len(ranked)
    assert len(ranked) == 3


def test_blank_or_fake_candidate_cannot_enter_ranker():
    try:
        BookCandidate('', '', '')
    except ValueError:
        pass
    else:
        raise AssertionError('candidate without catalog identity should be rejected')
