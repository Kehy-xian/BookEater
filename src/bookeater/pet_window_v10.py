from __future__ import annotations

"""Desktop-pet V10: real-catalog recommendations ranked privately on device."""

import hashlib
import queue
import threading
import uuid
import webbrowser

from .pet_window_v9 import DesktopPetWindowV9
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime
from .services.catalog import configured_catalog_client
from .services.recommendations import BookCandidate, rank_real_candidates


class DesktopPetWindowV10(DesktopPetWindowV9):
    def __init__(self, runtime: BookEaterRuntime):
        self._recommendation_busy = False
        super().__init__(runtime)
        self._rebuild_main_menu()

    def _rebuild_main_menu(self) -> None:
        self.menu.delete(0, 'end')
        name = self._monster_name()
        label = name or '몬스터'
        self.menu.add_command(label='기록 먹이기', command=self.open_feed_panel)
        self.menu.add_command(label='기억 꺼내기', command=self.open_memory_panel)
        self.menu.add_command(label='책 추천받기', command=self.open_recommendation_panel)
        self.menu.add_command(label='내 서재', command=self.open_library_panel)
        self.menu.add_separator()
        self.menu.add_command(
            label='몬스터 이름 다시 짓기' if name else '몬스터 이름 짓기',
            command=self.open_monster_name_panel,
        )
        self.menu.add_command(label='몬스터 도감', command=self.open_encyclopedia_panel)
        self.menu.add_command(label=f'{label} 정보 보기', command=self.open_profile_panel)
        self.menu.add_command(label=f'{label} 돌보기', command=self.open_care_panel)
        self.menu.add_command(label='휴식하기(트레이 축소)', command=self._send_home_to_tray)
        self.menu.add_separator()
        data_menu = self.tk.Menu(self.menu, tearoff=0)
        data_menu.add_command(label='기록 내보내기', command=self.export_reading_seed)
        data_menu.add_command(label='기록 읽기', command=self.plant_reading_seed)
        data_menu.add_separator()
        data_menu.add_command(label='전체 초기화', command=self.reset_reading_profile)
        self.menu.add_cascade(label='데이터 관리', menu=data_menu)
        self.menu.add_command(label='설정', command=self.open_settings_panel)
        self.menu.add_command(label='종료', command=self._confirm_exit)

    def open_monster_name_panel(self) -> None:
        tk, ttk = self.tk, self.ttk
        current = self._monster_name()
        win = self._new_panel('몬스터 이름 다시 짓기' if current else '몬스터 이름 짓기')
        win.transient(self.root)
        body = ttk.Frame(win, padding=16)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='몬스터 이름', font=('', 14, 'bold')).pack(anchor='w')
        name_var = tk.StringVar(value=current)
        entry = ttk.Entry(body, textvariable=name_var, width=28)
        entry.pack(fill='x', pady=(8, 5))
        msg = tk.StringVar(value='12자까지 지을 수 있어요.')
        ttk.Label(body, textvariable=msg).pack(anchor='w')
        actions = ttk.Frame(body)
        actions.pack(fill='x', pady=(14, 0))

        def save() -> None:
            name = ' '.join(name_var.get().split())
            if not name:
                msg.set('이름을 입력해 주세요.')
                return
            if len(name) > 12:
                msg.set('이름은 12자까지 지을 수 있어요.')
                return
            self.runtime.settings.set('monster_name', name)
            self._rebuild_main_menu()
            win.destroy()

        def reset_name() -> None:
            self.runtime.settings.delete('monster_name')
            self._rebuild_main_menu()
            win.destroy()

        ttk.Button(actions, text='변경하기' if current else '이름 짓기', command=save).pack(side='right')
        if current:
            ttk.Button(actions, text='이름만 초기화', command=reset_name).pack(side='right', padx=(0, 6))
        entry.bind('<Return>', lambda _event: save())
        entry.focus_set()

    def _data_action_available(self) -> bool:
        if self._recommendation_busy:
            from tkinter import messagebox
            messagebox.showinfo(
                '책먹는 몬스터',
                '추천 후보를 살펴보는 중이에요. 작업이 끝난 뒤 다시 시도해 주세요.',
                parent=self.root,
            )
            return False
        return super()._data_action_available()

    @staticmethod
    def _catalog_book_id(candidate: BookCandidate) -> str:
        raw = f'{candidate.source}\0{candidate.source_id}'.encode('utf-8')
        return 'catalog-' + hashlib.sha256(raw).hexdigest()[:24]

    def _save_wishlist(self, candidate: BookCandidate, status_var) -> None:
        from tkinter import messagebox
        book_id = self._catalog_book_id(candidate)
        existing = self.runtime.journal.get_book(book_id)
        if existing is not None:
            status_var.set(f'“{candidate.title}”은 이미 내 서재에 있어요.')
            messagebox.showinfo('내 서재', f'“{candidate.title}”은 이미 내 서재에 있어요.', parent=self.root)
            return
        try:
            self.runtime.journal.add_book(
                book_id,
                candidate.title,
                author=candidate.author,
                status='wishlist',
                cover_url=candidate.cover_url,
                source=candidate.source,
                isbn13=candidate.isbn13,
                publisher=candidate.publisher,
            )
        except Exception:
            status_var.set('서재에 저장하지 못했어요. 다시 시도해 주세요.')
            messagebox.showerror('저장 실패', '서재에 저장하지 못했어요. 다시 시도해 주세요.', parent=self.root)
            return
        status_var.set(f'“{candidate.title}”을 읽고 싶은 책에 넣었어요.')
        messagebox.showinfo(
            '내 서재에 저장했어요',
            f'“{candidate.title}”을 읽고 싶은 책으로 저장했어요.\n내 서재에서 상태를 바꿀 수 있습니다.',
            parent=self.root,
        )

    def _register_book_dialog(self, *, on_saved=None) -> None:
        """Search the real catalog first, with an explicit manual-entry fallback."""
        tk, ttk = self.tk, self.ttk
        win = self._new_panel('새 책 등록', '650x500')
        body = ttk.Frame(win, padding=14)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='ISBN·서명·저자명으로 찾기', font=('', 14, 'bold')).pack(anchor='w')
        ttk.Label(
            body,
            text='검색 결과에서 정확한 판본을 고르세요. 찾는 책이 없으면 직접 입력할 수 있습니다.',
            wraplength=600,
        ).pack(anchor='w', pady=(2, 8))
        search_row = ttk.Frame(body)
        search_row.pack(fill='x')
        query_var = tk.StringVar()
        query_entry = ttk.Entry(search_row, textvariable=query_var)
        query_entry.pack(side='left', fill='x', expand=True)
        search_button = ttk.Button(search_row, text='조회')
        search_button.pack(side='left', padx=(6, 0))

        results_wrap = ttk.Frame(body)
        results_wrap.pack(fill='both', expand=True, pady=(10, 6))
        columns = ('title', 'author', 'publisher', 'isbn')
        tree = ttk.Treeview(results_wrap, columns=columns, show='headings', selectmode='browse', height=10)
        for key, label, width in (
            ('title', '서명', 220), ('author', '저자', 145),
            ('publisher', '출판사', 105), ('isbn', 'ISBN', 105),
        ):
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor='w')
        scroll = ttk.Scrollbar(results_wrap, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        msg = tk.StringVar(value='검색어를 입력하거나 “직접 입력하기”를 누르세요.')
        ttk.Label(body, textvariable=msg, wraplength=600).pack(anchor='w')
        actions = ttk.Frame(body)
        actions.pack(fill='x', pady=(8, 0))
        item_to_candidate: dict[str, BookCandidate] = {}
        result_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        alive = {'yes': True}

        def finish(book_id: str) -> None:
            alive['yes'] = False
            win.destroy()
            if on_saved:
                on_saved(book_id)

        def save_candidate(candidate: BookCandidate) -> None:
            book_id = self._catalog_book_id(candidate)
            if self.runtime.journal.get_book(book_id) is None:
                self.runtime.journal.add_book(
                    book_id, candidate.title, author=candidate.author, status='reading',
                    isbn13=candidate.isbn13, publisher=candidate.publisher,
                    cover_url=candidate.cover_url, source=candidate.source,
                )
            finish(book_id)

        def choose_result() -> None:
            selection = tree.selection()
            if not selection:
                msg.set('등록할 판본을 목록에서 선택해 주세요.')
                return
            candidate = item_to_candidate.get(selection[0])
            if candidate is None:
                return
            try:
                save_candidate(candidate)
            except Exception:
                msg.set('선택한 책을 저장하지 못했어요. 다시 시도해 주세요.')

        def manual_entry() -> None:
            manual = self._new_panel('책 직접 입력')
            manual.transient(win)
            form = ttk.Frame(manual, padding=14)
            form.pack(fill='both', expand=True)
            title_var = tk.StringVar(value=query_var.get().strip())
            author_var = tk.StringVar()
            manual_msg = tk.StringVar(value='조회되지 않은 책도 직접 등록할 수 있습니다.')
            ttk.Label(form, text='책 제목').grid(row=0, column=0, sticky='w')
            title_entry = ttk.Entry(form, textvariable=title_var, width=42)
            title_entry.grid(row=1, column=0, sticky='ew', pady=(3, 8))
            ttk.Label(form, text='저자 (선택)').grid(row=2, column=0, sticky='w')
            ttk.Entry(form, textvariable=author_var, width=42).grid(row=3, column=0, sticky='ew', pady=(3, 8))
            ttk.Label(form, textvariable=manual_msg, wraplength=350).grid(row=4, column=0, sticky='w')

            def save_manual() -> None:
                title = title_var.get().strip()
                author = author_var.get().strip()
                if not title:
                    manual_msg.set('책 제목을 입력해 주세요.')
                    return
                for existing in self.runtime.journal.list_books(limit=500):
                    if existing.title.casefold() == title.casefold() and (
                        existing.author.casefold() == author.casefold() or not author
                    ):
                        manual.destroy(); finish(existing.book_id); return
                try:
                    book_id = uuid.uuid4().hex
                    self.runtime.journal.add_book(book_id, title, author=author)
                except Exception:
                    manual_msg.set('책을 저장하지 못했어요.')
                    return
                manual.destroy(); finish(book_id)

            ttk.Button(form, text='등록', command=save_manual).grid(row=5, column=0, sticky='e', pady=(10, 0))
            title_entry.focus_set()

        def poll() -> None:
            if not alive['yes']:
                return
            try:
                kind, payload = result_queue.get_nowait()
            except queue.Empty:
                win.after(100, poll)
                return
            search_button.configure(state='normal')
            if kind == 'error':
                msg.set('조회 서버에 연결하지 못했어요. 직접 입력하기를 사용할 수 있습니다.')
                return
            items = payload if isinstance(payload, list) else []
            for iid in tree.get_children():
                tree.delete(iid)
            item_to_candidate.clear()
            for candidate in items:
                iid = tree.insert('', 'end', values=(
                    candidate.title, candidate.author or '—', candidate.publisher or '—',
                    candidate.isbn13 or candidate.source_id,
                ))
                item_to_candidate[iid] = candidate
            msg.set(f'{len(items)}개 판본을 찾았어요. 하나를 선택해 주세요.' if items else '검색 결과가 없어요. 직접 입력할 수 있습니다.')

        def search() -> None:
            query = query_var.get().strip()
            if not query:
                msg.set('ISBN·서명·저자명 중 하나를 입력해 주세요.')
                return
            client = configured_catalog_client()
            if client is None:
                msg.set('조회 서버가 연결되지 않았어요. 직접 입력하기를 사용해 주세요.')
                return
            search_button.configure(state='disabled')
            msg.set('실제 도서를 조회하는 중…')

            def work() -> None:
                try:
                    result_queue.put(('ok', client.search(query, limit=20)))
                except Exception:
                    result_queue.put(('error', None))
            threading.Thread(target=work, name='bookeater-book-search', daemon=True).start()
            win.after(100, poll)

        ttk.Button(actions, text='선택한 책 등록', command=choose_result).pack(side='right')
        ttk.Button(actions, text='직접 입력하기', command=manual_entry).pack(side='right', padx=(0, 6))
        ttk.Label(
            body,
            text='도서 DB 제공 : 알라딘 인터넷서점(www.aladin.co.kr)',
        ).pack(anchor='e', pady=(8, 0))
        search_button.configure(command=search)
        query_entry.bind('<Return>', lambda _event: search())
        tree.bind('<Double-Button-1>', lambda _event: choose_result())
        win.bind('<Destroy>', lambda event: alive.update(yes=False) if event.widget is win else None, add='+')
        query_entry.focus_set()

    def open_recommendation_panel(self) -> None:
        tk, ttk = self.tk, self.ttk
        win = self._new_panel('책 추천', '610x540')
        body = ttk.Frame(win, padding=16)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text=f'{self._monster_subject()} 책을 추천해줘요', font=('', 18, 'bold')).pack(anchor='w')
        ttk.Label(
            body,
            text='기록을 토대로 독서 성향을 파악하고, 책을 추천받을 수 있어요.',
            wraplength=560,
        ).pack(anchor='w', pady=(3, 10))

        controls = ttk.Frame(body)
        controls.pack(fill='x')
        status_var = tk.StringVar(value='')
        result_wrap = ttk.Frame(body)
        result_wrap.pack(fill='both', expand=True, pady=(12, 6))
        result_canvas = tk.Canvas(result_wrap, highlightthickness=0)
        result_scroll = ttk.Scrollbar(result_wrap, orient='vertical', command=result_canvas.yview)
        result_holder = ttk.Frame(result_canvas)
        holder_window = result_canvas.create_window((0, 0), window=result_holder, anchor='nw')
        result_canvas.configure(yscrollcommand=result_scroll.set)
        result_canvas.pack(side='left', fill='both', expand=True)
        result_scroll.pack(side='right', fill='y')
        result_holder.bind(
            '<Configure>',
            lambda _event: result_canvas.configure(scrollregion=result_canvas.bbox('all')),
        )
        result_canvas.bind(
            '<Configure>',
            lambda event: result_canvas.itemconfigure(holder_window, width=event.width),
        )
        ttk.Label(body, textvariable=status_var, wraplength=560).pack(anchor='w')
        ttk.Label(
            body,
            text='도서 DB 제공 : 알라딘 인터넷서점(www.aladin.co.kr)',
        ).pack(anchor='e', pady=(4, 0))

        client = configured_catalog_client()
        if client is None:
            ttk.Label(
                result_holder,
                text='아직 실제 도서 카탈로그 서버가 연결되지 않았어요.\n연결되기 전에는 임의의 책을 추천하지 않습니다.',
                justify='center',
            ).pack(expand=True)
            status_var.set('추천 서버 연결을 기다리는 중입니다.')
            return

        result_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        alive = {'yes': True}

        def on_destroy(event) -> None:
            if event.widget is win:
                alive['yes'] = False
        win.bind('<Destroy>', on_destroy, add='+')

        def clear_results() -> None:
            for child in result_holder.winfo_children():
                child.destroy()

        def render(items) -> None:
            clear_results()
            if not items:
                ttk.Label(result_holder, text='지금 보여줄 수 있는 실제 후보 도서가 없어요.').pack(anchor='w')
                return
            for index, ranked in enumerate(items, 1):
                candidate = ranked.candidate
                card = ttk.Frame(result_holder, padding=(8, 7))
                card.pack(fill='x', pady=2)
                left = ttk.Frame(card)
                left.pack(side='left', fill='x', expand=True)
                ttk.Label(left, text=f'{index}. {candidate.title}', font=('', 10, 'bold')).pack(anchor='w')
                ttk.Label(left, text=candidate.author or '저자 정보 없음').pack(anchor='w')
                if candidate.description:
                    desc = candidate.description.replace('\n', ' ').strip()
                    if len(desc) > 110:
                        desc = desc[:107] + '…'
                    ttk.Label(left, text=desc, wraplength=395).pack(anchor='w', pady=(2, 0))
                actions = ttk.Frame(card)
                actions.pack(side='right', padx=(8, 0))
                ttk.Button(
                    actions,
                    text='읽고 싶음',
                    command=lambda c=candidate: self._save_wishlist(c, status_var),
                ).pack()
                if candidate.detail_url:
                    ttk.Button(
                        actions,
                        text='상세',
                        command=lambda url=candidate.detail_url: webbrowser.open(url),
                    ).pack(pady=(4, 0))

        def poll() -> None:
            if not alive['yes']:
                return
            try:
                kind, payload = result_queue.get_nowait()
            except queue.Empty:
                win.after(100, poll)
                return
            if kind in {'ok', 'cold'}:
                render(payload)
                if kind == 'cold':
                    status_var.set('아직 독서기록이 없어 현재 베스트셀러 순서로 보여드려요. 기록이 쌓이면 내 취향으로 정렬됩니다.')
                else:
                    status_var.set('실제 도서 후보를 독서 성향에 맞춰 정렬했어요.')
            elif kind == 'empty':
                render([])
                status_var.set('카탈로그에서 후보를 받지 못했어요. 나중에 다시 시도해 주세요.')
            else:
                clear_results()
                ttk.Label(result_holder, text='추천 서버에 잠시 문제가 있어요.').pack(anchor='w')
                status_var.set('기록과 유전정보는 서버로 보내지 않았고, 기존 데이터도 변경하지 않았습니다.')

        def load(mode: str) -> None:
            if self._recommendation_busy or self._data_mutating or self._busy or self._recovery_busy:
                status_var.set('다른 작업이 끝난 뒤 다시 눌러 주세요.')
                return
            self._recommendation_busy = True
            clear_results()
            ttk.Label(result_holder, text='실제 도서 후보를 살펴보는 중…').pack(anchor='w')
            status_var.set('후보 목록만 받아오고 있어요. 독서기록은 전송하지 않습니다.')

            def work() -> None:
                try:
                    candidates = client.discovery_pool(limit=40)
                    if not candidates:
                        result_queue.put(('empty', None))
                        return
                    state = self.runtime.store.load_state()
                    ranked = rank_real_candidates(
                        candidates,
                        self.runtime.analyzer,
                        state.stats,
                        mode=mode,
                        limit=5,
                    )
                    cold_start = not any(float(value) > 0 for value in state.stats.values())
                    result_queue.put(('cold' if cold_start else 'ok', ranked))
                except Exception:
                    result_queue.put(('error', None))
                finally:
                    # The panel may have been closed before poll() can consume the result. Always
                    # release the process-wide activity flag so data maintenance never remains
                    # permanently locked after a closed recommendation window.
                    self._recommendation_busy = False

            threading.Thread(target=work, name='bookeater-recommendations', daemon=True).start()
            win.after(100, poll)

        ttk.Button(controls, text='내 취향에 가까운 책', command=lambda: load('taste')).pack(side='left')
        ttk.Button(controls, text='조금 다른 세계의 책', command=lambda: load('expand')).pack(side='left', padx=(6, 0))


def run_pet_v10(*, runtime_factory=bootstrap_runtime) -> int:
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
    DesktopPetWindowV10(runtime).run()
    return 0
