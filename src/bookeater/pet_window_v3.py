from __future__ import annotations

"""Desktop-pet V3: collection UI plus real local memory resurfacing."""

from .pet_window_v2 import DesktopPetWindowV2
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime
from .services.memory import choose_memory


class DesktopPetWindowV3(DesktopPetWindowV2):
    def __init__(self, runtime: BookEaterRuntime):
        super().__init__(runtime)
        # Menu after V2 insertion: feed, library, encyclopedia, profile, separator, exit.
        self.menu.insert_command(4, label='기억 꺼내기', command=self.open_memory_panel)

    def open_memory_panel(self) -> None:
        ttk = self.ttk
        state = self.runtime.store.load_state()
        moment = choose_memory(self.runtime.journal, current_form=state.form_id)
        win = self._new_panel('기억 꺼내기', '470x360')
        body = ttk.Frame(win, padding=18)
        body.pack(fill='both', expand=True)

        ttk.Label(body, text='기억 한 조각', font=('', 18, 'bold')).pack(anchor='w')
        if moment is None:
            ttk.Label(
                body,
                text='아직 꺼내 보여줄 독서기록이 없어요. 책을 읽고 기록을 먹여 주면 여기서 다시 만날 수 있어요.',
                wraplength=420,
                justify='left',
            ).pack(anchor='w', pady=(14, 0))
            return

        title = moment.book_title
        if moment.author:
            title += f' — {moment.author}'
        ttk.Label(body, text=title, font=('', 12, 'bold'), wraplength=420).pack(anchor='w', pady=(12, 3))
        meta = moment.created_at[:10]
        if moment.progress_text:
            meta += f' · {moment.progress_text}'
        ttk.Label(body, text=meta).pack(anchor='w')

        quote = self.tk.Text(body, height=7, wrap='word', relief='flat', padx=10, pady=10)
        quote.insert('1.0', moment.note_text)
        quote.configure(state='disabled')
        quote.pack(fill='both', expand=True, pady=(12, 10))

        ttk.Label(
            body,
            text=moment.monster_line,
            wraplength=420,
            justify='left',
        ).pack(anchor='w')

        # A memory interaction briefly becomes a visible pet action without blocking storage.
        self._pet_state = 'spit_memory'
        self.root.after(1100, self._finish_memory_pose)

    def _finish_memory_pose(self) -> None:
        if self._pet_state == 'spit_memory':
            self._pet_state = 'idle'


def run_pet_v3(*, runtime_factory=bootstrap_runtime) -> int:
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
    DesktopPetWindowV3(runtime).run()
    return 0
