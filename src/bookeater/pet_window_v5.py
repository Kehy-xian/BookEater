from __future__ import annotations

"""Desktop-pet V5: practical bookshelf UI on top of dialogue, memory and encyclopedia."""

from .pet_window_v4 import DesktopPetWindowV4
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime


_STATUS_LABELS = {
    'reading': '읽는 중',
    'completed': '완독',
    'wishlist': '읽고 싶음',
    'paused': '잠시 멈춤',
}


class DesktopPetWindowV5(DesktopPetWindowV4):
    def open_library_panel(self) -> None:
        tk, ttk = self.tk, self.ttk
        win = self._new_panel('내 서재', '760x520')
        body = ttk.Frame(win, padding=14)
        body.pack(fill='both', expand=True)

        header = ttk.Frame(body)
        header.pack(fill='x')
        ttk.Label(header, text='내 서재', font=('', 18, 'bold')).pack(side='left')
        ttk.Button(
            header,
            text='새 책 등록',
            command=lambda: self._register_book_dialog(on_saved=lambda _id: refresh_books()),
        ).pack(side='right')

        content = ttk.Panedwindow(body, orient='horizontal')
        content.pack(fill='both', expand=True, pady=(10, 8))
        left = ttk.Frame(content, padding=(0, 0, 8, 0))
        right = ttk.Frame(content, padding=(8, 0, 0, 0))
        content.add(left, weight=2)
        content.add(right, weight=3)

        tree = ttk.Treeview(left, columns=('title','author','status'), show='headings', selectmode='browse')
        tree.heading('title', text='책')
        tree.heading('author', text='저자')
        tree.heading('status', text='상태')
        tree.column('title', width=220, anchor='w')
        tree.column('author', width=110, anchor='w')
        tree.column('status', width=80, anchor='center')
        tree.pack(fill='both', expand=True)

        ttk.Label(right, text='이 책에 남긴 기록', font=('', 11, 'bold')).pack(anchor='w')
        notes_view = tk.Text(right, wrap='word', state='disabled', padx=8, pady=8)
        notes_view.pack(fill='both', expand=True, pady=(6, 0))

        status_bar = ttk.Frame(body)
        status_bar.pack(fill='x')
        ttk.Label(status_bar, text='선택한 책 상태:').pack(side='left')

        item_to_book: dict[str, object] = {}

        def selected_book():
            selection = tree.selection()
            if not selection:
                return None
            return item_to_book.get(selection[0])

        def render_notes(_event=None) -> None:
            book = selected_book()
            notes_view.configure(state='normal')
            notes_view.delete('1.0', 'end')
            if book is None:
                notes_view.insert('end', '왼쪽에서 책을 선택해 주세요.')
            else:
                notes = self.runtime.journal.notes_for_book(book.book_id)
                if not notes:
                    notes_view.insert('end', '아직 이 책에 남긴 기록이 없어요.')
                else:
                    for index, note in enumerate(notes, 1):
                        date = note.created_at[:10]
                        progress = f' · {note.progress_text}' if note.progress_text else ''
                        notes_view.insert('end', f'{index}. {date}{progress}\n{note.note_text}\n\n')
            notes_view.configure(state='disabled')

        def refresh_books(select_book_id: str | None = None) -> None:
            current = selected_book()
            desired = select_book_id or (current.book_id if current is not None else None)
            for iid in tree.get_children():
                tree.delete(iid)
            item_to_book.clear()
            books = self.runtime.journal.list_books(limit=200)
            select_iid = None
            for book in books:
                iid = tree.insert('', 'end', values=(
                    book.title,
                    book.author or '—',
                    _STATUS_LABELS.get(book.status, book.status),
                ))
                item_to_book[iid] = book
                if book.book_id == desired:
                    select_iid = iid
            if select_iid is None and tree.get_children():
                select_iid = tree.get_children()[0]
            if select_iid:
                tree.selection_set(select_iid)
                tree.focus(select_iid)
            render_notes()

        def set_selected_status(status: str) -> None:
            book = selected_book()
            if book is None:
                return
            self.runtime.journal.set_status(book.book_id, status)
            refresh_books(book.book_id)

        for status in ('reading','completed','wishlist','paused'):
            ttk.Button(
                status_bar,
                text=_STATUS_LABELS[status],
                command=lambda value=status: set_selected_status(value),
            ).pack(side='left', padx=(6, 0))

        tree.bind('<<TreeviewSelect>>', render_notes)
        refresh_books()


def run_pet_v5(*, runtime_factory=bootstrap_runtime) -> int:
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
    DesktopPetWindowV5(runtime).run()
    return 0
