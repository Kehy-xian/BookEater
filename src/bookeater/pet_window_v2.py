from __future__ import annotations

"""Second desktop-pet shell layer.

V2 keeps the proven feed/library behavior from DesktopPetWindow and adds player-facing collection
UI plus a more grounded idle breathing motion.  Production PNG sprites can replace this renderer
later without changing the panels or reading pipeline.
"""

from .game.form_catalog import catalog_entry
from .game.growth_routes import ALL_GROWTH_FORMS
from .pet_window import DesktopPetWindow, _INTERRUPT_STATES
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime


class DesktopPetWindowV2(DesktopPetWindow):
    def __init__(self, runtime: BookEaterRuntime):
        super().__init__(runtime)
        # Existing indices before insertion: feed, library, profile, separator, exit.
        self.menu.insert_command(2, label='몬스터 도감', command=self.open_encyclopedia_panel)

    def open_encyclopedia_panel(self) -> None:
        tk, ttk = self.tk, self.ttk
        encountered = self.runtime.encyclopedia.encountered_ids()
        win = self._new_panel('몬스터 도감', '650x530')
        body = ttk.Frame(win, padding=14)
        body.pack(fill='both', expand=True)

        ttk.Label(body, text='몬스터 도감', font=('', 18, 'bold')).pack(anchor='w')
        ttk.Label(
            body,
            text=f'만난 모습 {len(encountered)} / {len(ALL_GROWTH_FORMS)}',
        ).pack(anchor='w', pady=(2, 10))

        columns = ('stage', 'name', 'status')
        tree = ttk.Treeview(body, columns=columns, show='headings', height=13, selectmode='browse')
        tree.heading('stage', text='단계')
        tree.heading('name', text='모습')
        tree.heading('status', text='상태')
        tree.column('stage', width=70, anchor='center', stretch=False)
        tree.column('name', width=230, anchor='w')
        tree.column('status', width=180, anchor='w')
        tree.pack(fill='both', expand=True)

        item_to_form: dict[str, str] = {}
        for form in ALL_GROWTH_FORMS:
            entry = catalog_entry(form.form_id)
            found = form.form_id in encountered
            if found:
                name = entry.public_name
                if entry.concept_approved:
                    status = '발견 · 스프라이트 준비중'
                else:
                    status = '발견 · 이미지 추후 업데이트'
            else:
                name = '???'
                status = '미발견' if entry.concept_approved else '미발견 · 빈 슬롯'
            iid = tree.insert('', 'end', values=(f'{form.tier + 1}단계', name, status))
            item_to_form[iid] = form.form_id

        detail = ttk.Label(
            body,
            text='항목을 선택하면 이 친구에 대한 짧은 힌트를 볼 수 있어요.',
            wraplength=600,
            justify='left',
        )
        detail.pack(fill='x', pady=(10, 0))

        def show_detail(_event=None) -> None:
            selected = tree.selection()
            if not selected:
                return
            form_id = item_to_form[selected[0]]
            entry = catalog_entry(form_id)
            if form_id not in encountered:
                detail.configure(text='아직 만나지 못한 몬스터다. 어떤 기록을 먹으면 만날 수 있을지는 비밀이다.')
                return
            art_note = (
                '현재 콘셉트는 확정됐고 실제 게임용 스프라이트를 준비 중이다.'
                if entry.concept_approved
                else '이 진화형의 이미지 자리는 확보되어 있으며 아트는 추후 업데이트된다.'
            )
            detail.configure(text=f'{entry.hint}\n{art_note}')

        tree.bind('<<TreeviewSelect>>', show_detail)
        children = tree.get_children()
        if children:
            tree.selection_set(children[0])
            show_detail()

    def open_profile_panel(self) -> None:
        ttk = self.ttk
        milestones = self.runtime.milestones.load()
        state = self.runtime.store.load_state()
        entry = catalog_entry(state.form_id)
        encountered = self.runtime.encyclopedia.encountered_ids()

        win = self._new_panel('이 친구', '410x360')
        body = ttk.Frame(win, padding=18)
        body.pack(fill='both', expand=True)

        ttk.Label(body, text=entry.public_name, font=('', 18, 'bold')).pack(anchor='w')
        ttk.Label(body, text=entry.hint, wraplength=365, justify='left').pack(anchor='w', pady=(4, 16))

        info = ttk.Frame(body)
        info.pack(fill='x')
        rows = (
            ('처음 만난 날', self._date_only(milestones.met_at)),
            ('첫 기록을 먹인 날', self._date_only(milestones.first_fed_at)),
            ('함께 쌓은 기록', f'{state.entry_count}개'),
            ('도감에서 만난 모습', f'{len(encountered)} / {len(ALL_GROWTH_FORMS)}'),
        )
        for row, (label, value) in enumerate(rows):
            ttk.Label(info, text=label).grid(row=row, column=0, sticky='w', pady=3)
            ttk.Label(info, text=value).grid(row=row, column=1, sticky='w', padx=(18, 0), pady=3)

        if not entry.concept_approved:
            ttk.Label(
                body,
                text='이 단계의 외형 이미지는 추후 업데이트될 예정이에요.',
                wraplength=365,
            ).pack(anchor='w', pady=(18, 0))
        ttk.Label(
            body,
            text='성장의 정확한 기준과 내부 점수는 보여주지 않아요. 남긴 기록이 쌓이면서 자연스럽게 모습이 달라집니다.',
            wraplength=365,
            justify='left',
        ).pack(anchor='w', pady=(12, 0))

    def _draw(self) -> None:
        """Vector fallback with grounded idle breathing.

        During idle the feet stay planted while only the body, face and bookmark rise/fall by a
        few pixels and stretch slightly. This reads as breathing rather than floating.
        """
        c = self.canvas
        c.delete('all')
        frame = self._frame
        state = self._pet_state
        eating = state == 'eat'
        walking = state == 'walk'
        sleeping = state == 'sleep'
        reading = state == 'read'
        talking = state == 'talk'
        idle = state == 'idle'
        x = 95
        base_y = 90

        if eating:
            bob = (0, -3, -5, -1, 2, -2)[frame % 6]
            squash = 5 if frame % 2 else 0
            stretch = 0
        elif walking:
            bob = (0, -2, 0, -2)[frame % 4]
            squash = 2 if frame % 2 else 0
            stretch = 0
        elif sleeping:
            bob = 2
            squash = 3
            stretch = 0
        elif idle:
            # 12 frames at the normal 150ms tick = ~1.8 seconds per quiet breath.
            bob = (0, 0, -1, -1, -2, -3, -3, -2, -1, -1, 0, 0)[frame % 12]
            stretch = (0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0)[frame % 12]
            squash = 0
        else:
            bob = (0, 0, -1, -2, -2, -1, 0, 0)[frame % 8]
            squash = 0
            stretch = 0
        y = base_y + bob

        outline = self.palette.outline
        paper = self.palette.paper
        shadow = self.palette.paper_shadow
        ink = self.palette.ink
        bookmark = self.palette.bookmark

        shadow_w = 44 + (4 if walking or eating else 0)
        c.create_oval(x-shadow_w, 151, x+shadow_w, 160, fill='#d8d2c8', outline='')

        # Idle breathing deliberately leaves feet on the floor; other actions may bounce them.
        foot_y = base_y if idle else y
        foot_shift = 5 if walking and frame % 2 else 0
        c.create_oval(x-30-foot_shift, foot_y+39, x-10-foot_shift, foot_y+53,
                      fill=shadow, outline=outline, width=2)
        c.create_oval(x+10+foot_shift, foot_y+39, x+30+foot_shift, foot_y+53,
                      fill=shadow, outline=outline, width=2)

        facing = self._motion.facing
        if facing >= 0:
            tail = (x+43, y+10, x+68, y+1, x+61, y+26, x+51, y+20)
        else:
            tail = (x-43, y+10, x-68, y+1, x-61, y+26, x-51, y+20)
        c.create_polygon(*tail, fill=bookmark, outline=outline, width=2)

        c.create_oval(
            x-52-squash, y-45-stretch+squash/2,
            x+52+squash, y+45+stretch-squash/2,
            fill=paper, outline=outline, width=3,
        )
        c.create_polygon(x-18, y-45-stretch, x+12, y-45-stretch,
                         x+24, y-28, x-6, y-31,
                         fill='#eee5cf', outline='#c9bda4', width=1)
        c.create_line(x-21, y+21, x+20, y+21, fill='#cfc4aa')
        c.create_line(x-16, y+27, x+15, y+27, fill='#d8cdb5')

        blink = idle and frame % 29 in {27, 28}
        if sleeping or blink:
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
        elif sleeping:
            c.create_arc(x-12, y+3, x+12, y+16, start=200, extent=140, style='arc', outline=ink, width=2)
            c.create_text(x+48, y-39, text='z', fill='#71685e', font=('', 10, 'bold'))
            if frame % 2:
                c.create_text(x+59, y-50, text='Z', fill='#8b8176', font=('', 8, 'bold'))
        elif reading:
            c.create_arc(x-20, y-1, x+20, y+18, start=205, extent=130, style='arc', outline=ink, width=2)
            c.create_polygon(
                x-34, y+14, x, y+22, x+34, y+14, x+31, y+39, x, y+32, x-31, y+39,
                fill='#fffaf0', outline=outline, width=2,
            )
            c.create_line(x, y+22, x, y+32, fill='#b9aa8d')
            c.create_line(x-24, y+23, x-7, y+27, fill='#c7baa2')
            c.create_line(x+7, y+27, x+24, y+23, fill='#c7baa2')
        elif talking:
            if frame % 2:
                c.create_oval(x-8, y+1, x+8, y+15, fill=ink, outline='')
            else:
                c.create_arc(x-18, y, x+18, y+18, start=200, extent=140, style='arc', outline=ink, width=3)
            c.create_oval(x+42, y-52, x+74, y-27, fill='#fffaf0', outline='#c9bda4', width=1)
            c.create_text(x+58, y-40, text='…', fill=ink, font=('', 10, 'bold'))
        else:
            c.create_arc(x-22, y, x+22, y+21, start=200, extent=140, style='arc', outline=ink, width=3)


def run_pet_v2(*, runtime_factory=bootstrap_runtime) -> int:
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
    DesktopPetWindowV2(runtime).run()
    return 0
