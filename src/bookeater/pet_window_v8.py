from __future__ import annotations

"""Desktop-pet V8: route-aware production sprite rendering with safe fallback."""

from .pet_art import GEULSSIAL_ANIMATIONS
from .pet_sprite import TkSpriteCache
from .pet_window_v7 import DesktopPetWindowV7
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime
from .services.dialogue import choose_ambient_line


class DesktopPetWindowV8(DesktopPetWindowV7):
    def __init__(self, runtime: BookEaterRuntime):
        # Base constructors call _draw during setup. Keep these fields valid before super().__init__.
        self._sprite_cache: TkSpriteCache | None = None
        self._visual_form_id = 'starter'
        self._visual_revision = -1
        super().__init__(runtime)
        self._visual_form_id = runtime.store.load_state().form_id
        # model_dir = <resource_root>/resources/models/<model>; parents[2] is resource_root.
        resource_base = runtime.model_dir.parents[2]
        self._sprite_cache = TkSpriteCache(self.tk, resource_base)

    def _refresh_visual_identity(self) -> None:
        # Poll only a few times per second at most; SQLite is local but there is no reason to read it
        # on every animation frame. Feed commits update revision atomically with form_id.
        if self._frame % 8:
            return
        state = self.runtime.store.load_state()
        if state.revision == self._visual_revision:
            return
        old = self._visual_form_id
        self._visual_revision = state.revision
        self._visual_form_id = state.form_id
        if old != self._visual_form_id and self._sprite_cache is not None:
            self._sprite_cache.invalidate(old)

    def _draw_dialogue_overlay(self) -> None:
        if self._pet_state != 'talk':
            return
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

    def _draw(self) -> None:
        if self._sprite_cache is None:
            super()._draw()
            return

        self._refresh_visual_identity()
        sprite_state = self._pet_state
        if sprite_state == 'drop':
            sprite_state = 'idle'
        if sprite_state not in GEULSSIAL_ANIMATIONS:
            super()._draw()
            return

        frames = self._sprite_cache.frames(self._visual_form_id, sprite_state)
        if not frames:
            super()._draw()
            return

        # A production state is all-or-nothing: if we reached here the full frame set loaded.
        c = self.canvas
        c.delete('all')
        image = frames[self._frame % len(frames)]
        c.create_image(95, 100, image=image, anchor='center')
        self._draw_dialogue_overlay()


def run_pet_v8(*, runtime_factory=bootstrap_runtime) -> int:
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
    DesktopPetWindowV8(runtime).run()
    return 0
