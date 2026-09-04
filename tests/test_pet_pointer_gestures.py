from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.pet_behavior import PetMotion, WorkArea
from bookeater.pet_window import DesktopPetWindow


class Root:
    def __init__(self):
        self.jobs = {}
        self.next_job = 0
        self.geometry_calls = []

    def after(self, _ms, callback):
        self.next_job += 1
        self.jobs[self.next_job] = callback
        return self.next_job

    def after_cancel(self, job):
        self.jobs.pop(job, None)

    def winfo_pointerx(self): return 140
    def winfo_pointery(self): return 150
    def winfo_exists(self): return True
    def geometry(self, value): self.geometry_calls.append(value)


def pet():
    value = DesktopPetWindow.__new__(DesktopPetWindow)
    value.root = Root()
    value._pointer_down = False
    value._dragging = False
    value._drag_x = value._drag_y = 0
    value._press_root_x = value._press_root_y = 0
    value._single_click_job = None
    value._suppress_click_release = False
    value._pose_serial = 0
    value._pet_state = 'idle'
    value._open_panels = 0
    value._busy = False
    value._motion = PetMotion(20, 30)
    value._intro_dropping = False
    value._roam = SimpleNamespace(
        floor_y=lambda _area: 200,
        clamp_position=lambda x, y, _area: (x, y),
    )
    value._work_area = lambda: WorkArea(0, 0, 500, 500)
    value._sync_motion_from_window = lambda: None
    value.open_feed_panel_calls = 0
    value.open_feed_panel = lambda: setattr(value, 'open_feed_panel_calls', value.open_feed_panel_calls + 1)
    return value


def event(x=10, y=12, x_root=100, y_root=100):
    return SimpleNamespace(x=x, y=y, x_root=x_root, y_root=y_root)


def test_short_click_surprises_without_starting_drop():
    p = pet()
    p._drag_start(event())
    p._drag_release(event())
    assert not p._dragging
    assert p._pet_state == 'idle'
    callback = p.root.jobs[p._single_click_job]
    callback()
    assert p._pet_state == 'surprised'


def test_double_click_cancels_single_click_and_opens_feed_once():
    p = pet()
    p._schedule_single_click()
    p._double_click(event())
    assert p._single_click_job is None
    assert p.open_feed_panel_calls == 1


def test_drag_threshold_held_drop_and_temporary_landing():
    p = pet()
    p._drag_start(event())
    p._drag_move(event(x_root=102, y_root=101))
    assert not p._dragging
    p._drag_move(event(x_root=108, y_root=100))
    assert p._dragging and p._pet_state == 'held'
    p._drag_release(event(x_root=108, y_root=100))
    assert p._pet_state == 'drop'
    p._motion = PetMotion(20, 200, state='drop')
    p._manual_drop_step()
    assert p._pet_state == 'landed'
    callback = list(p.root.jobs.values())[-1]
    callback()
    assert p._pet_state == 'idle'
