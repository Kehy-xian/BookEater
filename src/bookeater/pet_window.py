from __future__ import annotations

"""Small always-on-top desktop-pet shell for BookEater.

The pet exposes only diegetic player actions. Reading analysis and hidden growth remain behind
ReadingFeedService. Book context is selected once and reused for many timestamped notes.
Autonomous roaming is deliberately independent from reading traits and pauses for user actions.
"""

import queue
import sys
import threading
import uuid
from typing import Callable

from .book_choices import book_choice_map
from .game.loop import FeedOutcome
from .pet_art import GEULSSIAL_ANIMATIONS, PetPalette
from .pet_behavior import PetMotion, RoamPlanner, WorkArea
from .korean_text import has_final_consonant, named_subject, quoted_object
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime


_TRANSPARENT = '#ff00fe'
_INTERRUPT_STATES = {
    'eat', 'spit_memory', 'drop', 'snack', 'delicious', 'play', 'wash',
    'surprised', 'held', 'landed',
}


def _has_final_consonant(text: str) -> bool:
    return has_final_consonant(text)


def _quoted_with_object_particle(text: str) -> str:
    return quoted_object(text)


class DesktopPetWindow:
    def __init__(self, runtime: BookEaterRuntime):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.runtime = runtime
        self.palette = PetPalette()
        try:
            stored_scale = float(runtime.settings.get('pet_scale', '0.75') or '0.75')
            self._pet_scale = 0.45 if stored_scale == 0.5 else max(0.45, min(1.25, stored_scale))
        except (TypeError, ValueError):
            self._pet_scale = 0.75
        self._pet_window_size = max(86, round(190 * self._pet_scale))
        self.root = tk.Tk()
        self.root.title('책먹는 몬스터')
        self.root.geometry(f'{self._pet_window_size}x{self._pet_window_size}+80+80')
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg=_TRANSPARENT)
        try:
            self.root.wm_attributes('-transparentcolor', _TRANSPARENT)
        except tk.TclError:
            self.root.attributes('-alpha', 0.98)

        self.canvas = tk.Canvas(
            self.root, width=self._pet_window_size, height=self._pet_window_size, bg=_TRANSPARENT,
            highlightthickness=0, bd=0,
        )
        self.canvas.pack(fill='both', expand=True)

        self._drag_x = 0
        self._drag_y = 0
        self._dragging = False
        self._pointer_down = False
        self._press_root_x = 0
        self._press_root_y = 0
        self._single_click_job = None
        self._suppress_click_release = False
        self._pose_serial = 0
        self._menu_open = False
        self._open_panels = 0
        self._frame = 0
        self._pet_state = 'idle'
        self._busy = False
        self._tray_icon = None
        self._eat_frames = 0
        self._delicious_frames = 0
        self._show_delicious_after_eat = False
        self._result_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._book_display_to_id: dict[str, str] = {}

        # Movement is a pure state machine so it can be stress-tested without Tk.  A short initial
        # idle makes launch feel intentional before the creature begins waddling around.
        self._roam = RoamPlanner(
            step_px=6, window_width=self._pet_window_size, window_height=self._pet_window_size, margin=8,
            bond=self.runtime.care.load().bond,
        )
        self._motion = PetMotion(80, 80, state='idle', hold_ticks=14)

        self.canvas.bind('<ButtonPress-1>', self._drag_start)
        self.canvas.bind('<B1-Motion>', self._drag_move)
        self.canvas.bind('<ButtonRelease-1>', self._drag_release)
        self.canvas.bind('<Double-Button-1>', self._double_click)
        self.canvas.bind('<Button-3>', self._show_menu)

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label='기록 먹이기', command=self.open_feed_panel)
        self.menu.add_command(label='내 서재', command=self.open_library_panel)
        self.menu.add_command(label='내 몬스터 정보 보기', command=self.open_profile_panel)
        self.menu.add_command(label='휴식하기(트레이 축소)', command=self._send_home_to_tray)
        self.menu.add_separator()
        self.menu.add_command(label='종료', command=self._confirm_exit)
        self.root.protocol('WM_DELETE_WINDOW', self._confirm_exit)

        self.root.update_idletasks()
        self._sync_motion_from_window()
        self._draw()
        self.root.after(120, self._tick)
        self.root.after(70, self._roam_tick)
        self.root.after(100, self._poll_results)
        self.root.after(900, self._retry_pending_async)

    def _monster_name(self) -> str:
        return (self.runtime.settings.get('monster_name', '') or '').strip()

    def _monster_label(self) -> str:
        return self._monster_name() or '내 몬스터'

    def _monster_subject(self) -> str:
        name = self._monster_name()
        if not name:
            return '내 몬스터가'
        return named_subject(name)

    def _work_area(self) -> WorkArea:
        """Best available visible desktop work area.

        On Windows, SPI_GETWORKAREA avoids walking underneath the primary taskbar.  If that native
        call is unavailable, Tk's screen rectangle is still safe and the planner keeps a margin.
        Multi-monitor work-area refinement can be added after the first roaming playtest.
        """
        if sys.platform.startswith('win'):
            try:
                import ctypes

                class RECT(ctypes.Structure):
                    _fields_ = [
                        ('left', ctypes.c_long), ('top', ctypes.c_long),
                        ('right', ctypes.c_long), ('bottom', ctypes.c_long),
                    ]

                rect = RECT()
                if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
                    if rect.right > rect.left and rect.bottom > rect.top:
                        return WorkArea(rect.left, rect.top, rect.right, rect.bottom)
            except Exception:
                pass
        return WorkArea(0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())

    def _sync_motion_from_window(self) -> None:
        x = int(self.root.winfo_x())
        y = int(self.root.winfo_y())
        x, y = self._roam.clamp_position(x, y, self._work_area())
        self._motion = PetMotion(
            x=x,
            y=y,
            state=self._motion.state,
            target_x=self._motion.target_x,
            target_y=self._motion.target_y,
            facing=self._motion.facing,
            hold_ticks=self._motion.hold_ticks,
            vertical_direction=self._motion.vertical_direction,
        )
        self.root.geometry(f'+{x}+{y}')

    def _drag_start(self, event) -> None:
        self._pointer_down = True
        self._dragging = False
        self._drag_x = int(event.x)
        self._drag_y = int(event.y)
        self._press_root_x = int(event.x_root)
        self._press_root_y = int(event.y_root)

    def _drag_move(self, event) -> None:
        if not self._pointer_down:
            return
        distance = abs(int(event.x_root) - self._press_root_x) + abs(int(event.y_root) - self._press_root_y)
        if not self._dragging and distance < 5:
            return
        if not self._dragging:
            self._cancel_single_click()
            self._dragging = True
            self._pet_state = 'held'
        x = self.root.winfo_pointerx() - self._drag_x
        y = self.root.winfo_pointery() - self._drag_y
        self.root.geometry(f'+{x}+{y}')

    def _drag_release(self, _event) -> None:
        self._pointer_down = False
        if self._suppress_click_release:
            self._suppress_click_release = False
            self._dragging = False
            return
        if not self._dragging:
            self._schedule_single_click()
            return
        self._dragging = False
        if hasattr(self, '_intro_dropping'):
            self._intro_dropping = False
        # Bring the pet back into the work area, then let it visibly fall to the desktop floor.
        self._sync_motion_from_window()
        area = self._work_area()
        target_y = self._roam.floor_y(area)
        self._motion = PetMotion(
            self._motion.x, self._motion.y,
            state='drop', facing=self._motion.facing,
        )
        self._pet_state = 'drop'
        self._manual_drop_velocity = 3
        self._manual_drop_target_y = target_y
        self.root.after(24, self._manual_drop_step)

    def _manual_drop_step(self) -> None:
        if (
            self._pet_state != 'drop' or self._dragging or
            getattr(self, '_intro_dropping', False) or not self.root.winfo_exists()
        ):
            return
        if self._motion.y >= self._manual_drop_target_y:
            self._motion = PetMotion(
                self._motion.x, self._manual_drop_target_y,
                state='landed', facing=self._motion.facing, hold_ticks=0,
            )
            self.root.geometry(f'+{self._motion.x}+{self._motion.y}')
            self._pet_state = 'landed'
            self._pose_serial += 1
            serial = self._pose_serial
            self.root.after(520, lambda: self._finish_temporary_pose('landed', serial))
            return
        self._manual_drop_velocity = min(28, self._manual_drop_velocity + 3)
        next_y = min(self._manual_drop_target_y, self._motion.y + self._manual_drop_velocity)
        self._motion = PetMotion(
            self._motion.x, next_y, state='drop', facing=self._motion.facing,
        )
        self.root.geometry(f'+{self._motion.x}+{next_y}')
        self.root.after(24, self._manual_drop_step)

    def _cancel_single_click(self) -> None:
        if self._single_click_job is not None:
            try:
                self.root.after_cancel(self._single_click_job)
            except Exception:
                pass
            self._single_click_job = None

    def _schedule_single_click(self) -> None:
        self._cancel_single_click()
        self._single_click_job = self.root.after(260, self._show_surprised_pose)

    def _show_surprised_pose(self) -> None:
        self._single_click_job = None
        if self._dragging or self._open_panels or self._busy:
            return
        self._pet_state = 'surprised'
        self._pose_serial += 1
        serial = self._pose_serial
        self.root.after(520, lambda: self._finish_temporary_pose('surprised', serial))

    def _finish_temporary_pose(self, expected: str, serial: int) -> None:
        if self._pose_serial != serial or self._pet_state != expected:
            return
        self._pet_state = 'idle'
        self._motion = PetMotion(
            self._motion.x, self._motion.y, state='idle',
            facing=self._motion.facing, hold_ticks=8,
        )

    def _double_click(self, _event) -> None:
        self._cancel_single_click()
        self._suppress_click_release = True
        self._pointer_down = False
        self._dragging = False
        self.open_feed_panel()

    def _show_menu(self, event) -> None:
        self._menu_open = True
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()
            self._menu_open = False

    def _confirm_exit(self) -> None:
        from tkinter import messagebox
        if messagebox.askyesno(
            '책먹는 몬스터 종료',
            '책먹는 몬스터를 정말 종료할까요?',
            parent=self.root,
        ):
            if self._tray_icon is not None:
                try:
                    self._tray_icon.stop()
                except Exception:
                    pass
                self._tray_icon = None
            self.root.destroy()

    def _send_home_to_tray(self) -> None:
        """Hide without exiting and expose restore/exit actions through the system tray."""
        from tkinter import messagebox
        if self._open_panels:
            messagebox.showinfo(
                '열린 창이 있어요', '열린 창을 닫은 뒤 실행해 주세요.', parent=self.root,
            )
            return
        if self._tray_icon is not None:
            self.root.withdraw()
            return
        try:
            from PIL import Image, ImageDraw
            import pystray

            image = Image.new('RGBA', (64, 64), '#fffaf0')
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle((8, 6, 56, 58), radius=9, fill='#f4edda', outline='#29241f', width=4)
            draw.ellipse((19, 22, 27, 30), fill='#29241f')
            draw.ellipse((37, 22, 45, 30), fill='#29241f')
            draw.arc((20, 27, 44, 45), 15, 165, fill='#29241f', width=3)
            menu = pystray.Menu(
                pystray.MenuItem('바탕화면에 꺼내주기', lambda _icon, _item: self._result_queue.put(('tray_restore', None)), default=True),
                pystray.MenuItem('종료', lambda _icon, _item: self._result_queue.put(('tray_exit', None))),
            )
            self._tray_icon = pystray.Icon('BookEater', image, '책먹는 몬스터', menu)
            threading.Thread(target=self._tray_icon.run, name='bookeater-tray', daemon=True).start()
            self.root.withdraw()
            self.root.after(180, self._notify_tray_restored)
        except Exception:
            self._tray_icon = None
            messagebox.showinfo(
                '트레이 축소를 사용할 수 없어요',
                '이 환경에서는 트레이 아이콘을 만들 수 없어 작업 표시줄로 최소화했어요.',
                parent=self.root,
            )
            self.root.iconify()

    def _notify_tray_restored(self) -> None:
        if self._tray_icon is None:
            return
        try:
            self._tray_icon.notify(
                '언제든지 바탕화면에 다시 불러올 수 있어요.',
                '트레이 아이콘으로 되돌아갔어요.',
            )
            self.root.after(2000, lambda: self._tray_icon and self._tray_icon.remove_notification())
        except Exception:
            pass

    def _restore_from_tray(self) -> None:
        if self._tray_icon is not None:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
            self._tray_icon = None
        self.root.deiconify()
        self.root.lift()

    def _scale_canvas_items(self) -> None:
        if self._pet_scale != 1.0:
            self.canvas.scale('all', 0, 0, self._pet_scale, self._pet_scale)

    def _set_pet_scale(self, scale: float, *, persist: bool = True) -> None:
        self._pet_scale = max(0.45, min(1.25, float(scale)))
        self._pet_window_size = max(86, round(190 * self._pet_scale))
        if persist:
            self.runtime.settings.set('pet_scale', str(self._pet_scale))
        self._roam.window_width = self._pet_window_size
        self._roam.window_height = self._pet_window_size
        self.root.geometry(
            f'{self._pet_window_size}x{self._pet_window_size}+{self.root.winfo_x()}+{self.root.winfo_y()}'
        )
        if getattr(self, '_sprite_cache', None) is not None:
            self._sprite_cache.invalidate()
        self._sync_motion_from_window()
        self._draw()

    def _new_panel(self, title: str, geometry: str | None = None):
        """Create a tracked top-level window; roaming pauses while any player panel is open."""
        win = self.tk.Toplevel(self.root)
        win.title(title)
        win.attributes('-topmost', True)
        if geometry:
            win.geometry(geometry)
        self._open_panels += 1
        counted = True

        def released(event) -> None:
            nonlocal counted
            if event.widget is win and counted:
                counted = False
                self._open_panels = max(0, self._open_panels - 1)

        win.bind('<Destroy>', released, add='+')
        return win

    def _roam_tick(self) -> None:
        if not self.root.winfo_exists():
            return
        interrupting = self._pet_state in _INTERRUPT_STATES
        blocked = (
            self._busy or self._dragging or self._menu_open or
            self._open_panels > 0 or interrupting
        )
        previous = self._motion
        self._motion = self._roam.tick(self._motion, self._work_area(), blocked=blocked)

        if not blocked:
            if (self._motion.x, self._motion.y) != (previous.x, previous.y):
                self.root.geometry(f'+{self._motion.x}+{self._motion.y}')
            self._pet_state = self._motion.state

        self.root.after(70, self._roam_tick)

    def _tick(self) -> None:
        self._frame += 1
        if self._pet_state == 'eat':
            self._eat_frames -= 1
            if self._eat_frames <= 0 and not self._busy:
                if self._show_delicious_after_eat:
                    self._show_delicious_after_eat = False
                    self._pet_state = 'delicious'
                    self._delicious_frames = GEULSSIAL_ANIMATIONS['delicious'].frame_count
                else:
                    self._pet_state = 'idle'
                    self._motion = PetMotion(
                        self._motion.x, self._motion.y,
                        state='idle', facing=self._motion.facing, hold_ticks=8,
                    )
        elif self._pet_state == 'delicious' and self._delicious_frames > 0:
            self._delicious_frames -= 1
            if self._delicious_frames <= 0:
                self._pet_state = 'idle'
                self._motion = PetMotion(
                    self._motion.x, self._motion.y,
                    state='idle', facing=self._motion.facing, hold_ticks=8,
                )
        self._draw()
        display_state = {'run': 'walk', 'sit': 'idle'}.get(self._pet_state, self._pet_state)
        spec = GEULSSIAL_ANIMATIONS.get(display_state)
        frame_ms = 85 if self._pet_state == 'run' else (spec.frame_ms if spec is not None else 150)
        self.root.after(frame_ms, self._tick)

    def _draw(self) -> None:
        """Vector fallback renderer used until approved PNG sprite frames are integrated."""
        c = self.canvas
        c.delete('all')
        frame = self._frame
        state = self._pet_state
        eating = state == 'eat'
        walking = state == 'walk'
        sleeping = state == 'sleep'
        reading = state == 'read'
        talking = state == 'talk'
        x = 95

        if eating:
            bob = (0, -3, -5, -1, 2, -2)[frame % 6]
            squash = 5 if frame % 2 else 0
        elif walking:
            bob = (0, -2, 0, -2)[frame % 4]
            squash = 2 if frame % 2 else 0
        elif sleeping:
            bob = 2
            squash = 3
        else:
            bob = (0, 0, -1, -2, -2, -1, 0, 0)[frame % 8]
            squash = 0
        y = 90 + bob

        outline = self.palette.outline
        paper = self.palette.paper
        shadow = self.palette.paper_shadow
        ink = self.palette.ink
        bookmark = self.palette.bookmark

        shadow_w = 44 + (4 if walking or eating else 0)
        c.create_oval(x-shadow_w, 151, x+shadow_w, 160, fill='#d8d2c8', outline='')

        # Feet alternate while walking so movement reads even before sprite art is installed.
        foot_shift = 5 if walking and frame % 2 else 0
        c.create_oval(x-30-foot_shift, y+39, x-10-foot_shift, y+53, fill=shadow, outline=outline, width=2)
        c.create_oval(x+10+foot_shift, y+39, x+30+foot_shift, y+53, fill=shadow, outline=outline, width=2)

        # Bookmark tail changes side with walking direction. The approved starter art remains the
        # reference; this is only a readable movement fallback, not the final sprite.
        facing = self._motion.facing
        if facing >= 0:
            tail = (x+43, y+10, x+68, y+1, x+61, y+26, x+51, y+20)
        else:
            tail = (x-43, y+10, x-68, y+1, x-61, y+26, x-51, y+20)
        c.create_polygon(*tail, fill=bookmark, outline=outline, width=2)

        c.create_oval(
            x-52-squash, y-45+squash/2,
            x+52+squash, y+45-squash/2,
            fill=paper, outline=outline, width=3,
        )
        c.create_polygon(x-18, y-45, x+12, y-45, x+24, y-28, x-6, y-31,
                         fill='#eee5cf', outline='#c9bda4', width=1)
        c.create_line(x-21, y+21, x+20, y+21, fill='#cfc4aa')
        c.create_line(x-16, y+27, x+15, y+27, fill='#d8cdb5')

        blink = state == 'idle' and frame % 29 in {27, 28}
        if sleeping or blink:
            c.create_line(x-22, y-13, x-13, y-13, fill=ink, width=3)
            c.create_line(x+13, y-13, x+22, y-13, fill=ink, width=3)
        else:
            c.create_oval(x-22, y-17, x-14, y-9, fill=ink, outline='')
            c.create_oval(x+14, y-17, x+22, y-9, fill=ink, outline='')

        if eating:
            c.create_oval(x-23, y-2, x+23, y+29, fill=ink, outline=outline, width=2)
            for i, letter in enumerate(('가', 'A', '?')):
                phase = (frame * 10 + i * 29) % 78
                lx = x - 103 + phase
                ly = y + 5 - (i % 2) * 14
                if lx < x - 25:
                    c.create_text(lx, ly, text=letter, fill=ink, font=('', 10, 'bold'))
        elif sleeping:
            c.create_arc(x-12, y+3, x+12, y+16, start=200, extent=140, style='arc', outline=ink, width=2)
            c.create_text(x+48, y-39, text='z', fill='#71685e', font=('', 10, 'bold'))
            if frame % 2:
                c.create_text(x+59, y-50, text='Z', fill='#8b8176', font=('', 8, 'bold'))
        elif reading:
            c.create_arc(x-20, y-1, x+20, y+18, start=205, extent=130, style='arc', outline=ink, width=2)
            c.create_polygon(
                x-34, y+14, x, y+22, x+34, y+14, x+31, y+39, x, y+32, x-31, y+39,
                fill='#fffaf0', outline=outline, width=2,
            )
            c.create_line(x, y+22, x, y+32, fill='#b9aa8d')
            c.create_line(x-24, y+23, x-7, y+27, fill='#c7baa2')
            c.create_line(x+7, y+27, x+24, y+23, fill='#c7baa2')
        elif talking:
            if frame % 2:
                c.create_oval(x-8, y+1, x+8, y+15, fill=ink, outline='')
            else:
                c.create_arc(x-18, y, x+18, y+18, start=200, extent=140, style='arc', outline=ink, width=3)
            c.create_oval(x+42, y-52, x+74, y-27, fill='#fffaf0', outline='#c9bda4', width=1)
            c.create_text(x+58, y-40, text='…', fill=ink, font=('', 10, 'bold'))
        else:
            c.create_arc(x-22, y, x+22, y+21, start=200, extent=140, style='arc', outline=ink, width=3)

    def _recent_books(self):
        books = self.runtime.journal.list_books(limit=50)
        self._book_display_to_id = book_choice_map(books)
        return books

    @staticmethod
    def _date_only(value: str | None) -> str:
        if not value:
            return '아직 없음'
        text = str(value).strip()
        return text[:10] if len(text) >= 10 else text

    def open_profile_panel(self) -> None:
        tk, ttk = self.tk, self.ttk
        milestones = self.runtime.milestones.load()
        view = self.runtime.feed_service.current_view()
        win = self._new_panel('내 몬스터 정보', '380x300')
        body = ttk.Frame(win, padding=18)
        body.pack(fill='both', expand=True)

        ttk.Label(body, text=view.species or '글씨알', font=('', 18, 'bold')).pack(anchor='w')
        ttk.Label(
            body,
            text=view.tendency_hint or '아직 어떤 모습으로 자랄지 알 수 없다.',
            wraplength=335,
        ).pack(anchor='w', pady=(4, 18))

        dates = ttk.Frame(body)
        dates.pack(fill='x')
        ttk.Label(dates, text='처음 만난 날').grid(row=0, column=0, sticky='w', pady=3)
        ttk.Label(dates, text=self._date_only(milestones.met_at)).grid(row=0, column=1, sticky='w', padx=(18, 0), pady=3)
        ttk.Label(dates, text='첫 기록을 먹인 날').grid(row=1, column=0, sticky='w', pady=3)
        ttk.Label(dates, text=self._date_only(milestones.first_fed_at)).grid(row=1, column=1, sticky='w', padx=(18, 0), pady=3)

        ttk.Label(
            body,
            text='성장의 정확한 기준은 내 몬스터만 알고 있어요.',
            wraplength=335,
        ).pack(anchor='w', pady=(20, 0))

    def _register_book_dialog(self, *, on_saved: Callable[[str], None] | None = None) -> None:
        tk, ttk = self.tk, self.ttk
        win = self._new_panel('읽는 책 등록')
        body = ttk.Frame(win, padding=14)
        body.pack(fill='both', expand=True)
        title_var = tk.StringVar()
        author_var = tk.StringVar()
        msg = tk.StringVar(value='책은 한 번만 등록하면 됩니다.')

        ttk.Label(body, text='책 제목').grid(row=0, column=0, sticky='w')
        title_entry = ttk.Entry(body, textvariable=title_var, width=36)
        title_entry.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(3, 8))
        ttk.Label(body, text='저자 (선택)').grid(row=2, column=0, sticky='w')
        ttk.Entry(body, textvariable=author_var, width=36).grid(row=3, column=0, columnspan=2, sticky='ew', pady=(3, 8))
        ttk.Label(body, textvariable=msg).grid(row=4, column=0, columnspan=2, sticky='w')

        def finish(book_id: str) -> None:
            win.destroy()
            if on_saved:
                on_saved(book_id)

        def save() -> None:
            title = title_var.get().strip()
            author = author_var.get().strip()
            if not title:
                msg.set('책 제목을 입력해 주세요.')
                return
            for existing in self.runtime.journal.list_books(limit=200):
                title_same = existing.title.strip().casefold() == title.casefold()
                author_same = existing.author.strip().casefold() == author.casefold()
                if title_same and (author_same or not author):
                    finish(existing.book_id)
                    return
            book_id = uuid.uuid4().hex
            self.runtime.journal.add_book(book_id, title, author=author)
            finish(book_id)

        ttk.Button(body, text='등록', command=save).grid(row=5, column=1, sticky='e', pady=(8, 0))
        title_entry.focus_set()
        win.bind('<Return>', lambda _e: save())

    def open_feed_panel(self) -> None:
        if self._busy:
            return
        tk, ttk = self.tk, self.ttk
        books = self._recent_books()
        if not books:
            self._register_book_dialog(on_saved=lambda _bid: self.open_feed_panel())
            return
        book_choices = dict(self._book_display_to_id)

        win = self._new_panel('기록 먹이기', '470x430')
        body = ttk.Frame(win, padding=14)
        body.pack(fill='both', expand=True)

        ttk.Label(body, text='어느 책을 읽었나요?').pack(anchor='w')
        choices = list(book_choices)
        book_var = tk.StringVar(value=choices[0])
        combo = ttk.Combobox(body, textvariable=book_var, state='readonly', values=choices)
        combo.pack(fill='x', pady=(4, 8))

        def select_registered_book(book_id: str) -> None:
            self._recent_books()
            book_choices.clear()
            book_choices.update(self._book_display_to_id)
            choices = list(book_choices)
            combo.configure(values=choices)
            selected = next(
                (label for label, mapped_id in book_choices.items() if mapped_id == book_id),
                None,
            )
            if selected:
                book_var.set(selected)

        ttk.Button(
            body,
            text='새 책 등록',
            command=lambda: self._register_book_dialog(on_saved=select_registered_book),
        ).pack(anchor='e')

        row = ttk.Frame(body)
        row.pack(fill='x', pady=(8, 0))
        ttk.Label(row, text='읽은 범위 (선택)').pack(side='left')
        progress_var = tk.StringVar()
        ttk.Entry(row, textvariable=progress_var).pack(side='left', fill='x', expand=True, padx=(8, 0))

        ttk.Label(body, text='기록').pack(anchor='w', pady=(10, 0))
        note = tk.Text(body, height=10, wrap='word', undo=True)
        note.pack(fill='both', expand=True, pady=(4, 8))
        status_var = tk.StringVar(value='같은 책에 여러 번 이어서 남길 수 있어요.')
        ttk.Label(body, textvariable=status_var, wraplength=420).pack(anchor='w')

        def submit() -> None:
            if self._busy:
                return
            text = note.get('1.0', 'end').strip()
            book_id = book_choices.get(book_var.get())
            if not text:
                status_var.set('기록을 먼저 적어 주세요.')
                return
            if not book_id:
                status_var.set('책을 다시 선택해 주세요.')
                return
            feed_id = uuid.uuid4().hex
            self._busy = True
            self._pet_state = 'eat'
            self._eat_frames = 12
            win.destroy()

            def work() -> None:
                try:
                    self.runtime.journal.attach_note(
                        self.runtime.store, feed_id, text,
                        book_id=book_id, progress_text=progress_var.get().strip() or None,
                    )
                    out = self.runtime.feed_service.retry(feed_id)
                    self._result_queue.put(('feed', out))
                except Exception as exc:
                    self._result_queue.put(('error', type(exc).__name__))

            threading.Thread(target=work, name='bookeater-pet-feed', daemon=True).start()

        ttk.Button(body, text='몬스터에게 먹이기', command=submit).pack(anchor='e', pady=(8, 0))
        note.bind('<Control-Return>', lambda _e: submit())
        note.focus_set()

    def open_library_panel(self) -> None:
        tk, ttk = self.tk, self.ttk
        books = self._recent_books()
        win = self._new_panel('내 서재', '500x500')
        body = ttk.Frame(win, padding=14)
        body.pack(fill='both', expand=True)
        if not books:
            ttk.Label(body, text='아직 등록한 책이 없어요.').pack(anchor='w')
            return

        book_choices = dict(self._book_display_to_id)
        choices = list(book_choices)
        book_var = tk.StringVar(value=choices[0])
        combo = ttk.Combobox(body, textvariable=book_var, state='readonly', values=choices)
        combo.pack(fill='x')
        view = tk.Text(body, wrap='word', state='disabled')
        view.pack(fill='both', expand=True, pady=(10, 0))

        def render(*_args) -> None:
            book_id = book_choices.get(book_var.get())
            notes = self.runtime.journal.notes_for_book(book_id) if book_id else []
            view.configure(state='normal')
            view.delete('1.0', 'end')
            if not notes:
                view.insert('end', '아직 이 책에 남긴 기록이 없어요.')
            else:
                for i, item in enumerate(notes, 1):
                    progress = f' · {item.progress_text}' if item.progress_text else ''
                    view.insert('end', f'{i}. {item.created_at}{progress}\n{item.note_text}\n\n')
            view.configure(state='disabled')

        combo.bind('<<ComboboxSelected>>', render)
        render()

    def _retry_pending_async(self) -> None:
        def work() -> None:
            try:
                outcomes = self.runtime.feed_service.retry_pending(limit=25)
                self._result_queue.put(('recovery', outcomes))
            except Exception:
                pass
        threading.Thread(target=work, name='bookeater-pet-recovery', daemon=True).start()

    def _poll_results(self) -> None:
        try:
            while True:
                kind, payload = self._result_queue.get_nowait()
                if kind == 'feed':
                    outcome = payload
                    if isinstance(outcome, FeedOutcome):
                        self._busy = False
                        self._pet_state = 'eat'
                        self._eat_frames = 6
                        self._show_delicious_after_eat = True
                elif kind == 'recovery':
                    outcomes = payload if isinstance(payload, list) else []
                    if any(isinstance(x, FeedOutcome) and x.status == 'fed' for x in outcomes):
                        self._pet_state = 'eat'
                        self._eat_frames = 5
                        self._show_delicious_after_eat = True
                elif kind == 'error':
                    self._busy = False
                    self._pet_state = 'idle'
                    self._show_delicious_after_eat = False
                elif kind == 'tray_restore':
                    self._restore_from_tray()
                elif kind == 'tray_exit':
                    self._restore_from_tray()
                    self._confirm_exit()
        except queue.Empty:
            pass
        self.root.after(100, self._poll_results)

    def run(self) -> None:
        self.root.mainloop()


def run_pet(*, runtime_factory: Callable[[], BookEaterRuntime] = bootstrap_runtime) -> int:
    try:
        runtime = runtime_factory()
    except RuntimeStartupError:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        messagebox.showerror('책먹는 몬스터', '독서기록 저장 공간을 안전하게 열 수 없습니다. 기존 데이터는 변경하지 않았습니다.')
        root.destroy()
        return 2
    DesktopPetWindow(runtime).run()
    return 0
