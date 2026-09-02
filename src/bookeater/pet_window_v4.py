from __future__ import annotations

"""Desktop-pet V4: real ambient dialogue on top of V3 memory/collection interactions."""

import random

from .pet_window_v3 import DesktopPetWindowV3
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime
from .services.dialogue import choose_ambient_line


class DesktopPetWindowV4(DesktopPetWindowV3):
    def __init__(self, runtime: BookEaterRuntime):
        # Base constructors render once during setup, so initialize dialogue fields first.
        self._talk_line = ''
        self._talk_cycle = -1
        self._dialogue_rng = random.Random()
        super().__init__(runtime)

    def _draw(self) -> None:
        super()._draw()
        if self._pet_state != 'talk':
            return

        # Keep one sentence stable for the whole talk pose instead of flickering every frame.
        cycle = self._frame // 12
        if cycle != self._talk_cycle or not self._talk_line:
            state = self.runtime.store.load_state()
            self._talk_line = choose_ambient_line(
                state.form_id,
                state.entry_count,
                rng=self._dialogue_rng,
            )
            self._talk_cycle = cycle

        c = self.canvas
        c.create_rectangle(8, 6, 182, 54, fill='#fffaf0', outline='#c9bda4', width=1)
        c.create_polygon(142, 54, 154, 54, 148, 64, fill='#fffaf0', outline='#c9bda4')
        c.create_text(
            95, 30,
            text=self._talk_line,
            fill=self.palette.ink,
            width=155,
            justify='center',
            font=('', 8),
        )


def run_pet_v4(*, runtime_factory=bootstrap_runtime) -> int:
    try:
        runtime = runtime_factory()
    except RuntimeStartupError:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        messagebox.showerror(
            '책먹는 몬스터',
            '독서기록 저장 공간을 안전하게 열 수 없습니다. 기존 데이터는 변경하지 않았습니다.',
        )
        root.destroy()
        return 2
    DesktopPetWindowV4(runtime).run()
    return 0
