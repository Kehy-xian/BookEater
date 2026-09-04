from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.korean_text import named_subject, quoted_object


def test_dynamic_particles_follow_last_syllable():
    assert named_subject('콩') == '콩이가'
    assert named_subject('모모') == '모모가'
    assert quoted_object('어린 왕자') == '“어린 왕자”를'
    assert quoted_object('데미안') == '“데미안”을'
