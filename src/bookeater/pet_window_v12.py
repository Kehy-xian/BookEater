from __future__ import annotations

"""Desktop-pet V12: evolution ceremonies and completed-monster story books."""

import random
from datetime import datetime

from .game.form_catalog import catalog_entry
from .game.growth_routes import get_growth_form
from .korean_text import named_subject, quoted_object
from .pet_window_v11 import DesktopPetWindowV11
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime
from .ui_text_flow import TYPEWRITER_DELAY_MS, typewriter_prefix


class DesktopPetWindowV12(DesktopPetWindowV11):
    def __init__(self, runtime: BookEaterRuntime):
        self._last_presented_form_id = runtime.store.load_state().form_id
        self._ceremony_open = False
        super().__init__(runtime)

    def _rebuild_main_menu(self) -> None:
        super()._rebuild_main_menu()
        state = self.runtime.store.load_state()
        if get_growth_form(state.form_id).tier < 3:
            return
        # Insert directly below 휴식하기 and before its following separator.
        end = self.menu.index('end')
        if end is None:
            return
        for index in range(end + 1):
            if self.menu.type(index) == 'command' and self.menu.entrycget(index, 'label') == '휴식하기(트레이 축소)':
                self.menu.insert_command(index + 1, label='떠나보내기', command=self._ask_release_monster)
                break

    def _after_feed_processed(self, outcome) -> None:
        state = self.runtime.store.load_state()
        previous = self._last_presented_form_id
        self._last_presented_form_id = state.form_id
        if previous == state.form_id:
            return
        self.runtime.memoirs.record_evolution(previous, state.form_id, state.entry_count)
        self.root.after(250, lambda: self._open_evolution_ceremony(previous, state.form_id))

    def _idle_frame(self, form_id: str):
        if self._sprite_cache is None:
            return None
        frames = self._sprite_cache.frames(form_id, 'idle', scale=1.0)
        return frames[0] if frames else None

    def _open_evolution_ceremony(self, previous: str, current: str) -> None:
        if self._ceremony_open:
            return
        self._ceremony_open = True
        self.root.withdraw()
        tk, ttk = self.tk, self.ttk
        win = tk.Toplevel(self.root)
        win.title('새로운 모습')
        win.geometry('560x520')
        win.resizable(False, False)
        win.attributes('-topmost', True)
        canvas = tk.Canvas(win, width=560, height=365, bg='#11152f', highlightthickness=0)
        canvas.pack(fill='x')
        is_final = get_growth_form(current).tier >= 3
        message = tk.StringVar(value='')
        ttk.Label(win, textvariable=message, font=('', 14, 'bold'), anchor='center').pack(fill='x', pady=(18, 8))
        action = ttk.Frame(win)
        action.pack(fill='x', padx=24)
        jobs: list[str] = []
        alive = {'yes': True}
        glowing = {'yes': True}
        advance = {'action': None}

        def clear_actions() -> None:
            for child in action.winfo_children():
                child.destroy()

        def run_advance(_event=None):
            callback = advance['action']
            if callback is not None:
                advance['action'] = None
                callback()
            return 'break'

        win.bind('<space>', run_advance)

        def type_message(
            copy: str, done, *, button_text: str = '다음', delay: int = TYPEWRITER_DELAY_MS,
        ) -> None:
            clear_actions()
            advance['action'] = None
            message.set('')

            def step(index: int = 0) -> None:
                if not alive['yes']:
                    return
                message.set(typewriter_prefix(copy, index))
                if index <= len(copy):
                    jobs.append(win.after(delay, lambda: step(index + 1)))
                else:
                    advance['action'] = done
                    ttk.Button(action, text=button_text, command=run_advance).pack(anchor='center')
            step()

        stars = [(random.randint(20, 540), random.randint(15, 340), random.randint(1, 3)) for _ in range(42)]
        for x, y, size in stars:
            canvas.create_oval(x-size, y-size, x+size, y+size, fill='#fff2ae', outline='')

        def glow(frame: int = 0) -> None:
            if not alive['yes'] or not glowing['yes']:
                return
            canvas.delete('glow')
            radius = 45 + (frame % 10) * 12
            colors = ('#fff9c9', '#f8dd80', '#cab8ff')
            for i in range(3):
                r = radius + i * 27
                canvas.create_oval(280-r, 182-r, 280+r, 182+r, outline=colors[i], width=5-i, tags='glow')
            canvas.tag_lower('glow')
            jobs.append(win.after(110, lambda: glow(frame + 1)))
        glow()

        def reveal() -> None:
            if not alive['yes']:
                return
            glowing['yes'] = False
            canvas.delete('all')
            for index, (x, y, size) in enumerate(stars):
                color = '#ffffff' if index % 2 else '#ffe78a'
                canvas.create_oval(x-size, y-size, x+size, y+size, fill=color, outline='')
            image = self._idle_frame(current)
            if image is not None:
                canvas.create_image(280, 190, image=image)
                win._bookeater_image = image
            else:
                canvas.create_oval(215, 125, 345, 255, fill='#f4edda', outline='#29241f', width=4)
                canvas.create_text(280, 190, text=catalog_entry(current).public_name, fill='#25211e')
            tier = get_growth_form(current).tier
            if tier < 3:
                type_message(
                    f'{self._monster_subject()} 부쩍 컸다!',
                    lambda: finish(False), button_text='계속하기',
                )
            else:
                type_message(
                    f'{self._monster_subject()} 무럭무럭 자라 어른이 되었어요.\n'
                    '그동안 열심히 키워줘서 고마워요!',
                    lambda: finish(True), button_text='계속하기',
                )
            sparkle()

        def sparkle(frame: int = 0) -> None:
            if not alive['yes'] or not canvas.winfo_exists():
                return
            canvas.delete('sparkle')
            for index, (x, y, size) in enumerate(stars):
                if (index + frame) % 4 == 0:
                    radius = size + (frame % 3)
                    canvas.create_line(x-radius*2, y, x+radius*2, y, fill='#ffffff', tags='sparkle')
                    canvas.create_line(x, y-radius*2, x, y+radius*2, fill='#ffffff', tags='sparkle')
            jobs.append(win.after(240, lambda: sparkle(frame + 1)))

        def close_window() -> None:
            alive['yes'] = False
            for job in jobs:
                try:
                    win.after_cancel(job)
                except tk.TclError:
                    pass
            win.destroy()
            self._ceremony_open = False
            self.root.deiconify()

        def finish(final: bool) -> None:
            close_window()
            if final:
                self.root.after(120, self._offer_final_choice)

        win.protocol('WM_DELETE_WINDOW', lambda: finish(get_growth_form(current).tier >= 3))
        type_message('우왓!' if is_final else '어라...?', reveal)

    def _offer_final_choice(self) -> None:
        from tkinter import messagebox
        if messagebox.askyesno(
            '새로운 보금자리',
            f'{quoted_object(self._monster_label())} 새로운 보금자리로 보내주시겠습니까?',
            parent=self.root,
        ):
            self._release_monster()
            return
        self.runtime.settings.set_bool('growth_locked', True)
        self._rebuild_main_menu()

    def _ask_release_monster(self) -> None:
        from tkinter import messagebox
        if messagebox.askyesno(
            '떠나보내기',
            f'{quoted_object(self._monster_label())} 정말 떠나보내시겠습니까?',
            parent=self.root,
        ):
            self._release_monster()

    def _release_monster(self) -> None:
        self.runtime.settings.set_bool('growth_locked', True)
        tk, ttk = self.tk, self.ttk
        win = self._new_panel('새로운 보금자리', '590x540')
        win.transient(self.root)
        canvas = tk.Canvas(win, width=590, height=300, bg='#d8c8a8', highlightthickness=0)
        canvas.pack(fill='x')
        # Library background and the departing back silhouette; replaceable with final art later.
        for x in range(15, 576, 80):
            canvas.create_rectangle(x, 35, x+58, 255, fill='#7b513b', outline='#4b3329', width=2)
            for y in range(60, 235, 35):
                canvas.create_line(x+5, y, x+53, y, fill='#e6c982', width=8)
        canvas.create_oval(250, 142, 340, 244, fill='#5a4a42', outline='#29241f', width=3)
        canvas.create_oval(258, 230, 292, 258, fill='#5a4a42', outline='#29241f')
        canvas.create_oval(298, 230, 332, 258, fill='#5a4a42', outline='#29241f')
        body = ttk.Frame(win, padding=18)
        body.pack(fill='both', expand=True)
        ttk.Label(
            body,
            text=(
                f'{self._monster_subject()} 이제 자신의 보금자리를 찾으러 떠났습니다.\n\n'
                f'{self._monster_subject()} 잘 키워줘서 고맙다며 책을 한 권 두고 갔습니다.\n\n'
                '신기한 책이다. 책을 펼쳐보시겠습니까?'
            ),
            justify='center', anchor='center', wraplength=520,
        ).pack(fill='x', pady=(0, 12))
        ttk.Button(body, text='펼쳐본다', command=lambda: self._open_left_book(win)).pack()

    def _open_left_book(self, farewell_window) -> None:
        from tkinter import messagebox
        try:
            memoir = self.runtime.memoirs.create_current_book(
                monster_name=self._monster_label(),
                final_form_id=self.runtime.store.load_state().form_id,
                favorite_book=self.runtime.settings.get('favorite_book_title', '') or '',
            )
        except Exception:
            messagebox.showerror('책을 만들지 못했어요', '기록은 그대로 보존되어 있습니다. 다시 시도해 주세요.', parent=farewell_window)
            return
        farewell_window.destroy()
        self._show_memoir(memoir, after_close=lambda: self._after_memoir_closed(memoir))

    def _show_memoir(self, memoir, *, after_close=None) -> None:
        from tkinter import messagebox
        tk, ttk = self.tk, self.ttk
        win = self._new_panel(f'{memoir.monster_name}의 책', '760x600')
        outer = ttk.Frame(win, padding=12)
        outer.pack(fill='both', expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        inner = ttk.Frame(canvas, padding=(12, 6, 12, 20))
        canvas.configure(yscrollcommand=scroll.set)
        canvas.create_window((0, 0), window=inner, anchor='nw', tags='inner')
        canvas.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        inner.bind('<Configure>', lambda _e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure('inner', width=e.width))
        ttk.Label(inner, text=f'{memoir.monster_name}의 책', font=('', 20, 'bold')).pack(anchor='center', pady=(2, 4))
        if memoir.favorite_book:
            ttk.Label(inner, text=f'가장 좋아하는 책: {memoir.favorite_book}').pack(anchor='center', pady=(0, 14))
        images = []
        events = [
            {'to_form_id': 'starter', 'entry_count': 0, 'happened_at': memoir.started_at},
            *memoir.payload.get('evolutions', []),
        ]
        records = memoir.payload.get('records', [])
        for event_index, event in enumerate(events):
            section = ttk.LabelFrame(inner, text='처음 만난 모습' if event is events[0] else '자라난 순간', padding=10)
            section.pack(fill='x', pady=6)
            form_id = str(event.get('to_form_id', 'starter'))
            art = tk.Canvas(section, width=190, height=190, highlightthickness=0)
            art.pack(side='left', padx=(0, 12))
            image = self._idle_frame(form_id)
            if image is not None:
                images.append(image)
                art.create_image(95, 95, image=image)
            else:
                art.create_text(95, 95, text=catalog_entry(form_id).public_name)
            info = ttk.Frame(section)
            info.pack(side='left', fill='both', expand=True)
            ttk.Label(info, text=catalog_entry(form_id).public_name, font=('', 13, 'bold')).pack(anchor='w')
            happened_at = str(event.get('happened_at', ''))
            ttk.Label(info, text=happened_at[:10]).pack(anchor='w')
            end_at = (
                str(events[event_index + 1].get('happened_at', ''))
                if event_index + 1 < len(events) else memoir.completed_at
            )
            stage_records = [
                item for item in records
                if happened_at <= str(item.get('created_at', '')) <= end_at
            ]
            titles = []
            for item in stage_records:
                title = str(item.get('title') or '').strip()
                if title and title not in titles:
                    titles.append(title)
            ttk.Label(info, text=f'함께 남긴 기록 {len(stage_records)}개').pack(anchor='w', pady=(4, 0))
            if titles:
                ttk.Label(info, text='읽은 책: ' + ', '.join(titles), wraplength=390).pack(anchor='w')
            try:
                elapsed = max(0, (datetime.fromisoformat(end_at) - datetime.fromisoformat(happened_at)).days)
                ttk.Label(info, text=f'이 모습으로 지낸 시간 {elapsed}일').pack(anchor='w')
            except (TypeError, ValueError):
                pass
        ttk.Separator(inner).pack(fill='x', pady=12)
        ttk.Label(inner, text='함께 읽은 책과 기록', font=('', 15, 'bold')).pack(anchor='w', pady=(0, 6))
        if not records:
            ttk.Label(inner, text='책에 연결된 기록은 없어요.').pack(anchor='w')
        for record in records:
            title = str(record.get('title') or '제목 없는 책')
            ttk.Button(
                inner, text=f'{title} · {str(record.get("created_at", ""))[:10]}',
                command=lambda item=record: messagebox.showinfo(
                    str(item.get('title') or '독서기록'),
                    (f'{item.get("progress_text")}\n\n' if item.get('progress_text') else '') + str(item.get('note_text') or ''),
                    parent=win,
                ),
            ).pack(fill='x', pady=3)
        win._bookeater_images = images

        def close() -> None:
            win.destroy()
            if after_close:
                after_close()
        win.protocol('WM_DELETE_WINDOW', close)
        ttk.Button(inner, text='책 덮기', command=close).pack(pady=(18, 0))

    def _after_memoir_closed(self, memoir) -> None:
        from tkinter import messagebox
        again = messagebox.askyesno(
            '나만의 책',
            f'{memoir.monster_name}의 책은 내 서재에서 언제든지 다시 꺼내볼 수 있습니다.\n\n'
            '새로운 책을 한 권 더 써보시겠어요?',
            parent=self.root,
        )
        self.runtime.memoirs.begin_new_cycle()
        self.runtime.drafts.clear()
        self._last_presented_form_id = 'starter'
        self._refresh_after_profile_change()
        self._rebuild_main_menu()
        if again:
            self.root.after(120, self._open_birth_onboarding)
        else:
            self.root.destroy()

    def _open_memoir_library(self) -> None:
        tk, ttk = self.tk, self.ttk
        books = self.runtime.memoirs.list_books()
        win = self._new_panel('나만의 책', '520x430')
        body = ttk.Frame(win, padding=14)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='나만의 책', font=('', 18, 'bold')).pack(anchor='w')
        ttk.Label(body, text='다 자란 몬스터가 남기고 간 책입니다.').pack(anchor='w', pady=(2, 10))
        if not books:
            ttk.Label(body, text='아직 완성된 책이 없어요.').pack(anchor='w')
            return
        holder = ttk.Frame(body)
        holder.pack(fill='both', expand=True)
        tree = ttk.Treeview(holder, columns=('name', 'date'), show='headings', selectmode='browse')
        tree.heading('name', text='책')
        tree.heading('date', text='완성한 날')
        tree.column('name', width=300, anchor='w')
        tree.column('date', width=110, anchor='center')
        scroll = ttk.Scrollbar(holder, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        mapping = {}
        for book in books:
            iid = tree.insert('', 'end', values=(f'{book.monster_name}의 책', book.completed_at[:10]))
            mapping[iid] = book
        if tree.get_children():
            tree.selection_set(tree.get_children()[0])

        def open_selected(_event=None) -> None:
            selected = tree.selection()
            if selected:
                self._show_memoir(mapping[selected[0]])

        tree.bind('<Double-Button-1>', open_selected)
        ttk.Button(body, text='펼쳐보기', command=open_selected).pack(anchor='e', pady=(8, 0))


def run_pet_v12(*, runtime_factory=bootstrap_runtime) -> int:
    try:
        runtime = runtime_factory()
    except RuntimeStartupError:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        messagebox.showerror('책먹는 몬스터', '독서기록 저장 공간을 안전하게 열 수 없습니다.')
        root.destroy()
        return 2
    DesktopPetWindowV12(runtime).run()
    return 0
