from __future__ import annotations

"""Small always-on-top desktop-pet shell for BookEater.

The pet exposes only diegetic player actions. Reading analysis and hidden growth remain behind
ReadingFeedService. Book context is selected once and reused for many timestamped notes.
"""

import queue
import threading
import uuid
from typing import Callable

from .game.loop import FeedOutcome
from .pet_art import PetPalette
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime


_TRANSPARENT = '#ff00fe'


class DesktopPetWindow:
    def __init__(self, runtime: BookEaterRuntime):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.runtime = runtime
        self.palette = PetPalette()
        self.root = tk.Tk()
        self.root.title('책먹는 몬스터')
        self.root.geometry('190x190+80+80')
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg=_TRANSPARENT)
        try:
            self.root.wm_attributes('-transparentcolor', _TRANSPARENT)
        except tk.TclError:
            self.root.attributes('-alpha', 0.98)

        self.canvas = tk.Canvas(
            self.root, width=190, height=190, bg=_TRANSPARENT,
            highlightthickness=0, bd=0,
        )
        self.canvas.pack(fill='both', expand=True)

        self._drag_x = 0
        self._drag_y = 0
        self._frame = 0
        self._pet_state = 'idle'
        self._busy = False
        self._eat_frames = 0
        self._result_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._book_display_to_id: dict[str, str] = {}

        self.canvas.bind('<ButtonPress-1>', self._drag_start)
        self.canvas.bind('<B1-Motion>', self._drag_move)
        self.canvas.bind('<Double-Button-1>', lambda _e: self.open_feed_panel())
        self.canvas.bind('<Button-3>', self._show_menu)

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label='기록 먹이기', command=self.open_feed_panel)
        self.menu.add_command(label='내 책 기록', command=self.open_library_panel)
        self.menu.add_separator()
        self.menu.add_command(label='종료', command=self.root.destroy)

        self._draw()
        self.root.after(120, self._tick)
        self.root.after(100, self._poll_results)
        self.root.after(900, self._retry_pending_async)

    def _drag_start(self, event) -> None:
        self._drag_x = int(event.x)
        self._drag_y = int(event.y)

    def _drag_move(self, event) -> None:
        x = self.root.winfo_pointerx() - self._drag_x
        y = self.root.winfo_pointery() - self._drag_y
        self.root.geometry(f'+{x}+{y}')

    def _show_menu(self, event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _tick(self) -> None:
        self._frame += 1
        if self._pet_state == 'eat':
            self._eat_frames -= 1
            if self._eat_frames <= 0 and not self._busy:
                self._pet_state = 'idle'
        self._draw()
        self.root.after(115 if self._pet_state == 'eat' else 170, self._tick)

    def _draw(self) -> None:
        c = self.canvas
        c.delete('all')
        frame = self._frame
        eating = self._pet_state == 'eat'
        x = 95
        if eating:
            bob = (0, -3, -5, -1, 2, -2)[frame % 6]
            squash = 5 if frame % 2 else 0
        else:
            bob = (0, 0, -1, -2, -2, -1, 0, 0)[frame % 8]
            squash = 0
        y = 90 + bob

        outline = self.palette.outline
        paper = self.palette.paper
        shadow = self.palette.paper_shadow
        ink = self.palette.ink
        bookmark = self.palette.bookmark

        c.create_oval(x-47, 151, x+47, 160, fill='#d8d2c8', outline='')
        c.create_oval(x-30, y+39, x-10, y+53, fill=shadow, outline=outline, width=2)
        c.create_oval(x+10, y+39, x+30, y+53, fill=shadow, outline=outline, width=2)
        c.create_polygon(
            x+43, y+10, x+68, y+1, x+61, y+26, x+51, y+20,
            fill=bookmark, outline=outline, width=2,
        )
        c.create_oval(
            x-52-squash, y-45+squash/2,
            x+52+squash, y+45-squash/2,
            fill=paper, outline=outline, width=3,
        )
        c.create_line(x-21, y+21, x+20, y+21, fill='#cfc4aa')
        c.create_line(x-16, y+27, x+15, y+27, fill='#d8cdb5')

        blink = (not eating) and frame % 29 in {27, 28}
        if blink:
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
        else:
            c.create_arc(x-22, y, x+22, y+21, start=200, extent=140, style='arc', outline=ink, width=3)

    def _recent_books(self):
        books = self.runtime.journal.list_books(limit=50)
        self._book_display_to_id = {book.display_name: book.book_id for book in books}
        return books

    def _register_book_dialog(self, *, on_saved: Callable[[str], None] | None = None) -> None:
        tk, ttk = self.tk, self.ttk
        win = tk.Toplevel(self.root)
        win.title('읽는 책 등록')
        win.attributes('-topmost', True)
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

        win = tk.Toplevel(self.root)
        win.title('기록 먹이기')
        win.attributes('-topmost', True)
        win.geometry('470x430')
        body = ttk.Frame(win, padding=14)
        body.pack(fill='both', expand=True)

        ttk.Label(body, text='어느 책을 읽었나요?').pack(anchor='w')
        book_var = tk.StringVar(value=books[0].display_name)
        combo = ttk.Combobox(body, textvariable=book_var, state='readonly', values=[b.display_name for b in books])
        combo.pack(fill='x', pady=(4, 8))

        def select_registered_book(book_id: str) -> None:
            fresh = self._recent_books()
            combo.configure(values=[b.display_name for b in fresh])
            selected = next((b.display_name for b in fresh if b.book_id == book_id), None)
            if selected:
                book_var.set(selected)

        ttk.Button(
            body,
            text='새 책 등록',
            command=lambda: self._register_book_dialog(on_saved=select_registered_book),
        ).pack(anchor='e')

        row = ttk.Frame(body)
        row.pack(fill='x', pady=(8, 0))
        ttk.Label(row, text='읽은 곳 (선택)').pack(side='left')
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
            book_id = self._book_display_to_id.get(book_var.get())
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
        win = tk.Toplevel(self.root)
        win.title('내 책 기록')
        win.attributes('-topmost', True)
        win.geometry('500x500')
        body = ttk.Frame(win, padding=14)
        body.pack(fill='both', expand=True)
        if not books:
            ttk.Label(body, text='아직 등록한 책이 없어요.').pack(anchor='w')
            return

        book_var = tk.StringVar(value=books[0].display_name)
        combo = ttk.Combobox(body, textvariable=book_var, state='readonly', values=[b.display_name for b in books])
        combo.pack(fill='x')
        view = tk.Text(body, wrap='word', state='disabled')
        view.pack(fill='both', expand=True, pady=(10, 0))

        def render(*_args) -> None:
            book_id = self._book_display_to_id.get(book_var.get())
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
                elif kind == 'recovery':
                    outcomes = payload if isinstance(payload, list) else []
                    if any(isinstance(x, FeedOutcome) and x.status == 'fed' for x in outcomes):
                        self._pet_state = 'eat'
                        self._eat_frames = 5
                elif kind == 'error':
                    self._busy = False
                    self._pet_state = 'idle'
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
