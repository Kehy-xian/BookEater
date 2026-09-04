from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.pet_window import _has_final_consonant, _quoted_with_object_particle


def test_korean_name_particles_follow_final_consonant():
    assert _has_final_consonant('콩')
    assert not _has_final_consonant('두부')
    assert _quoted_with_object_particle('책') == '“책”을'
    assert _quoted_with_object_particle('소나기') == '“소나기”를'
