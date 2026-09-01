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
        self._pet_state = 'idle'
        self._pet_frame = 0
        self._pet_state_until = 0
        self._build()
        self._render_growth(self.runtime.feed_service.current_view())
        self.root.after(80, self._animate_pet)
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

        self.canvas = tk.Canvas(
            pet_frame,
            height=168,
            highlightthickness=0,
            background='#fbfaf5',
        )
        self.canvas.pack(fill='x')
        self.canvas.bind('<Configure>', lambda _e: self._draw_pet())

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

    def _set_pet_state(self, state: str, *, hold_frames: int = 0) -> None:
        """Switch the visible creature animation without leaking hidden growth state."""
        self._pet_state = state if state in {'idle', 'eat'} else 'idle'
        self._pet_frame = 0
        self._pet_state_until = max(0, int(hold_frames))
        self._draw_pet()

    def _animate_pet(self) -> None:
        self._pet_frame += 1
        if self._pet_state == 'eat' and self._pet_state_until > 0:
            self._pet_state_until -= 1
            if self._pet_state_until == 0 and not self._busy:
                self._pet_state = 'idle'
                self._pet_frame = 0
        self._draw_pet()
        self.root.after(120 if self._pet_state == 'eat' else 170, self._animate_pet)

    def _draw_pet(self) -> None:
        """Draw the first real 글씨알 animation using lightweight vector frames.

        The creature is deliberately asset-free for this first playable build: paper body,
        ink face, bookmark tail and a tiny stream of letters while eating. Later sprite art can
        replace this renderer without changing the feed/runtime contract.
        """
        c = self.canvas
        if not c.winfo_exists():
            return
        c.delete('pet')
        w = max(c.winfo_width(), 300)
        x = w / 2
        frame = self._pet_frame
        eating = self._pet_state == 'eat'

        # Idle breath: a two-pixel paper-like bob. Eating bounces faster and slightly forward.
        if eating:
            bob_pattern = (0, -2, -4, -1, 1, -2)
            bob = bob_pattern[frame % len(bob_pattern)]
            squash = 4 if frame % 2 else 0
        else:
            bob_pattern = (0, 0, -1, -2, -2, -1, 0, 0)
            bob = bob_pattern[frame % len(bob_pattern)]
            squash = 0
        y = 78 + bob

        outline = '#29241f'
        paper = '#f4edda'
        paper_shadow = '#ded3ba'
        ink = '#25211e'
        bookmark = '#b95f55'

        # Ground shadow, feet, and bookmark tail establish the desktop-pet silhouette.
        shadow_w = 58 + (5 if eating else 0)
        c.create_oval(x-shadow_w, 134, x+shadow_w, 145, fill='#e6e1d7', outline='', tags='pet')
        c.create_oval(x-35, y+42, x-13, y+57, fill=paper_shadow, outline=outline, width=2, tags='pet')
        c.create_oval(x+13, y+42, x+35, y+57, fill=paper_shadow, outline=outline, width=2, tags='pet')
        c.create_polygon(
            x+48, y+12,
            x+76, y+2,
            x+68, y+30,
            x+56, y+23,
            fill=bookmark,
            outline=outline,
            width=2,
            tags='pet',
        )

        # Rounded paper body. Squash/stretch gives the EAT frames motion without image assets.
        c.create_oval(
            x-57-squash, y-49+squash/2,
            x+57+squash, y+49-squash/2,
            fill=paper,
            outline=outline,
            width=3,
            tags='pet',
        )

        # Faint ruled-paper marks in the belly reinforce the book/paper identity.
        c.create_line(x-24, y+23, x+22, y+23, fill='#cfc4aa', width=1, tags='pet')
        c.create_line(x-19, y+29, x+17, y+29, fill='#d8cdb5', width=1, tags='pet')

        blink = (not eating) and frame % 27 in {25, 26}
        if blink:
            c.create_line(x-24, y-14, x-14, y-14, fill=ink, width=3, tags='pet')
            c.create_line(x+14, y-14, x+24, y-14, fill=ink, width=3, tags='pet')
        else:
            c.create_oval(x-24, y-18, x-15, y-9, fill=ink, outline='', tags='pet')
            c.create_oval(x+15, y-18, x+24, y-9, fill=ink, outline='', tags='pet')

        if eating:
            mouth_open = frame % 4 in {0, 1}
            if mouth_open:
                c.create_oval(x-25, y-4, x+25, y+30, fill=ink, outline=outline, width=2, tags='pet')
                c.create_arc(x-14, y+9, x+14, y+27, start=200, extent=140, style='arc', fill=paper, width=2, tags='pet')
            else:
                c.create_arc(x-25, y+1, x+25, y+24, start=195, extent=150, style='arc', outline=ink, width=4, tags='pet')

            # Three letter crumbs travel from the left into the mouth, then disappear.
            letters = ('가', 'A', '?')
            for i, letter in enumerate(letters):
                phase = (frame * 11 + i * 31) % 86
                lx = x - 112 + phase
                ly = y + 7 - (i % 2) * 15 + ((phase // 18) % 2) * 3
                if lx < x - 27:
                    c.create_text(lx, ly, text=letter, fill=ink, font=('', 11, 'bold'), tags='pet')
            c.create_text(x, y+67, text='우물우물…', fill='#675d51', font=('', 9), tags='pet')
        else:
            c.create_arc(x-24, y-1, x+24, y+24, start=200, extent=140, style='arc', outline=ink, width=3, tags='pet')
            if frame % 18 == 0:
                c.create_text(x+47, y-38, text='·', fill='#8d8376', font=('', 14, 'bold'), tags='pet')
            c.create_text(x, y+67, text='꼼지락…', fill='#817769', font=('', 9), tags='pet')

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
        self._set_pet_state('eat')

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
                    self._set_pet_state('idle')
        except queue.Empty:
            pass
        self.root.after(120, self._poll_results)

    def _handle_feed(self, outcome: FeedOutcome) -> None:
        if outcome.growth is not None:
            self._render_growth(outcome.growth)
        self.status_var.set(outcome.message)
        # ReadingFeedService is save-first. Both 'fed' and 'pending' therefore mean this exact
        # text has already been persisted locally. Clear it to avoid a second click creating a
        # second feed id for the same pending note; recovery will retry the saved record instead.
        if outcome.status in {'fed', 'pending'}:
            self.note.delete('1.0', 'end')
        self._set_busy(False)
        # Finish one visible chew cycle before returning to the quiet idle bob.
        self._pet_state_until = 4

    def _handle_recovery(self, outcomes: list[FeedOutcome]) -> None:
        fed = [x for x in outcomes if x.status == 'fed' and x.growth is not None]
        if fed:
            self._render_growth(fed[-1].growth)  # type: ignore[arg-type]
            self.status_var.set('전에 챙겨 둔 기록도 잘 먹었다.')
            self._set_pet_state('eat', hold_frames=4)

    def run(self) -> None:
        self.root.mainloop()


def run_desktop(*, runtime_factory: Callable[[], BookEaterRuntime] = bootstrap_runtime) -> int:
    """Start the desktop app and return a process-style status code."""
    try:
        runtime = runtime_factory()
    except RuntimeStartupError:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        messagebox.showerror('책먹는 몬스터', '독서기록 저장 공간을 안전하게 열 수 없습니다. 기존 데이터는 변경하지 않았습니다.')
        root.destroy()
        return 2
    DesktopApp(runtime).run()
    return 0
