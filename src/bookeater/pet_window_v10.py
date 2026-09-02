from __future__ import annotations

"""Desktop-pet V10: real-catalog recommendations ranked privately on device."""

import hashlib
import queue
import threading
import webbrowser

from .pet_window_v9 import DesktopPetWindowV9
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime
from .services.catalog import CatalogUnavailable, CatalogResponseError, configured_catalog_client
from .services.recommendations import BookCandidate, rank_real_candidates


class DesktopPetWindowV10(DesktopPetWindowV9):
    def __init__(self, runtime: BookEaterRuntime):
        self._recommendation_busy = False
        super().__init__(runtime)
        # Insert before the Data Management cascade so ordinary play actions remain grouped.
        end = self.menu.index('end')
        self.menu.insert_command(max(0, end - 1), label='책 추천', command=self.open_recommendation_panel)

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
        book_id = self._catalog_book_id(candidate)
        existing = self.runtime.journal.get_book(book_id)
        if existing is not None:
            status_var.set(f'“{candidate.title}”은 이미 내 서재에 있어요.')
            return
        try:
            self.runtime.journal.add_book(
                book_id,
                candidate.title,
                author=candidate.author,
                status='wishlist',
                cover_url=candidate.cover_url,
                source=candidate.source,
            )
        except Exception:
            status_var.set('서재에 저장하지 못했어요. 다시 시도해 주세요.')
            return
        status_var.set(f'“{candidate.title}”을 읽고 싶은 책에 넣었어요.')

    def open_recommendation_panel(self) -> None:
        tk, ttk = self.tk, self.ttk
        win = self._new_panel('책 추천', '610x540')
        body = ttk.Frame(win, padding=16)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='이 친구가 고른 실재 도서', font=('', 18, 'bold')).pack(anchor='w')
        ttk.Label(
            body,
            text='후보 도서는 카탈로그 서버에서 받고, 내 독서 성향과 비교하는 작업은 이 PC 안에서만 합니다.',
            wraplength=560,
        ).pack(anchor='w', pady=(3, 10))

        controls = ttk.Frame(body)
        controls.pack(fill='x')
        status_var = tk.StringVar(value='추천 방식을 골라 주세요.')
        result_holder = ttk.Frame(body)
        result_holder.pack(fill='both', expand=True, pady=(12, 6))
        ttk.Label(body, textvariable=status_var, wraplength=560).pack(anchor='w')

        client = configured_catalog_client()
        if client is None:
            ttk.Label(
                result_holder,
                text='아직 실재 도서 카탈로그 서버가 연결되지 않았어요.\n연결되기 전에는 임의의 책을 추천하지 않습니다.',
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
            self._recommendation_busy = False
            if kind == 'ok':
                render(payload)
                status_var.set('실재 도서 후보를 로컬 독서 성향으로 정렬했어요.')
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
            ttk.Label(result_holder, text='실재 도서 후보를 살펴보는 중…').pack(anchor='w')
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
                    result_queue.put(('ok', ranked))
                except (CatalogUnavailable, CatalogResponseError, Exception):
                    result_queue.put(('error', None))

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
