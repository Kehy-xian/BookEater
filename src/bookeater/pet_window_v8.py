from __future__ import annotations

"""Desktop-pet V8: route-aware production sprites with lineage-safe vector fallback."""

import textwrap
from datetime import datetime, timezone

from .pet_art import GEULSSIAL_ANIMATIONS
from .pet_fallback_forms import approved_visual_form, fallback_family, fallback_variant
from .pet_sprite import TkSpriteCache
from .pet_window_v7 import DesktopPetWindowV7
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime
from .services.dialogue import choose_ambient_line, greeting_line


def dialogue_layout(text: str) -> tuple[str, int, int]:
    """Fit Korean dialogue inside the 190px pet canvas without clipping."""
    clean = ' '.join(str(text).split())
    width = 21 if len(clean) <= 42 else 18
    lines = textwrap.wrap(clean, width=width, break_long_words=True, break_on_hyphens=False) or ['']
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1][: max(1, width - 1)].rstrip() + '…'
    font_size = 8 if len(lines) <= 2 else 7
    height = 18 + len(lines) * (font_size + 4)
    return '\n'.join(lines), font_size, height


class DesktopPetWindowV8(DesktopPetWindowV7):
    def __init__(self, runtime: BookEaterRuntime):
        self._sprite_cache: TkSpriteCache | None = None
        self._visual_form_id = 'starter'
        self._visual_revision = -1
        self._away_days = 0
        previous_launch = runtime.settings.get('last_launch_at')
        if previous_launch:
            try:
                previous = datetime.fromisoformat(previous_launch)
                if previous.tzinfo is None:
                    previous = previous.replace(tzinfo=timezone.utc)
                self._away_days = max(0, (datetime.now(timezone.utc) - previous).days)
            except (TypeError, ValueError):
                pass
        runtime.settings.set('last_launch_at', datetime.now(timezone.utc).isoformat())
        super().__init__(runtime)
        self._visual_form_id = runtime.store.load_state().form_id
        resource_base = runtime.model_dir.parents[2]
        self._sprite_cache = TkSpriteCache(self.tk, resource_base)
        self.root.after(1900, self._show_launch_greeting)

    def _show_launch_greeting(self) -> None:
        if not self.runtime.settings.get_bool('intro_seen', False):
            return
        if self._busy or self._dragging or self._open_panels or self._pet_state == 'drop':
            self.root.after(700, self._show_launch_greeting)
            return
        state = self.runtime.store.load_state()
        self._talk_line = greeting_line(
            state.form_id, self.runtime.care.load().bond,
            entry_count=state.entry_count, stats=state.stats, rng=self._dialogue_rng,
            away_days=self._away_days,
        )
        self._talk_cycle = self._frame // 12
        self._pet_state = 'talk'
        self._motion = self._motion.__class__(
            self._motion.x, self._motion.y, state='talk',
            facing=self._motion.facing, hold_ticks=20,
        )

    def _refresh_visual_identity(self) -> None:
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
                bond=self.runtime.care.load().bond,
                stats=state.stats,
                rng=self._dialogue_rng,
            )
            self._talk_cycle = cycle
        c = self.canvas
        rendered, font_size, height = dialogue_layout(self._talk_line)
        bottom = min(78, 6 + height)
        c.create_rectangle(8, 6, 182, bottom, fill='#fffaf0', outline='#c9bda4', width=1)
        c.create_polygon(142, bottom, 154, bottom, 148, bottom + 10, fill='#fffaf0', outline='#c9bda4')
        c.create_text(
            95, (6 + bottom) // 2,
            text=rendered,
            fill=self.palette.ink,
            width=160,
            justify='center',
            font=('', font_size),
        )

    def _pose(self, state: str) -> tuple[int, int]:
        """Return body bob and alternating foot shift for a lightweight fallback animation."""
        frame = self._frame
        if state in {'walk', 'run'}:
            return (0, -2, 0, -2)[frame % 4], (5 if frame % 2 else -3)
        if state == 'eat':
            return (0, -3, -5, -1, 2, -2)[frame % 6], 0
        if state == 'sleep':
            return 2, 0
        if state == 'idle':
            return (0, 0, -1, -1, -2, -3, -3, -2, -1, -1, 0, 0)[frame % 12], 0
        return (0, -1, -1, 0)[frame % 4], 0

    def _draw_face(self, x: int, y: int, *, dark_face: bool, state: str) -> None:
        c = self.canvas
        ink = '#fff1c7' if dark_face else self.palette.ink
        sleeping = state == 'sleep'
        blink = state == 'idle' and self._frame % 29 in {27, 28}
        if sleeping or blink:
            c.create_line(x-16, y-8, x-8, y-8, fill=ink, width=3)
            c.create_line(x+8, y-8, x+16, y-8, fill=ink, width=3)
        else:
            c.create_oval(x-17, y-13, x-9, y-4, fill=ink, outline='')
            c.create_oval(x+9, y-13, x+17, y-4, fill=ink, outline='')

        if state == 'eat':
            c.create_oval(x-11, y+2, x+11, y+18, fill=ink, outline='')
        elif sleeping:
            c.create_arc(x-10, y+1, x+10, y+12, start=200, extent=140, style='arc', outline=ink, width=2)
        elif state == 'talk' and self._frame % 2:
            c.create_oval(x-7, y+1, x+7, y+13, fill=ink, outline='')
        else:
            c.create_arc(x-13, y, x+13, y+13, start=200, extent=140, style='arc', outline=ink, width=2)

    def _draw_action_marks(self, x: int, y: int, state: str) -> None:
        c = self.canvas
        if state == 'eat':
            for i, letter in enumerate(('가', 'A', '?')):
                phase = (self._frame * 10 + i * 29) % 72
                lx = x - 100 + phase
                ly = y + 4 - (i % 2) * 13
                if lx < x - 25:
                    c.create_text(lx, ly, text=letter, fill=self.palette.ink, font=('', 9, 'bold'))
        elif state == 'sleep':
            c.create_text(x+48, y-43, text='Z', fill='#71685e', font=('', 10, 'bold'))
        elif state == 'read':
            c.create_polygon(
                x-32, y+23, x, y+30, x+32, y+23, x+28, y+43, x, y+37, x-28, y+43,
                fill='#fffaf0', outline=self.palette.outline, width=2,
            )
            c.create_line(x, y+30, x, y+37, fill='#b9aa8d')

    def _draw_book_family(self, visual_form: str, state: str, bob: int, foot_shift: int) -> None:
        c = self.canvas
        x, y = 95, 93 + bob
        outline = self.palette.outline
        paper = self.palette.paper
        shadow = self.palette.paper_shadow
        bookmark = self.palette.bookmark
        variant = fallback_variant(visual_form)

        c.create_oval(x-46, 151, x+46, 159, fill='#d8d2c8', outline='')
        c.create_oval(x-30-foot_shift, 132, x-12-foot_shift, 145, fill=shadow, outline=outline, width=2)
        c.create_oval(x+12+foot_shift, 132, x+30+foot_shift, 145, fill=shadow, outline=outline, width=2)

        # Page block behind the cover.
        for i in range(4):
            dx = 24 + i * 5
            c.create_rectangle(x-35+dx, y-38+i, x+42+dx, y+39-i, fill='#e8dec7', outline='#baad93', width=1)
        c.create_polygon(x+18, y-48, x+31, y-58, x+43, y-47, x+38, y-27,
                         fill=bookmark, outline=outline, width=2)
        c.create_rectangle(x-43, y-42, x+39, y+42, fill=paper, outline=outline, width=3)
        c.create_line(x+31, y-36, x+31, y+36, fill='#c7baa2', width=1)

        if variant == '1':
            # Calm folded-paper hood/collar; keeps Route A face, not Route B's ink core.
            c.create_polygon(x-42, y+16, x-20, y-7, x, y+8, x+20, y-7, x+42, y+16,
                             x+32, y+42, x-32, y+42, fill='#eee5cf', outline='#c9bda4', width=1)
        elif variant == '2':
            # Approved page-ear direction.
            c.create_polygon(x-30, y-42, x-18, y-78, x-3, y-44,
                             fill='#f5edd9', outline=outline, width=2)
            c.create_polygon(x+4, y-44, x+21, y-79, x+32, y-42,
                             fill='#f5edd9', outline=outline, width=2)
            c.create_line(x-22, y-64, x-10, y-50, fill='#c7baa2')
            c.create_line(x+14, y-63, x+25, y-49, fill='#c7baa2')

        self._draw_face(x-5, y, dark_face=False, state=state)
        self._draw_action_marks(x, y, state)

    def _draw_ink_family(self, visual_form: str, state: str, bob: int, foot_shift: int) -> None:
        c = self.canvas
        x, y = 95, 94 + bob
        outline = self.palette.outline
        paper = self.palette.paper
        shadow = self.palette.paper_shadow
        bookmark = self.palette.bookmark
        variant = fallback_variant(visual_form)

        c.create_oval(x-48, 151, x+48, 159, fill='#d8d2c8', outline='')
        c.create_oval(x-31-foot_shift, 132, x-13-foot_shift, 145, fill=shadow, outline=outline, width=2)
        c.create_oval(x+13+foot_shift, 132, x+31+foot_shift, 145, fill=shadow, outline=outline, width=2)
        c.create_polygon(x+25, y-50, x+40, y-62, x+51, y-46, x+42, y-27,
                         fill=bookmark, outline=outline, width=2)

        if variant == '1':
            c.create_polygon(x-52, y-30, x-35, y-48, x, y-55, x+35, y-48, x+53, y-28,
                             x+42, y+45, x+18, y+52, x, y+43, x-18, y+52, x-43, y+45,
                             fill=paper, outline=outline, width=3)
        elif variant == '2':
            c.create_polygon(x-48, y-20, x-28, y-49, x, y-60, x+28, y-49, x+48, y-20,
                             x+43, y+44, x-43, y+44, fill=paper, outline=outline, width=3)
            c.create_line(x-33, y-22, x-33, y+28, fill='#b9aa8d', width=2)
            c.create_line(x+33, y-22, x+33, y+28, fill='#b9aa8d', width=2)
        else:
            c.create_oval(x-51, y-49, x+51, y+48, fill=paper, outline=outline, width=3)
            # Crumpled paper facets around the nest.
            for dx, dy in ((-38,-30),(-18,-44),(11,-43),(35,-28),(-43,5),(41,8),(-25,34),(23,35)):
                c.create_polygon(x+dx-8, y+dy, x+dx+2, y+dy-8, x+dx+10, y+dy+5,
                                 fill='#e8dec7', outline='#c6b99f', width=1)

        c.create_oval(x-32, y-31, x+32, y+31, fill='#292724', outline='#151413', width=2)
        self._draw_face(x, y, dark_face=True, state=state)
        self._draw_action_marks(x, y, state)

    def _draw_lantern_family(self, visual_form: str, state: str, bob: int, foot_shift: int) -> None:
        c = self.canvas
        x, y = 95, 96 + bob
        outline = self.palette.outline
        paper = self.palette.paper
        shadow = self.palette.paper_shadow
        bookmark = self.palette.bookmark
        variant = fallback_variant(visual_form)

        c.create_oval(x-48, 151, x+48, 159, fill='#d8d2c8', outline='')
        c.create_oval(x-30-foot_shift, 134, x-12-foot_shift, 147, fill=shadow, outline=outline, width=2)
        c.create_oval(x+12+foot_shift, 134, x+30+foot_shift, 147, fill=shadow, outline=outline, width=2)
        c.create_arc(x-28, y-73, x+28, y-30, start=0, extent=180, style='arc', outline='#6f6250', width=3)
        c.create_polygon(x+28, y-50, x+42, y-58, x+49, y-43, x+38, y-31,
                         fill=bookmark, outline=outline, width=2)

        if variant == '1':
            # Petal/leaf lantern evolution.
            for dx in (-48, -32, 32, 48):
                tip = -1 if dx < 0 else 1
                c.create_polygon(x+dx, y-5, x+dx+tip*20, y-28, x+dx+tip*13, y+18,
                                 fill='#f3ead5', outline='#c6b99f', width=1)
        elif variant == '2':
            # More sheltered, bookish lantern evolution.
            c.create_arc(x-42, y-54, x+42, y-12, start=0, extent=180, style='arc', outline='#b8aa91', width=3)
            c.create_line(x-41, y-33, x-48, y+31, fill='#b8aa91', width=2)
            c.create_line(x+41, y-33, x+48, y+31, fill='#b8aa91', width=2)

        c.create_polygon(x-45, y-37, x-32, y-54, x+32, y-54, x+45, y-37,
                         x+38, y+42, x-38, y+42, fill=paper, outline=outline, width=3)
        c.create_polygon(x-26, y-25, x, y-43, x+26, y-25, x+22, y+25, x, y+36, x-22, y+25,
                         fill='#292724', outline='#151413', width=2)
        # Lantern side vents.
        for side in (-1, 1):
            for dy in (-15, 4):
                c.create_rectangle(x+side*34-4, y+dy-5, x+side*34+4, y+dy+5,
                                   fill='#292724', outline='')
        self._draw_face(x, y-1, dark_face=True, state=state)
        self._draw_action_marks(x, y, state)

    def _draw_route_fallback(self, state: str) -> None:
        visual_form = approved_visual_form(self._visual_form_id)
        family = fallback_family(visual_form)
        if family == 'starter':
            super()._draw()
            return

        fallback_state = state if state in GEULSSIAL_ANIMATIONS else 'idle'
        bob, foot_shift = self._pose(fallback_state)
        self.canvas.delete('all')
        if family == 'a':
            self._draw_book_family(visual_form, fallback_state, bob, foot_shift)
        elif family == 'b':
            self._draw_ink_family(visual_form, fallback_state, bob, foot_shift)
        else:
            self._draw_lantern_family(visual_form, fallback_state, bob, foot_shift)
        self._draw_dialogue_overlay()

    def _draw_care_overlay(self, state: str) -> None:
        c = self.canvas
        if state == 'snack':
            c.create_oval(31, 111, 51, 131, fill='#d69b55', outline='#704726', width=2)
            c.create_text(41, 121, text='· ·', fill='#5a351c', font=('', 8, 'bold'))
        elif state == 'delicious':
            c.create_text(95, 35, text='맛있다!', fill=self.palette.ink, font=('', 11, 'bold'))
            c.create_arc(77, 85, 113, 113, start=190, extent=160, style='arc', outline='#29241f', width=3)
        elif state == 'play':
            c.create_text(46, 37, text='♪', fill='#d46b78', font=('', 15, 'bold'))
            c.create_text(145, 50, text='♪', fill='#678fc6', font=('', 12, 'bold'))
        elif state == 'wash':
            for index, (x, y) in enumerate(((38, 56), (54, 34), (137, 43), (153, 72), (48, 111))):
                radius = 6 + (self._frame + index) % 4
                c.create_oval(x-radius, y-radius, x+radius, y+radius, outline='#72bcd4', width=2)
        elif state == 'bump':
            vertical = self._motion.vertical_direction
            if vertical:
                x, y = 95, (28 if vertical < 0 else 158)
            else:
                side = 1 if self._motion.facing >= 0 else -1
                x, y = 95 + side * 63, 67
            c.create_text(x, y, text='콩!', fill=self.palette.ink, font=('', 12, 'bold'))
        elif state == 'surprised':
            c.create_text(145, 48, text='!', fill=self.palette.ink, font=('', 18, 'bold'))
        elif state == 'held':
            sway = (-3, 0, 3, 0)[self._frame % 4]
            c.create_line(95, 0, 95 + sway, 38, fill='#655b50', width=3)
            c.create_oval(89 + sway, 31, 101 + sway, 43, fill='#d8d2c8', outline='#655b50')
        elif state == 'landed':
            c.create_text(145, 111, text='콩!', fill=self.palette.ink, font=('', 12, 'bold'))
            c.create_arc(35, 137, 77, 157, start=190, extent=140, style='arc', outline='#8b7d69', width=2)
            c.create_arc(113, 137, 155, 157, start=210, extent=140, style='arc', outline='#8b7d69', width=2)

    def _draw(self) -> None:
        if self._sprite_cache is None:
            super()._draw()
            self._scale_canvas_items()
            return

        self._refresh_visual_identity()
        action_state = self._pet_state
        custom_action = action_state in {
            'snack', 'delicious', 'play', 'wash', 'bump', 'drop', 'surprised', 'held', 'landed',
        }
        sprite_state = {'run': 'walk', 'sit': 'idle'}.get(action_state, action_state)
        mirror = getattr(getattr(self, '_motion', None), 'facing', 1) < 0
        frames = None
        if sprite_state in GEULSSIAL_ANIMATIONS:
            frames = self._sprite_cache.frames(
                self._visual_form_id, sprite_state,
                scale=self._pet_scale, mirror=mirror,
            )
        using_custom_action_frames = bool(custom_action and frames)
        if frames is None and custom_action:
            sprite_state = 'eat' if action_state == 'snack' else 'idle'
            frames = self._sprite_cache.frames(
                self._visual_form_id, sprite_state,
                scale=self._pet_scale, mirror=mirror,
            )

        if frames:
            c = self.canvas
            c.delete('all')
            image = frames[self._frame % len(frames)]
            bounce = (
                (0, -7, -13, -5)[self._frame % 4]
                if action_state == 'play' and not using_custom_action_frames else 0
            )
            pose_y = 100 + bounce
            if action_state == 'held':
                pose_y += 12 + (-2, 0, 2, 0)[self._frame % 4]
            elif action_state == 'landed':
                pose_y += 13
            elif action_state == 'surprised':
                pose_y -= 8
            c.create_image(95, pose_y, image=image, anchor='center')
            self._draw_dialogue_overlay()
            if not using_custom_action_frames:
                self._draw_care_overlay(action_state)
            self._scale_canvas_items()
            return

        # Missing/corrupt/incomplete PNGs never crash or reveal unapproved final-form art.
        self._draw_route_fallback(sprite_state)
        self._draw_care_overlay(action_state)
        self._scale_canvas_items()


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
