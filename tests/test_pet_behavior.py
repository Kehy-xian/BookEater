from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.pet_behavior import PetMotion, RoamPlanner, WorkArea


def test_walk_targets_and_steps_stay_inside_work_area():
    area = WorkArea(0, 0, 1280, 720)
    planner = RoamPlanner(rng=random.Random(23), step_px=7)
    motion = PetMotion(100, 100)

    for _ in range(3000):
        motion = planner.tick(motion, area)
        assert 8 <= motion.x <= 1280 - 190 - 8
        assert 8 <= motion.y <= 720 - 190 - 8


def test_walk_eventually_moves_from_starting_position():
    area = WorkArea(0, 0, 1000, 700)
    planner = RoamPlanner(rng=random.Random(7), step_px=8)
    motion = PetMotion(100, 100, state='idle', hold_ticks=0)
    positions = set()
    for _ in range(160):
        motion = planner.tick(motion, area)
        positions.add((motion.x, motion.y))
    assert len(positions) > 10
    assert 'walk' in {planner.tick(PetMotion(100, 100), area).state for _ in range(20)} or len(positions) > 10


def test_busy_interaction_freezes_autonomous_motion():
    area = WorkArea(0, 0, 1000, 700)
    planner = RoamPlanner(rng=random.Random(3))
    motion = PetMotion(250, 180, state='walk', target_x=500, target_y=200)
    frozen = planner.tick(motion, area, blocked=True)
    assert frozen.x == 250
    assert frozen.y == 180
    assert frozen.target_x == 500


def test_eat_memory_and_drop_are_never_overridden_by_roaming():
    area = WorkArea(0, 0, 1000, 700)
    planner = RoamPlanner(rng=random.Random(1))
    for state in ('eat', 'spit_memory', 'drop'):
        motion = PetMotion(300, 220, state=state)
        after = planner.tick(motion, area)
        assert after.state == state
        assert (after.x, after.y) == (300, 220)


def test_offscreen_drag_is_clamped_back_to_visible_desktop():
    area = WorkArea(100, 50, 900, 600)
    planner = RoamPlanner(rng=random.Random(2))
    motion = planner.tick(PetMotion(-500, 9999), area, blocked=True)
    assert motion.x == 108
    assert motion.y == 600 - 190 - 8
