from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.services.dialogue import after_feed_line, choose_ambient_line, greeting_line


def test_route_specific_ambient_voice_changes_without_exposing_labels():
    a = choose_ambient_line('route_a2', 20, rng=random.Random(1))
    b = choose_ambient_line('route_b1', 20, rng=random.Random(1))
    c = choose_ambient_line('route_c2', 20, rng=random.Random(1))
    assert len({a, b, c}) == 3
    blob = a + b + c
    for forbidden in ('사유', '탐구', '감정', '감각', '상상', '모험', '자연', '사회', '어둠', '점수'):
        assert forbidden not in blob


def test_mature_monster_can_say_more_settled_lines():
    lines = {
        choose_ambient_line('route_a1', 50, rng=random.Random(seed))
        for seed in range(30)
    }
    assert any('예전보다' in line for line in lines)


def test_after_feed_voice_follows_established_route():
    a = after_feed_line('route_a1', rng=random.Random(2))
    b = after_feed_line('route_b2', rng=random.Random(2))
    c = after_feed_line('route_c1', rng=random.Random(2))
    assert len({a, b, c}) == 3


def test_greeting_changes_with_bond():
    low = greeting_line('route_a1', 0, rng=random.Random(3))
    high = greeting_line('route_a1', 100, rng=random.Random(3))
    assert low != high
    assert any(word in low for word in ('천천히', '조용'))
    assert any(word in high for word in ('반가워', '기다리고'))
