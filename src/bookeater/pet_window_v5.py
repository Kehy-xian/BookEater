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
        tree_scroll = ttk.Scrollbar(left, orient='vertical', command=tree.yview)
        tree_scroll_x = ttk.Scrollbar(left, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=tree_scroll.set, xscrollcommand=tree_scroll_x.set)
        tree_scroll_x.pack(side='bottom', fill='x')
        tree_scroll.pack(side='right', fill='y')
        tree.pack(side='left', fill='both', expand=True)

        ttk.Label(right, text='이 책에 남긴 기록', font=('', 11, 'bold')).pack(anchor='w')
        notes_wrap = ttk.Frame(right)
        notes_wrap.pack(fill='both', expand=True, pady=(6, 0))
        notes_view = tk.Text(notes_wrap, wrap='word', state='disabled', padx=8, pady=8)
        notes_scroll = ttk.Scrollbar(notes_wrap, orient='vertical', command=notes_view.yview)
        notes_view.configure(yscrollcommand=notes_scroll.set)
        notes_view.pack(side='left', fill='both', expand=True)
        notes_scroll.pack(side='right', fill='y')

        book_actions = ttk.Frame(right)
        book_actions.pack(fill='x', pady=(6, 0))

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
                from tkinter import messagebox
                messagebox.showinfo('내 서재', '먼저 책을 선택해 주세요.', parent=win)
                return
            try:
                self.runtime.journal.set_status(book.book_id, status)
                refresh_books(book.book_id)
            except Exception:
                from tkinter import messagebox
                messagebox.showerror('상태 변경 실패', '책 상태를 변경하지 못했어요.', parent=win)
                return
            from tkinter import messagebox
            explanations = {
                'reading': '지금 읽는 책으로 표시했어요. 기록 먹이기에서 계속 선택할 수 있습니다.',
                'completed': '완독한 책으로 표시했어요. 기존 기록과 유전정보는 그대로 남습니다.',
                'wishlist': '읽고 싶은 책으로 표시했어요. 내 서재에 계속 보관됩니다.',
                'paused': '잠시 멈춘 책으로 표시했어요. 나중에 언제든 다시 읽는 중으로 바꿀 수 있습니다.',
            }
            messagebox.showinfo(f'“{book.title}” · {_STATUS_LABELS[status]}', explanations[status], parent=win)

        def edit_selected_book() -> None:
            book = selected_book()
            if book is None:
                from tkinter import messagebox
                messagebox.showinfo('내 서재', '수정할 책을 먼저 선택해 주세요.', parent=win)
                return
            edit = self._new_panel('책 정보 수정')
            edit.transient(win)
            edit_body = ttk.Frame(edit, padding=14)
            edit_body.pack(fill='both', expand=True)
            title_var = tk.StringVar(value=book.title)
            author_var = tk.StringVar(value=book.author)
            msg = tk.StringVar(value='표시 정보만 수정합니다. 독서기록과 유전정보는 바뀌지 않습니다.')
            ttk.Label(edit_body, text='책 제목').grid(row=0, column=0, sticky='w')
            title_entry = ttk.Entry(edit_body, textvariable=title_var, width=40)
            title_entry.grid(row=1, column=0, sticky='ew', pady=(3, 8))
            ttk.Label(edit_body, text='저자 (선택)').grid(row=2, column=0, sticky='w')
            ttk.Entry(edit_body, textvariable=author_var, width=40).grid(row=3, column=0, sticky='ew', pady=(3, 8))
            ttk.Label(edit_body, textvariable=msg, wraplength=340).grid(row=4, column=0, sticky='w')

            def save_edit() -> None:
                title = title_var.get().strip()
                if not title:
                    msg.set('책 제목은 비워 둘 수 없어요.')
                    return
                try:
                    self.runtime.journal.update_book(book.book_id, title=title, author=author_var.get().strip())
                except Exception:
                    msg.set('책 정보를 수정하지 못했어요.')
                    return
                edit.destroy()
                refresh_books(book.book_id)

            ttk.Button(edit_body, text='저장', command=save_edit).grid(row=5, column=0, sticky='e', pady=(10, 0))
            title_entry.focus_set()

        def delete_selected_book() -> None:
            book = selected_book()
            if book is None:
                from tkinter import messagebox
                messagebox.showinfo('내 서재', '삭제할 책을 먼저 선택해 주세요.', parent=win)
                return
            from tkinter import messagebox
            note_count = len(self.runtime.journal.notes_for_book(book.book_id))
            if not messagebox.askyesno(
                '서재에서 책 삭제',
                f'“{book.title}”을 내 서재에서 삭제할까요?\n\n'
                f'연결된 독서기록 {note_count}개는 삭제하지 않고 제목 연결만 해제합니다.\n'
                '이미 반영된 유전정보·성장·도감도 그대로 유지됩니다.\n\n'
                '모든 기록과 유전정보까지 지우려면 데이터 관리의 “전체 초기화”를 사용해야 합니다.',
                parent=win,
            ):
                return
            try:
                self.runtime.journal.delete_book_metadata(book.book_id)
                refresh_books()
            except Exception:
                messagebox.showerror('삭제 실패', '책 정보를 삭제하지 못했어요.', parent=win)
                return
            messagebox.showinfo('삭제 완료', '책 정보만 서재에서 삭제했어요. 독서기록과 유전정보는 보존했습니다.', parent=win)

        ttk.Button(book_actions, text='책 정보 수정', command=edit_selected_book).pack(side='left')
        ttk.Button(book_actions, text='서재에서 삭제', command=delete_selected_book).pack(side='left', padx=(6, 0))

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
