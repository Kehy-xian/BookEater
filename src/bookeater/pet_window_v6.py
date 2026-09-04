from __future__ import annotations

"""Desktop-pet V6: optional first-meeting drop animation and per-user Windows autostart."""

import queue
import random
import threading

from .pet_behavior import PetMotion
from .pet_window_v5 import DesktopPetWindowV5
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime, resource_root
from .services.update_check import configured_update_checker
from .services.update_install import (
    VerifiedInstaller,
    download_verified_installer,
    launch_verified_installer,
)
from .services.birth_imprint import create_birth_imprint
from .services.catalog import configured_catalog_client
from .services.windows_autostart import can_enable_autostart, is_autostart_enabled, set_autostart
from .version import APP_VERSION
from .ui_text_flow import TYPEWRITER_DELAY_MS, space_can_advance, typewriter_prefix


class DesktopPetWindowV6(DesktopPetWindowV5):
    def __init__(self, runtime: BookEaterRuntime):
        self._intro_dropping = False
        self._drop_y = 0
        self._drop_v = 0
        self._drop_target_y = 80
        super().__init__(runtime)
        # feed, library, encyclopedia, profile, memory, separator, exit
        self.menu.insert_command(5, label='설정', command=self.open_settings_panel)
        self.root.after(220, self._maybe_start_first_drop)

    def _maybe_start_first_drop(self) -> None:
        if not self.runtime.settings.get_bool('intro_seen', False):
            self._open_birth_onboarding()
            return
        enabled = self.runtime.settings.get_bool('intro_drop_enabled', True)
        if not enabled:
            area = self._work_area()
            x, _ = self._roam.clamp_position(self._motion.x, self._motion.y, area)
            floor_y = self._roam.floor_y(area)
            self._motion = PetMotion(x, floor_y, state='idle', facing=self._motion.facing, hold_ticks=10)
            self.root.geometry(f'+{x}+{floor_y}')
            return

        area = self._work_area()
        target_x = max(area.left + 8, min(self._motion.x, area.right - self._pet_window_size - 8))
        self._drop_target_y = max(area.top + 8, area.bottom - self._pet_window_size - 8)
        self._drop_y = area.top - 200
        self._drop_v = 8
        self._intro_dropping = True
        self._pet_state = 'drop'
        self._motion = PetMotion(target_x, self._drop_y, state='drop', facing=1)
        self.root.geometry(f'+{target_x}+{self._drop_y}')
        self.root.after(35, self._drop_step)

    def _open_birth_onboarding(self) -> None:
        """Run the one-time birth ritual before exposing the roaming desktop pet."""
        tk, ttk = self.tk, self.ttk
        self.root.withdraw()
        win = tk.Toplevel(self.root)
        win.title('몬스터의 탄생')
        win.geometry('560x520')
        win.resizable(False, False)
        win.attributes('-topmost', True)
        win.protocol('WM_DELETE_WINDOW', self.root.destroy)

        canvas = tk.Canvas(win, width=560, height=330, bg='#070a22', highlightthickness=0)
        canvas.pack(fill='x')
        rng = random.Random(2718)
        for _ in range(95):
            x, y = rng.randrange(8, 552), rng.randrange(8, 322)
            radius = rng.choice((1, 1, 1, 2))
            color = rng.choice(('#ffffff', '#9fc5ff', '#d8c7ff', '#ffe8b5'))
            canvas.create_oval(x-radius, y-radius, x+radius, y+radius, fill=color, outline='')
        canvas.create_oval(175, 54, 385, 264, fill='#18204a', outline='')
        canvas.create_oval(196, 75, 364, 243, fill='#252c5e', outline='')

        egg = canvas.create_oval(
            237, 105, 323, 250, fill='#f4edda', outline='#c9bda4', width=3, tags='egg',
        )
        canvas.create_arc(
            249, 132, 311, 210, start=200, extent=140, style='arc',
            outline='#ded3ba', width=2, tags='egg',
        )
        text_var = tk.StringVar(value='')
        text = ttk.Label(win, textvariable=text_var, font=('', 13), anchor='center', justify='center')
        text.pack(fill='x', padx=28, pady=(18, 12))
        controls = ttk.Frame(win, padding=(28, 0, 28, 18))
        controls.pack(fill='both', expand=True)

        alive = {'yes': True}
        sway = {'step': 0}
        def animate_egg() -> None:
            if not alive['yes']:
                return
            phase = (-2, -1, 0, 1, 2, 1, 0, -1)[sway['step'] % 8]
            current = canvas.coords(egg)
            center = (current[0] + current[2]) / 2
            canvas.move('egg', 280 + phase - center, 0)
            sway['step'] += 1
            win.after(110, animate_egg)
        animate_egg()

        jobs: list[str] = []
        def clear_controls() -> None:
            for child in controls.winfo_children():
                child.destroy()

        advance = {'action': None}

        def run_advance(_event=None):
            focus = win.focus_get()
            if focus is not None and not space_can_advance(focus.winfo_class()):
                return None
            action = advance['action']
            if action is not None:
                advance['action'] = None
                action()
            return 'break'

        win.bind('<space>', run_advance)

        def type_text(
            message: str, done=None, *, delay: int = TYPEWRITER_DELAY_MS,
            button_text: str = '다음',
        ) -> None:
            clear_controls()
            advance['action'] = None
            text_var.set('')
            def step(index: int = 0) -> None:
                if not alive['yes']:
                    return
                # A blank visual line keeps multi-line Korean copy from feeling cramped.
                text_var.set(typewriter_prefix(message, index))
                if index <= len(message):
                    jobs.append(win.after(delay, lambda: step(index + 1)))
                elif done is not None:
                    advance['action'] = done
                    ttk.Button(controls, text=button_text, command=run_advance).pack(pady=(4, 0))
            step()

        favorite_var = tk.StringVar()
        name_var = tk.StringVar()

        def ask_favorite() -> None:
            type_text(
                '가장 좋아하는 책 이름을 이야기하면\n무언가 태어나지 않을까?',
                show_favorite_entry,
            )

        def show_favorite_entry() -> None:
            clear_controls()
            advance['action'] = None
            entry = ttk.Entry(controls, textvariable=favorite_var, font=('', 12))
            entry.pack(fill='x', pady=(4, 8))
            button = ttk.Button(controls, text='이야기하기', command=accept_favorite)
            button.pack()
            entry.bind('<Return>', lambda _event: accept_favorite())
            entry.focus_set()

        def accept_favorite() -> None:
            favorite = ' '.join(favorite_var.get().split())
            if not favorite:
                return
            clear_controls()
            self.runtime.settings.set('favorite_book_title', favorite)
            threading.Thread(
                target=lambda: create_birth_imprint(
                    self.runtime, favorite, client=configured_catalog_client(),
                ),
                name='bookeater-birth-imprint', daemon=True,
            ).start()
            type_text('이름을 붙여주세요.', show_name_entry)

        def show_name_entry() -> None:
            clear_controls()
            advance['action'] = None
            entry = ttk.Entry(controls, textvariable=name_var, font=('', 12))
            entry.pack(fill='x', pady=(4, 8))
            button = ttk.Button(controls, text='이름 붙이기', command=accept_name)
            button.pack()
            entry.bind('<Return>', lambda _event: accept_name())
            entry.focus_set()

        def accept_name() -> None:
            name = ' '.join(name_var.get().split())
            if not name or len(name) > 12:
                text_var.set('이름은 1자 이상 12자까지 붙일 수 있어요.')
                return
            self.runtime.settings.set('monster_name', name)
            clear_controls()
            glow_birth()

        def glow_birth(step: int = 0) -> None:
            if not alive['yes']:
                return
            if step < 9:
                radius = 50 + step * 13
                color = ('#fff6d5', '#ffeaa3', '#fffbe8')[step % 3]
                canvas.create_oval(280-radius, 178-radius, 280+radius, 178+radius,
                                   outline=color, width=5, tags='glow')
                canvas.tag_raise('egg')
                win.after(85, lambda: glow_birth(step + 1))
                return
            canvas.delete('glow')
            canvas.delete('egg')
            self._start_birth_idle(canvas, win, alive)
            type_text('우왓!', birth_message_one)

        def birth_message_one() -> None:
            type_text(
                '당신의 몬스터가 무사히 태어났습니다.\n당신이 읽은 책과 당신의 생각을 꾸준히 먹이면',
                birth_message_two,
            )

        def birth_message_two() -> None:
            type_text('언젠가 멋진 몬스터로 자라날 거예요.', birth_message_three)

        def birth_message_three() -> None:
            type_text('잘 돌봐주세요.', finish_birth, button_text='시작하기')

        def finish_birth() -> None:
            alive['yes'] = False
            self.runtime.settings.set_bool('intro_seen', True)
            rebuild = getattr(self, '_rebuild_main_menu', None)
            if callable(rebuild):
                rebuild()
            win.destroy()
            area = self._work_area()
            x, _ = self._roam.clamp_position(self._motion.x, self._motion.y, area)
            y = self._roam.floor_y(area)
            self._motion = PetMotion(x, y, state='idle', facing=1, hold_ticks=18)
            self._pet_state = 'idle'
            self.root.geometry(f'+{x}+{y}')
            self.root.deiconify()
            self.root.lift()

        type_text('곧 깨어날 것 같다...!', ask_favorite)

    def _draw_born_paperling(self, canvas) -> None:
        """Small vector birth illustration; the roaming window switches to production IDLE art."""
        x, y = 280, 178
        canvas.create_oval(x-51, y+52, x+51, y+66, fill='#11162f', outline='')
        canvas.create_polygon(x+41, y+4, x+70, y-8, x+60, y+27, x+49, y+21,
                              fill='#b95f55', outline='#29241f', width=2)
        canvas.create_oval(x-54, y-55, x+54, y+55, fill='#f4edda', outline='#29241f', width=3)
        canvas.create_oval(x-25, y+43, x-6, y+57, fill='#ded3ba', outline='#29241f', width=2)
        canvas.create_oval(x+6, y+43, x+25, y+57, fill='#ded3ba', outline='#29241f', width=2)
        canvas.create_oval(x-23, y-18, x-13, y-8, fill='#25211e', outline='')
        canvas.create_oval(x+13, y-18, x+23, y-8, fill='#25211e', outline='')
        canvas.create_arc(x-19, y-2, x+19, y+23, start=200, extent=140,
                          style='arc', outline='#25211e', width=3)

    def _start_birth_idle(self, canvas, win, alive: dict[str, bool]) -> None:
        """Show the same four-frame breathing animation used by the desktop pet."""
        paths = [
            resource_root() / 'resources' / 'sprites' / f'paperling_idle_{index:02d}.png'
            for index in range(4)
        ]
        try:
            images = [self.tk.PhotoImage(file=str(path)) for path in paths]
        except Exception:
            self._draw_born_paperling(canvas)
            return
        self._birth_idle_images = images
        item = canvas.create_image(280, 175, image=images[0], anchor='center')

        def animate(index: int = 0) -> None:
            if not alive['yes']:
                return
            canvas.itemconfigure(item, image=images[index % len(images)])
            win.after(420, lambda: animate(index + 1))
        animate()

    def _drop_step(self) -> None:
        if not self._intro_dropping or self._pet_state != 'drop' or not self.root.winfo_exists():
            return
        self._drop_v = min(30, self._drop_v + 3)
        self._drop_y += self._drop_v
        if self._drop_y < self._drop_target_y:
            self.root.geometry(f'+{self._motion.x}+{self._drop_y}')
            self.root.after(35, self._drop_step)
            return

        # Simple readable '콩!' landing: touch, tiny rebound, settle.
        self._drop_y = self._drop_target_y
        self.root.geometry(f'+{self._motion.x}+{self._drop_y}')
        self.canvas.create_text(95, 28, text='콩!', fill=self.palette.ink, font=('', 13, 'bold'))
        self.root.after(80, self._drop_bounce_up)

    def _drop_bounce_up(self) -> None:
        if self._pet_state != 'drop':
            return
        self.root.geometry(f'+{self._motion.x}+{self._drop_target_y - 11}')
        self.root.after(95, self._finish_first_drop)

    def _finish_first_drop(self) -> None:
        self.root.geometry(f'+{self._motion.x}+{self._drop_target_y}')
        self._motion = PetMotion(
            self._motion.x, self._drop_target_y,
            state='idle', facing=self._motion.facing, hold_ticks=18,
        )
        self._pet_state = 'idle'
        self._intro_dropping = False

    def open_settings_panel(self) -> None:
        tk, ttk = self.tk, self.ttk
        win = self._new_panel('설정', '470x550')
        body = ttk.Frame(win, padding=18)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='설정', font=('', 18, 'bold')).pack(anchor='w')

        msg = tk.StringVar(value='')
        intro_var = tk.BooleanVar(value=self.runtime.settings.get_bool('intro_drop_enabled', True))

        def toggle_intro() -> None:
            self.runtime.settings.set_bool('intro_drop_enabled', bool(intro_var.get()))
            msg.set('시작 애니메이션 설정을 저장했어요. 다음 실행에도 적용됩니다.')

        ttk.Checkbutton(
            body,
            text='시작 시 애니메이션 실행',
            variable=intro_var,
            command=toggle_intro,
        ).pack(anchor='w', pady=(14, 5))

        auto_available = can_enable_autostart()
        auto_var = tk.BooleanVar(value=is_autostart_enabled() if auto_available else False)

        def toggle_autostart() -> None:
            desired = bool(auto_var.get())
            try:
                set_autostart(desired)
                self.runtime.settings.set_bool('autostart_enabled', desired)
                msg.set('Windows 자동 실행 설정을 저장했어요.' if desired else 'Windows 자동 실행을 껐어요.')
            except Exception:
                auto_var.set(False)
                msg.set('자동 실행 설정을 변경하지 못했어요. 기존 설정은 그대로입니다.')

        auto = ttk.Checkbutton(
            body,
            text='Windows 시작 시 자동 실행',
            variable=auto_var,
            command=toggle_autostart,
        )
        auto.pack(anchor='w', pady=(18, 3))
        if not auto_available:
            auto.configure(state='disabled')
            ttk.Label(
                body,
                text='이 옵션은 Windows에 설치된 실행파일에서 사용할 수 있어요.',
                wraplength=380,
            ).pack(anchor='w')

        ttk.Label(body, text='몬스터 크기').pack(anchor='w', pady=(16, 3))
        size_var = tk.StringVar(value=str(self._pet_scale))
        size_row = ttk.Frame(body)
        size_row.pack(anchor='w')

        def change_size() -> None:
            self._set_pet_scale(float(size_var.get()))
            msg.set('몬스터 크기를 저장했어요. 다음 실행에도 적용됩니다.')

        for value, label in (
            ('1.25', '아주 크게'), ('1.0', '크게'), ('0.75', '기본'),
            ('0.6', '작게'), ('0.45', '아주 작게'),
        ):
            ttk.Radiobutton(
                size_row, text=label, value=value, variable=size_var, command=change_size,
            ).pack(side='left', padx=(0, 8))
        ttk.Label(
            body,
            text='변경한 설정은 다음 실행에도 그대로 적용됩니다.',
        ).pack(anchor='w', pady=(14, 0))

        ttk.Separator(body).pack(fill='x', pady=(18, 10))
        ttk.Label(body, text=f'현재 버전 {APP_VERSION}').pack(anchor='w')
        update_row = ttk.Frame(body)
        update_row.pack(fill='x', pady=(8, 0))
        update_manifest = {'value': None}
        update_button = ttk.Button(update_row, text='업데이트 확인')
        update_button.pack(side='left')
        download_button = ttk.Button(update_row, text='업데이트 받기', state='disabled')
        download_button.pack(side='left', padx=(6, 0))
        update_results: queue.Queue[tuple[str, object]] = queue.Queue()
        update_polling = {'active': False}

        def finish_update_check(result=None, error: str | None = None) -> None:
            try:
                if not win.winfo_exists():
                    return
            except tk.TclError:
                return
            update_button.configure(state='normal')
            if error:
                msg.set(error)
                return
            if result is None:
                msg.set('업데이트 서버가 아직 연결되지 않았어요. 현재 버전을 계속 사용할 수 있습니다.')
                return
            if result.update_available:
                update_manifest['value'] = result.manifest
                download_button.configure(state='normal')
                text = f'새 버전 {result.manifest.latest_version}이 있어요.'
                if result.manifest.notes:
                    text += ' ' + result.manifest.notes[:180]
                msg.set(text)
            else:
                update_manifest['value'] = None
                download_button.configure(state='disabled')
                msg.set('현재 버전이 최신입니다.')

        def finish_download(installer: VerifiedInstaller | None, *, error: bool = False) -> None:
            update_button.configure(state='normal')
            download_button.configure(state='normal' if update_manifest['value'] is not None else 'disabled')
            if error or installer is None:
                msg.set('설치 파일을 안전하게 받지 못했어요. 기존 앱과 데이터는 변경하지 않았습니다.')
                return
            msg.set(f'새 버전 {installer.version} 설치 파일의 SHA-256 검증을 마쳤어요.')
            from tkinter import messagebox
            install_now = messagebox.askyesno(
                '업데이트 설치 준비 완료',
                f'새 버전 {installer.version} 설치 파일을 안전하게 확인했어요.\n\n'
                '지금 설치를 시작하고 책먹는 몬스터를 종료할까요?\n'
                '독서기록과 설정은 설치 폴더 밖에 그대로 보존됩니다.',
                parent=win,
            )
            if not install_now:
                msg.set('설치 파일은 이 PC의 업데이트 폴더에 보관했어요. 나중에 다시 업데이트를 확인할 수 있습니다.')
                return
            try:
                launch_verified_installer(installer)
            except Exception:
                msg.set('설치 프로그램을 시작하지 못했어요. 기존 앱과 데이터는 그대로입니다.')
                return
            msg.set('설치 프로그램을 시작했어요. 안전한 교체를 위해 앱을 종료합니다.')
            self.root.after(250, self.root.destroy)

        def poll_update_results() -> None:
            try:
                if not win.winfo_exists():
                    update_polling['active'] = False
                    return
            except tk.TclError:
                update_polling['active'] = False
                return
            try:
                kind, payload = update_results.get_nowait()
            except queue.Empty:
                win.after(100, poll_update_results)
                return
            update_polling['active'] = False
            if kind == 'check_ok':
                finish_update_check(payload)
            elif kind == 'download_ok':
                finish_download(payload if isinstance(payload, VerifiedInstaller) else None)
            elif kind == 'download_error':
                finish_download(None, error=True)
            else:
                finish_update_check(error='업데이트 정보를 확인하지 못했어요. 기존 앱은 그대로 사용할 수 있습니다.')

        def check_update() -> None:
            update_button.configure(state='disabled')
            download_button.configure(state='disabled')
            update_manifest['value'] = None
            msg.set('업데이트 정보를 확인하는 중…')
            checker = configured_update_checker(resource_root=resource_root())
            if checker is None:
                finish_update_check(None)
                return

            def work() -> None:
                try:
                    update_results.put(('check_ok', checker.check(current_version=APP_VERSION)))
                except Exception:
                    update_results.put(('check_error', None))

            threading.Thread(target=work, name='bookeater-update-check', daemon=True).start()
            if not update_polling['active']:
                update_polling['active'] = True
                win.after(100, poll_update_results)

        def download_update() -> None:
            manifest = update_manifest['value']
            if manifest is None:
                return
            from tkinter import messagebox
            confirmed = messagebox.askyesno(
                '업데이트 다운로드',
                f'새 버전 {manifest.latest_version} 설치 파일을 받을까요?\n\n'
                '다운로드가 끝나면 SHA-256을 확인한 뒤 설치 여부를 다시 묻습니다.',
                parent=win,
            )
            if not confirmed:
                return
            update_button.configure(state='disabled')
            download_button.configure(state='disabled')
            msg.set('설치 파일을 받는 중… 완료되면 안전성 검사를 진행합니다.')

            def work() -> None:
                try:
                    verified = download_verified_installer(
                        manifest,
                        updates_dir=self.runtime.data_dir / 'updates',
                    )
                    update_results.put(('download_ok', verified))
                except Exception:
                    update_results.put(('download_error', None))

            threading.Thread(target=work, name='bookeater-update-download', daemon=True).start()
            if not update_polling['active']:
                update_polling['active'] = True
                win.after(100, poll_update_results)

        update_button.configure(command=check_update)
        download_button.configure(command=download_update)
        ttk.Label(
            body,
                text='업데이트 확인: 새 업데이트 버전이 있는지 확인\n\n'
                 '업데이트 받기: 업데이트를 수동으로 진행',
            wraplength=380,
            justify='left',
        ).pack(anchor='w', pady=(8, 0))

        ttk.Label(body, textvariable=msg, wraplength=380, justify='left').pack(anchor='w', pady=(14, 0))


def run_pet_v6(*, runtime_factory=bootstrap_runtime) -> int:
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
    DesktopPetWindowV6(runtime).run()
    return 0
