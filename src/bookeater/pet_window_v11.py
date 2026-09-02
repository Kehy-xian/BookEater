from __future__ import annotations

"""Desktop-pet V11: crash-resistant note drafts and save-first submission.

Committed reading records were already transactional; this version protects the only meaningful
remaining loss window: text typed in the feed panel but not yet submitted. Drafts autosave locally
and are restored on the next panel/app launch. On submit, the raw note and its book context are
written synchronously before semantic analysis starts in a background thread.
"""

import threading
import uuid

from .pet_window_v10 import DesktopPetWindowV10
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime


class DesktopPetWindowV11(DesktopPetWindowV10):
    # Throttle, not debounce: continuous typing still reaches SQLite at least about once per this
    # interval instead of postponing the save forever until the user pauses.
    DRAFT_AUTOSAVE_MS = 1200

    def open_feed_panel(self) -> None:
        if self._busy:
            return
        tk, ttk = self.tk, self.ttk
        books = self._recent_books()
        if not books:
            self._register_book_dialog(on_saved=lambda _bid: self.open_feed_panel())
            return
        book_choices = dict(self._book_display_to_id)

        draft = self.runtime.drafts.load()
        draft_display = None
        if draft is not None and draft.book_id:
            draft_display = next(
                (
                    label
                    for label, book_id in book_choices.items()
                    if book_id == draft.book_id
                ),
                None,
            )

        win = self._new_panel('기록 먹이기', '470x455')
        body = ttk.Frame(win, padding=14)
        body.pack(fill='both', expand=True)

        ttk.Label(body, text='어느 책을 읽었나요?').pack(anchor='w')
        choices = list(book_choices)
        book_var = tk.StringVar(value=draft_display or choices[0])
        if draft is not None and draft.book_id and draft_display is None:
            # Do not silently attach a recovered draft to a different book.
            book_var.set('')
        combo = ttk.Combobox(
            body,
            textvariable=book_var,
            state='readonly',
            values=choices,
        )
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
                schedule_save()

        ttk.Button(
            body,
            text='새 책 등록',
            command=lambda: self._register_book_dialog(on_saved=select_registered_book),
        ).pack(anchor='e')

        row = ttk.Frame(body)
        row.pack(fill='x', pady=(8, 0))
        ttk.Label(row, text='읽은 곳 (선택)').pack(side='left')
        progress_var = tk.StringVar(value=draft.progress_text if draft is not None else '')
        progress_entry = ttk.Entry(row, textvariable=progress_var)
        progress_entry.pack(side='left', fill='x', expand=True, padx=(8, 0))

        ttk.Label(body, text='기록').pack(anchor='w', pady=(10, 0))
        note = tk.Text(body, height=10, wrap='word', undo=True)
        note.pack(fill='both', expand=True, pady=(4, 8))
        if draft is not None and draft.note_text:
            note.insert('1.0', draft.note_text)

        if draft is None:
            initial_status = '같은 책에 여러 번 이어서 남길 수 있어요. 초안은 이 PC에 자동 저장됩니다.'
        elif draft.book_id and draft_display is None:
            initial_status = '저장된 초안을 복구했어요. 원래 책을 찾지 못해 책을 다시 선택해야 합니다.'
        else:
            initial_status = '저장된 초안을 복구했어요. 입력 중 내용은 자동 저장됩니다.'
        status_var = tk.StringVar(value=initial_status)
        ttk.Label(body, textvariable=status_var, wraplength=420).pack(anchor='w')

        save_job = {'id': None}
        submitted = {'yes': False}

        def selected_book_id() -> str | None:
            return book_choices.get(book_var.get())

        def flush_draft(*, announce: bool = False) -> None:
            try:
                text = note.get('1.0', 'end').rstrip('\n')
            except tk.TclError:
                return
            try:
                self.runtime.drafts.save(
                    book_id=selected_book_id(),
                    progress_text=progress_var.get(),
                    note_text=text,
                )
                if announce and (text or progress_var.get()):
                    status_var.set('초안을 이 PC에 자동 저장했어요.')
            except Exception:
                # A draft save failure must never block the user's ability to submit the record.
                if announce:
                    status_var.set('초안 자동저장에 문제가 있어요. 먹이기 버튼을 누르면 기록은 바로 저장됩니다.')

        def autosave_now() -> None:
            save_job['id'] = None
            flush_draft(announce=True)

        def schedule_save(_event=None) -> None:
            # Do not cancel an already scheduled save. This makes autosave a throttle and bounds
            # the unsaved window even when key-release events arrive continuously for minutes.
            if save_job['id'] is None:
                save_job['id'] = win.after(self.DRAFT_AUTOSAVE_MS, autosave_now)

        combo.bind('<<ComboboxSelected>>', schedule_save)
        progress_entry.bind('<KeyRelease>', schedule_save)
        note.bind('<KeyRelease>', schedule_save)

        def cancel_pending_save() -> None:
            job = save_job['id']
            save_job['id'] = None
            if job is not None:
                try:
                    win.after_cancel(job)
                except tk.TclError:
                    pass

        def close_panel() -> None:
            cancel_pending_save()
            if not submitted['yes']:
                flush_draft()
            win.destroy()

        win.protocol('WM_DELETE_WINDOW', close_panel)

        def submit() -> None:
            if self._busy:
                return
            text = note.get('1.0', 'end').strip()
            book_id = selected_book_id()
            if not text:
                status_var.set('기록을 먼저 적어 주세요.')
                return
            if not book_id:
                status_var.set('책을 다시 선택해 주세요.')
                return

            feed_id = uuid.uuid4().hex
            # Save first, synchronously. Analysis can be slow or fail, but the user's text is now
            # durable and will remain pending for retry rather than disappearing with the window.
            try:
                self.runtime.journal.attach_note(
                    self.runtime.store,
                    feed_id,
                    text,
                    book_id=book_id,
                    progress_text=progress_var.get().strip() or None,
                )
                self.runtime.drafts.clear()
            except Exception:
                status_var.set('기록을 저장하지 못했어요. 초안은 유지했습니다. 다시 시도해 주세요.')
                return

            submitted['yes'] = True
            cancel_pending_save()
            self._busy = True
            self._pet_state = 'eat'
            self._eat_frames = 12
            win.destroy()

            def work() -> None:
                try:
                    outcome = self.runtime.feed_service.retry(feed_id)
                    self._result_queue.put(('feed', outcome))
                except Exception as exc:
                    self._result_queue.put(('error', type(exc).__name__))

            threading.Thread(target=work, name='bookeater-pet-feed', daemon=True).start()

        ttk.Button(body, text='몬스터에게 먹이기', command=submit).pack(anchor='e', pady=(8, 0))
        note.bind('<Control-Return>', lambda _e: submit())
        note.focus_set()


def run_pet_v11(*, runtime_factory=bootstrap_runtime) -> int:
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
    DesktopPetWindowV11(runtime).run()
    return 0
