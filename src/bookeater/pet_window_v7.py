from __future__ import annotations

"""Desktop-pet V7: optional care actions and a tiny click mini-game.

Care affects only care/bond state. Reading growth remains exclusively driven by fed reading notes.
"""

import random

from .pet_window_v6 import DesktopPetWindowV6
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime


class DesktopPetWindowV7(DesktopPetWindowV6):
    def __init__(self, runtime: BookEaterRuntime):
        self._care_pose_serial = 0
        super().__init__(runtime)
        # feed, library, encyclopedia, profile, memory, settings, separator, exit
        self.menu.insert_command(5, label='돌보기', command=self.open_care_panel)

    def open_care_panel(self) -> None:
        tk, ttk = self.tk, self.ttk
        win = self._new_panel(f'{self._monster_label()} 돌보기', '470x390')
        body = ttk.Frame(win, padding=18)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text=f'{self._monster_label()} 돌보기', font=('', 18, 'bold')).pack(anchor='w')
        ttk.Label(
            body,
            text='돌보기는 기분과 친밀도만 바꾸고 독서 진화에는 영향을 주지 않아요.',
            wraplength=420,
        ).pack(anchor='w', pady=(3, 12))
        ttk.Label(
            body,
            text='친밀도는 하루 최대 5까지 오릅니다. 하루를 온전히 돌보지 않으면 이후 하루마다 2씩 내려갑니다.',
            wraplength=420,
        ).pack(anchor='w', pady=(0, 10))

        bars = ttk.Frame(body)
        bars.pack(fill='x')
        value_labels: dict[str, object] = {}
        progress: dict[str, object] = {}
        labels = (
            ('fullness', '포만감'),
            ('mood', '기분'),
            ('cleanliness', '깨끗함'),
            ('bond', '친밀도'),
        )
        for row, (key, text) in enumerate(labels):
            ttk.Label(bars, text=text, width=8).grid(row=row, column=0, sticky='w', pady=3)
            bar = ttk.Progressbar(bars, maximum=100, length=250)
            bar.grid(row=row, column=1, sticky='ew', padx=(6, 8), pady=3)
            val = ttk.Label(bars, text='0', width=4)
            val.grid(row=row, column=2, sticky='e')
            progress[key] = bar
            value_labels[key] = val
        bars.columnconfigure(1, weight=1)

        msg = tk.StringVar(value='하고 싶은 걸 골라 주세요.')

        def refresh(state=None) -> None:
            state = state or self.runtime.care.load()
            values = {
                'fullness': state.fullness,
                'mood': state.mood,
                'cleanliness': state.cleanliness,
                'bond': state.bond,
            }
            for key, value in values.items():
                progress[key]['value'] = value
                value_labels[key].configure(text=str(value))

        def care(action: str, text: str) -> None:
            state = self.runtime.care.apply(action)
            self._roam.set_bond(state.bond)
            refresh(state)
            msg.set(text)
            self._care_pose_serial += 1
            serial = self._care_pose_serial
            self._pet_state = action
            duration = {'snack': 700, 'play': 1200, 'wash': 1200}[action]
            if action == 'snack':
                self.root.after(duration, lambda: self._show_delicious_pose(serial))
            else:
                self.root.after(duration, lambda: self._care_pose_done(serial))

        buttons = ttk.Frame(body)
        buttons.pack(fill='x', pady=(14, 6))
        ttk.Button(buttons, text='간식 주기', command=lambda: care('snack', '냠! 간식은 독서기록과는 다른 맛이래요.')).pack(side='left')
        ttk.Button(buttons, text='놀아주기', command=lambda: care('play', '신나게 놀고 기분이 좋아졌어요.')).pack(side='left', padx=6)
        ttk.Button(buttons, text='씻기기', command=lambda: care('wash', '보송보송 깨끗해졌어요.')).pack(side='left')
        ttk.Button(buttons, text='글자 잡기', command=self.open_letter_game).pack(side='right')
        ttk.Label(body, textvariable=msg, wraplength=420).pack(anchor='w', pady=(8, 0))
        refresh()

    def _show_delicious_pose(self, serial: int) -> None:
        if serial != self._care_pose_serial or self._pet_state != 'snack':
            return
        self._pet_state = 'delicious'
        self.root.after(850, lambda: self._care_pose_done(serial))

    def _care_pose_done(self, serial: int | None = None) -> None:
        if serial is not None and serial != self._care_pose_serial:
            return
        if self._pet_state in {'snack', 'delicious', 'play', 'wash'}:
            self._pet_state = 'idle'

    def open_letter_game(self) -> None:
        tk, ttk = self.tk, self.ttk
        rng = random.Random()
        win = self._new_panel('미니게임 · 글자 잡기', '430x350')
        body = ttk.Frame(win, padding=12)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='도망가는 글자를 10번 눌러 주세요!', font=('', 12, 'bold')).pack(anchor='w')
        score_var = tk.StringVar(value='0 / 10')
        ttk.Label(body, textvariable=score_var).pack(anchor='w', pady=(2, 6))
        canvas = tk.Canvas(body, width=390, height=245, bg='#fffaf0', highlightthickness=1)
        canvas.pack(fill='both', expand=True)

        score = {'n': 0}
        letters = ('가', '책', 'A', '?', '★')

        def spawn() -> None:
            canvas.delete('target')
            if score['n'] >= 10:
                state = self.runtime.care.apply('minigame')
                score_var.set(f'완료! 친밀도 {state.bond}')
                canvas.create_text(195, 120, text='잡았다!\n또 놀자!', font=('', 18, 'bold'), tags='done')
                return
            x = rng.randint(35, 355)
            y = rng.randint(35, 210)
            canvas.create_oval(x-24, y-24, x+24, y+24, fill='#f4edda', outline='#29241f', width=2, tags='target')
            canvas.create_text(x, y, text=rng.choice(letters), font=('', 14, 'bold'), tags='target')
            canvas.tag_bind('target', '<Button-1>', hit)

        def hit(_event=None) -> None:
            if score['n'] >= 10:
                return
            score['n'] += 1
            score_var.set(f"{score['n']} / 10")
            spawn()

        spawn()


def run_pet_v7(*, runtime_factory=bootstrap_runtime) -> int:
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
    DesktopPetWindowV7(runtime).run()
    return 0
