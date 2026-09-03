from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.pet_art import GEULSSIAL_ANIMATIONS
from bookeater.pet_behavior import PetMotion
from bookeater.pet_window import DesktopPetWindow


class FakeRoot:
    def __init__(self):
        self.delays = []

    def after(self, delay, _callback):
        self.delays.append(delay)


def test_completed_reading_feed_flows_into_delicious_pose_then_idle():
    pet = object.__new__(DesktopPetWindow)
    pet._frame = 0
    pet._pet_state = 'eat'
    pet._eat_frames = 1
    pet._busy = False
    pet._show_delicious_after_eat = True
    pet._delicious_frames = 0
    pet._motion = PetMotion(80, 80, state='eat')
    pet.root = FakeRoot()
    pet._draw = lambda: None

    pet._tick()
    assert pet._pet_state == 'delicious'
    assert pet._delicious_frames == GEULSSIAL_ANIMATIONS['delicious'].frame_count
    assert pet.root.delays[-1] == GEULSSIAL_ANIMATIONS['delicious'].frame_ms

    for _ in range(GEULSSIAL_ANIMATIONS['delicious'].frame_count):
        pet._tick()
    assert pet._pet_state == 'idle'
    assert pet._motion.state == 'idle'
    assert pet.root.delays[-1] == GEULSSIAL_ANIMATIONS['idle'].frame_ms
