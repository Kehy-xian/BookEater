from __future__ import annotations

"""Pure desktop-pet movement/behavior logic.

Tkinter rendering is intentionally kept out of this module so movement can be stress-tested
without opening a window.  The UI will consume these decisions to make the creature wander,
pause, read, doze and talk while remaining inside the visible desktop work area.
"""

from dataclasses import dataclass, replace
import math
import random


AMBIENT_STATES = ('idle', 'walk', 'read', 'sleep', 'talk')
INTERRUPT_STATES = ('eat', 'spit_memory', 'drop')


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
    ) -> None:
        self.rng = rng or random.Random()
        self.step_px = max(1, int(step_px))
        self.window_width = max(1, int(window_width))
        self.window_height = max(1, int(window_height))
        self.margin = max(0, int(margin))

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

    def choose_walk_target(self, motion: PetMotion, area: WorkArea) -> PetMotion:
        min_x, max_x, min_y, max_y = self._bounds(area)
        # Desktop pets feel less like teleporting windows when vertical drift is restrained.
        radius_y = min(90, max_y - min_y)
        lo_y = max(min_y, motion.y - radius_y)
        hi_y = min(max_y, motion.y + radius_y)
        tx = self.rng.randint(min_x, max_x)
        ty = self.rng.randint(lo_y, hi_y) if hi_y >= lo_y else min_y
        facing = -1 if tx < motion.x else 1
        return replace(
            motion,
            state='walk',
            target_x=tx,
            target_y=ty,
            facing=facing,
            hold_ticks=0,
        )

    def choose_ambient_pause(self, motion: PetMotion) -> PetMotion:
        # Mostly idle, with occasional readable personality-building poses.
        state = self.rng.choices(
            population=('idle', 'read', 'sleep', 'talk'),
            weights=(60, 18, 12, 10),
            k=1,
        )[0]
        hold = {
            'idle': self.rng.randint(10, 28),
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

        if motion.state == 'walk' and motion.target_x is not None and motion.target_y is not None:
            dx = motion.target_x - motion.x
            dy = motion.target_y - motion.y
            dist = math.hypot(dx, dy)
            if dist <= self.step_px:
                arrived = replace(
                    motion,
                    x=motion.target_x,
                    y=motion.target_y,
                    target_x=None,
                    target_y=None,
                )
                return self.choose_ambient_pause(arrived)
            scale = self.step_px / dist
            nx = int(round(motion.x + dx * scale))
            ny = int(round(motion.y + dy * scale))
            nx, ny = self.clamp_position(nx, ny, area)
            return replace(motion, x=nx, y=ny, facing=-1 if dx < 0 else 1)

        if motion.hold_ticks > 0:
            return replace(motion, hold_ticks=motion.hold_ticks - 1)

        # After a pause, most cycles become a short walk.  Occasionally choose another quiet pose.
        if self.rng.random() < 0.72:
            return self.choose_walk_target(motion, area)
        return self.choose_ambient_pause(motion)
