from __future__ import annotations

"""Desktop-pet V6: optional first-meeting drop animation and per-user Windows autostart."""

import threading
import webbrowser

from .pet_behavior import PetMotion
from .pet_window_v5 import DesktopPetWindowV5
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime, resource_root
from .services.update_check import configured_update_checker
from .services.windows_autostart import can_enable_autostart, is_autostart_enabled, set_autostart
from .version import APP_VERSION


class DesktopPetWindowV6(DesktopPetWindowV5):
    def __init__(self, runtime: BookEaterRuntime):
        self._drop_y = 0
        self._drop_v = 0
        self._drop_target_y = 80
        super().__init__(runtime)
        # feed, library, encyclopedia, profile, memory, separator, exit
        self.menu.insert_command(5, label='설정', command=self.open_settings_panel)
        self.root.after(220, self._maybe_start_first_drop)

    def _maybe_start_first_drop(self) -> None:
        enabled = self.runtime.settings.get_bool('intro_drop_enabled', True)
        seen = self.runtime.settings.get_bool('intro_seen', False)
        if not enabled or seen:
            if not seen:
                self.runtime.settings.set_bool('intro_seen', True)
            return

        area = self._work_area()
        target_x = max(area.left + 8, min(self._motion.x, area.right - 198))
        self._drop_target_y = max(area.top + 32, min(100, area.bottom - 240))
        self._drop_y = area.top - 200
        self._drop_v = 8
        self._pet_state = 'drop'
        self._motion = PetMotion(target_x, self._drop_y, state='drop', facing=1)
        self.root.geometry(f'+{target_x}+{self._drop_y}')
        self.root.after(35, self._drop_step)

    def _drop_step(self) -> None:
        if self._pet_state != 'drop' or not self.root.winfo_exists():
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
        self.runtime.settings.set_bool('intro_seen', True)

    def open_settings_panel(self) -> None:
        tk, ttk = self.tk, self.ttk
        win = self._new_panel('설정', '430x430')
        body = ttk.Frame(win, padding=18)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='설정', font=('', 18, 'bold')).pack(anchor='w')

        msg = tk.StringVar(value='')
        intro_var = tk.BooleanVar(value=self.runtime.settings.get_bool('intro_drop_enabled', True))

        def toggle_intro() -> None:
            self.runtime.settings.set_bool('intro_drop_enabled', bool(intro_var.get()))
            msg.set('첫 만남 연출 설정을 저장했어요.')

        ttk.Checkbutton(
            body,
            text='처음 만날 때 하늘에서 콩! 떨어지기',
            variable=intro_var,
            command=toggle_intro,
        ).pack(anchor='w', pady=(14, 5))

        def replay_next_launch() -> None:
            self.runtime.settings.set_bool('intro_seen', False)
            msg.set('다음 실행 때 첫 만남 연출을 다시 보여줄게요.')

        ttk.Button(body, text='다음 실행에 첫 만남 다시 보기', command=replay_next_launch).pack(anchor='w')

        auto_available = can_enable_autostart()
        auto_var = tk.BooleanVar(value=is_autostart_enabled() if auto_available else False)

        def toggle_autostart() -> None:
            desired = bool(auto_var.get())
            try:
                set_autostart(desired)
                self.runtime.settings.set_bool('autostart_enabled', desired)
                msg.set('Windows 자동실행 설정을 저장했어요.' if desired else 'Windows 자동실행을 껐어요.')
            except Exception:
                auto_var.set(False)
                msg.set('자동실행 설정을 변경하지 못했어요. 기존 설정은 그대로입니다.')

        auto = ttk.Checkbutton(
            body,
            text='Windows 시작 시 책먹는 몬스터도 깨우기',
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

        ttk.Separator(body).pack(fill='x', pady=(18, 10))
        update_row = ttk.Frame(body)
        update_row.pack(fill='x')
        ttk.Label(update_row, text=f'현재 버전 {APP_VERSION}').pack(side='left')
        update_url = {'value': None}

        def open_update_page() -> None:
            url = update_url['value']
            if url:
                webbrowser.open(url)

        download_button = ttk.Button(update_row, text='다운로드 페이지', command=open_update_page, state='disabled')
        download_button.pack(side='right')

        update_button = ttk.Button(body, text='업데이트 확인')
        update_button.pack(anchor='w', pady=(7, 0))

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
                update_url['value'] = result.manifest.installer_url
                download_button.configure(state='normal')
                text = f'새 버전 {result.manifest.latest_version}이 있어요.'
                if result.manifest.notes:
                    text += ' ' + result.manifest.notes[:180]
                msg.set(text)
            else:
                update_url['value'] = None
                download_button.configure(state='disabled')
                msg.set('현재 버전이 최신입니다.')

        def check_update() -> None:
            update_button.configure(state='disabled')
            download_button.configure(state='disabled')
            update_url['value'] = None
            msg.set('업데이트 정보를 확인하는 중…')
            checker = configured_update_checker(resource_root=resource_root())
            if checker is None:
                finish_update_check(None)
                return

            def work() -> None:
                try:
                    result = checker.check(current_version=APP_VERSION)
                    win.after(0, lambda: finish_update_check(result))
                except Exception:
                    win.after(0, lambda: finish_update_check(error='업데이트 정보를 확인하지 못했어요. 기존 앱은 그대로 사용할 수 있습니다.'))

            threading.Thread(target=work, name='bookeater-update-check', daemon=True).start()

        update_button.configure(command=check_update)
        ttk.Label(
            body,
            text='업데이트 확인은 버튼을 눌렀을 때만 실행되며, 앱이 스스로 설치파일을 덮어쓰지는 않습니다.',
            wraplength=380,
        ).pack(anchor='w', pady=(5, 0))

        ttk.Label(body, textvariable=msg, wraplength=380).pack(anchor='w', pady=(16, 0))


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
