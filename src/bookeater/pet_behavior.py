from __future__ import annotations

"""Pure desktop-pet movement/behavior logic.

Tkinter rendering is intentionally kept out of this module so movement can be stress-tested
without opening a window.  The UI will consume these decisions to make the creature wander,
pause, read, doze and talk while remaining inside the visible desktop work area.
"""

from dataclasses import dataclass, replace
import math
import random


AMBIENT_STATES = ('idle', 'walk', 'run', 'sit', 'read', 'sleep', 'talk', 'bump')
INTERRUPT_STATES = (
    'eat', 'spit_memory', 'drop', 'snack', 'delicious', 'play', 'wash',
    'surprised', 'held', 'landed',
)


@dataclass(frozen=True)
class WorkArea:
    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self) -> None:
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError('invalid work area')


@dataclass(frozen=True)
class PetMotion:
    x: int
    y: int
    state: str = 'idle'
    target_x: int | None = None
    target_y: int | None = None
    facing: int = 1
    hold_ticks: int = 0
    vertical_direction: int = 0


class RoamPlanner:
    """Small stochastic planner with deterministic injection for tests.

    It does not move while an interaction is busy.  Ambient behavior alternates between walking
    and short pauses/activities.  The planner has no knowledge of reading traits or evolution.
    """

    def __init__(
        self,
        *,
        rng: random.Random | None = None,
        step_px: int = 5,
        window_width: int = 190,
        window_height: int = 190,
        margin: int = 8,
        bond: int = 0,
    ) -> None:
        self.rng = rng or random.Random()
        self.step_px = max(1, int(step_px))
        self.window_width = max(1, int(window_width))
        self.window_height = max(1, int(window_height))
        self.margin = max(0, int(margin))
        self.bond = max(0, min(100, int(bond)))

    def set_bond(self, bond: int) -> None:
        self.bond = max(0, min(100, int(bond)))

    def _bounds(self, area: WorkArea) -> tuple[int, int, int, int]:
        min_x = area.left + self.margin
        max_x = max(min_x, area.right - self.window_width - self.margin)
        min_y = area.top + self.margin
        max_y = max(min_y, area.bottom - self.window_height - self.margin)
        return min_x, max_x, min_y, max_y

    def clamp_position(self, x: int, y: int, area: WorkArea) -> tuple[int, int]:
        min_x, max_x, min_y, max_y = self._bounds(area)
        return (
            max(min_x, min(max_x, int(x))),
            max(min_y, min(max_y, int(y))),
        )

    def floor_y(self, area: WorkArea) -> int:
        return self._bounds(area)[3]

    def choose_walk_target(self, motion: PetMotion, area: WorkArea) -> PetMotion:
        min_x, max_x, min_y, max_y = self._bounds(area)
        # Use the whole work area so horizontal, vertical and diagonal trips all occur.
        tx = self.rng.choice((min_x, max_x)) if self.rng.random() < 0.16 else self.rng.randint(min_x, max_x)
        ty = self.rng.choice((min_y, max_y)) if self.rng.random() < 0.12 else self.rng.randint(min_y, max_y)
        dx = tx - motion.x
        dy = ty - motion.y
        facing = motion.facing if dx == 0 else (-1 if dx < 0 else 1)
        vertical = 0 if dy == 0 else (-1 if dy < 0 else 1)
        state = 'run' if self.rng.random() < (0.16 + self.bond * 0.0018) else 'walk'
        return replace(
            motion,
            state=state,
            target_x=tx,
            target_y=ty,
            facing=facing,
            vertical_direction=vertical,
            hold_ticks=0,
        )

    def choose_ambient_pause(self, motion: PetMotion) -> PetMotion:
        # Mostly idle, with occasional readable personality-building poses.
        talk_weight = 3 + round(self.bond * 0.21)
        state = self.rng.choices(
            population=('idle', 'sit', 'read', 'sleep', 'talk'),
            weights=(39, 12, 18, 11, talk_weight),
            k=1,
        )[0]
        hold = {
            'idle': self.rng.randint(7, 20),
            'sit': self.rng.randint(12, 28),
            'read': self.rng.randint(16, 34),
            'sleep': self.rng.randint(24, 48),
            'talk': self.rng.randint(8, 18),
        }[state]
        return replace(motion, state=state, target_x=None, target_y=None, hold_ticks=hold)

    def tick(self, motion: PetMotion, area: WorkArea, *, blocked: bool = False) -> PetMotion:
        x, y = self.clamp_position(motion.x, motion.y, area)
        motion = replace(motion, x=x, y=y)

        if blocked or motion.state in INTERRUPT_STATES:
            return motion

        if motion.state in {'walk', 'run'} and motion.target_x is not None and motion.target_y is not None:
            dx = motion.target_x - motion.x
            dy = motion.target_y - motion.y
            dist = math.hypot(dx, dy)
            activity_scale = 0.55 + self.bond * 0.006
            stride = self.step_px * activity_scale * (1.75 if motion.state == 'run' else 1.0)
            if dist <= stride:
                arrived = replace(
                    motion,
                    x=motion.target_x,
                    y=motion.target_y,
                    target_x=None,
                    target_y=None,
                )
                bounds = self._bounds(area)
                if arrived.x in {bounds[0], bounds[1]} or arrived.y in {bounds[2], bounds[3]}:
                    return replace(arrived, state='bump', hold_ticks=7)
                return self.choose_ambient_pause(arrived)
            scale = stride / dist
            nx = int(round(motion.x + dx * scale))
            ny = int(round(motion.y + dy * scale))
            nx, ny = self.clamp_position(nx, ny, area)
            facing = motion.facing if dx == 0 else (-1 if dx < 0 else 1)
            vertical = 0 if dy == 0 else (-1 if dy < 0 else 1)
            return replace(motion, x=nx, y=ny, facing=facing, vertical_direction=vertical)

        if motion.hold_ticks > 0:
            return replace(motion, hold_ticks=motion.hold_ticks - 1)

        # After a pause, most cycles become a short walk.  Occasionally choose another quiet pose.
        if self.rng.random() < (0.55 + self.bond * 0.0035):
            return self.choose_walk_target(motion, area)
        return self.choose_ambient_pause(motion)
