from __future__ import annotations

"""Minimal playable desktop shell for BookEater.

This module is intentionally a thin player-facing layer. It only consumes the public outcome
and public growth view returned by ReadingFeedService. Internal traits, classifier scores,
keywords, thresholds and hidden nutrition never enter UI state.
"""

from dataclasses import dataclass
import queue
import threading
import uuid
from typing import Callable

from .game.loop import FeedOutcome
from .game.presentation import PublicGrowthView
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime


@dataclass(frozen=True)
class CreatureCard:
    species: str
    stage_text: str
    hint: str


def creature_card(view: PublicGrowthView) -> CreatureCard:
    """Convert a public phenotype into the tiny amount of text the player may see."""
    stage = max(0, int(view.stage))
    return CreatureCard(
        species=str(view.species or '글씨알'),
        stage_text='아직 알 속에서 자라는 중' if stage <= 0 else f'성장 {stage}단계',
        hint=str(view.tendency_hint or '아직 어떤 모습으로 자랄지 알 수 없다.'),
    )


def _feed_id() -> str:
    return uuid.uuid4().hex


class DesktopApp:
    def __init__(self, runtime: BookEaterRuntime):
        # Import Tk only when the actual desktop shell is constructed. CI/core imports stay safe.
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.runtime = runtime
        self.root = tk.Tk()
        self.root.title('책먹는 몬스터')
        self.root.geometry('520x650')
        self.root.minsize(430, 560)

        self._result_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._busy = False
        self._build()
        self._render_growth(self.runtime.feed_service.current_view())
        self.root.after(120, self._poll_results)
        # Pending meals are retried after the window has already appeared, so a slow model load
        # cannot make startup look frozen. This remains entirely local.
        self.root.after(900, self._retry_pending_async)

    def _build(self) -> None:
        tk, ttk = self.tk, self.ttk
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill='both', expand=True)

        title = ttk.Label(outer, text='책먹는 몬스터', font=('', 20, 'bold'))
        title.pack(anchor='w')
        ttk.Label(
            outer,
            text='읽고 남긴 문장을 먹이면, 몬스터가 천천히 자기 모습으로 자랍니다.',
            wraplength=470,
        ).pack(anchor='w', pady=(4, 14))

        pet_frame = ttk.LabelFrame(outer, text='내 몬스터', padding=14)
        pet_frame.pack(fill='x')

        self.canvas = tk.Canvas(pet_frame, height=150, highlightthickness=0)
        self.canvas.pack(fill='x')
        self.canvas.bind('<Configure>', lambda _e: self._draw_placeholder())

        self.species_var = tk.StringVar(value='글씨알')
        self.stage_var = tk.StringVar(value='아직 알 속에서 자라는 중')
        self.hint_var = tk.StringVar(value='아직 어떤 모습으로 자랄지 알 수 없다.')
        ttk.Label(pet_frame, textvariable=self.species_var, font=('', 15, 'bold')).pack()
        ttk.Label(pet_frame, textvariable=self.stage_var).pack(pady=(2, 6))
        ttk.Label(pet_frame, textvariable=self.hint_var, wraplength=440, justify='center').pack()

        note_frame = ttk.LabelFrame(outer, text='오늘 남긴 독서기록', padding=12)
        note_frame.pack(fill='both', expand=True, pady=(16, 0))
        ttk.Label(
            note_frame,
            text='인상 깊었던 장면, 떠오른 질문, 확인해 본 것처럼 자유롭게 적어 주세요.',
            wraplength=445,
        ).pack(anchor='w')

        self.note = tk.Text(note_frame, height=9, wrap='word', undo=True)
        self.note.pack(fill='both', expand=True, pady=(8, 10))
        self.note.bind('<Control-Return>', lambda _e: self._submit())

        bottom = ttk.Frame(note_frame)
        bottom.pack(fill='x')
        self.status_var = tk.StringVar(value='기록을 한 조각 남겨 보세요.')
        ttk.Label(bottom, textvariable=self.status_var, wraplength=310).pack(side='left', fill='x', expand=True)
        self.feed_button = ttk.Button(bottom, text='몬스터에게 먹이기', command=self._submit)
        self.feed_button.pack(side='right', padx=(10, 0))

        ttk.Label(
            outer,
            text='Ctrl+Enter로도 먹일 수 있어요. 성장의 정확한 기준은 몬스터만 알고 있습니다.',
            wraplength=470,
        ).pack(anchor='w', pady=(10, 0))

    def _draw_placeholder(self) -> None:
        """Paper-and-ink placeholder until the first real sprite set is wired in."""
        c = self.canvas
        c.delete('pet')
        w = max(c.winfo_width(), 300)
        x, y = w / 2, 72
        # No fixed colors: use Tk theme-ish defaults and simple line art.
        c.create_oval(x-52, y-48, x+52, y+48, width=3, tags='pet')
        c.create_oval(x-21, y-12, x-14, y-5, fill='black', tags='pet')
        c.create_oval(x+14, y-12, x+21, y-5, fill='black', tags='pet')
        c.create_arc(x-26, y-5, x+26, y+28, start=200, extent=140, style='arc', width=3, tags='pet')
        c.create_line(x+48, y+8, x+72, y-5, x+66, y+20, width=3, tags='pet')
        c.create_text(x, y+62, text='…꿀꺽', tags='pet')

    def _render_growth(self, view: PublicGrowthView) -> None:
        card = creature_card(view)
        self.species_var.set(card.species)
        self.stage_var.set(card.stage_text)
        self.hint_var.set(card.hint)

    def _set_busy(self, busy: bool, message: str | None = None) -> None:
        self._busy = busy
        self.feed_button.configure(state='disabled' if busy else 'normal')
        if message is not None:
            self.status_var.set(message)

    def _submit(self) -> None:
        if self._busy:
            return
        text = self.note.get('1.0', 'end').strip()
        if not text:
            self.status_var.set('먹일 독서기록을 먼저 적어 주세요.')
            return
        feed_id = _feed_id()
        self._set_busy(True, '몬스터가 문장을 우물우물 읽는 중…')

        def work() -> None:
            try:
                outcome = self.runtime.feed_service.submit(feed_id, text)
                self._result_queue.put(('feed', outcome))
            except Exception as exc:
                # UI gets a generic local failure. Detailed internals remain local logs/store only.
                self._result_queue.put(('error', type(exc).__name__))

        threading.Thread(target=work, name='bookeater-feed', daemon=True).start()

    def _retry_pending_async(self) -> None:
        if self._busy:
            return

        def work() -> None:
            try:
                outcomes = self.runtime.feed_service.retry_pending(limit=25)
                self._result_queue.put(('recovery', outcomes))
            except Exception:
                # Recovery is best-effort. Saved notes remain pending if it cannot run now.
                pass

        threading.Thread(target=work, name='bookeater-recovery', daemon=True).start()

    def _poll_results(self) -> None:
        try:
            while True:
                kind, payload = self._result_queue.get_nowait()
                if kind == 'feed':
                    self._handle_feed(payload)  # type: ignore[arg-type]
                elif kind == 'recovery':
                    self._handle_recovery(payload)  # type: ignore[arg-type]
                elif kind == 'error':
                    self._set_busy(False, '기록은 처리하지 못했어요. 잠시 뒤 다시 시도해 주세요.')
        except queue.Empty:
            pass
        self.root.after(120, self._poll_results)

    def _handle_feed(self, outcome: FeedOutcome) -> None:
        if outcome.growth is not None:
            self._render_growth(outcome.growth)
        self.status_var.set(outcome.message)
        if outcome.status == 'fed':
            self.note.delete('1.0', 'end')
        # If pending, leave text visible so the user can see what was saved locally.
        self._set_busy(False)

    def _handle_recovery(self, outcomes: list[FeedOutcome]) -> None:
        fed = [x for x in outcomes if x.status == 'fed' and x.growth is not None]
        if fed:
            self._render_growth(fed[-1].growth)  # type: ignore[arg-type]
            self.status_var.set('전에 챙겨 둔 기록도 잘 먹었다.')

    def run(self) -> None:
        self.root.mainloop()


def run_desktop(*, runtime_factory: Callable[[], BookEaterRuntime] = bootstrap_runtime) -> int:
    """Start the desktop app and return a process-style status code."""
    try:
        runtime = runtime_factory()
    except RuntimeStartupError:
        # Import messagebox only after Tk is available; failing local storage is a hard stop because
        # silently using a temporary DB could lose the user's reading history.
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        messagebox.showerror('책먹는 몬스터', '독서기록 저장 공간을 안전하게 열 수 없습니다. 기존 데이터는 변경하지 않았습니다.')
        root.destroy()
        return 2
    DesktopApp(runtime).run()
    return 0
