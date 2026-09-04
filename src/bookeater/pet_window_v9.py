from __future__ import annotations

"""Desktop-pet V9: portable reading/genetics export, planting and safe reset."""

from datetime import datetime
from pathlib import Path
import threading

from .pet_window_v8 import DesktopPetWindowV8
from .runtime import BookEaterRuntime, RuntimeStartupError, bootstrap_runtime
from .services.data_transfer import SeedFormatError, read_seed
from .services.profile_transfer import export_profile_seed, plant_profile_seed, reset_profile
from .services.windows_autostart import can_enable_autostart, is_autostart_enabled, set_autostart


class DesktopPetWindowV9(DesktopPetWindowV8):
    def __init__(self, runtime: BookEaterRuntime):
        self._recovery_busy = False
        self._data_mutating = False
        super().__init__(runtime)
        data_menu = self.tk.Menu(self.menu, tearoff=0)
        data_menu.add_command(label='기록 내보내기', command=self.export_reading_seed)
        data_menu.add_command(label='기록 읽기', command=self.plant_reading_seed)
        data_menu.add_separator()
        data_menu.add_command(label='전체 초기화', command=self.reset_reading_profile)
        end = self.menu.index('end')
        self.menu.insert_cascade(end, label='데이터 관리', menu=data_menu)

    def _retry_pending_async(self) -> None:
        if self._data_mutating:
            return
        self._recovery_busy = True

        def work() -> None:
            try:
                outcomes = self.runtime.feed_service.retry_pending(limit=25)
                self._result_queue.put(('recovery', outcomes))
            except Exception:
                pass
            finally:
                self._recovery_busy = False

        threading.Thread(target=work, name='bookeater-pet-recovery', daemon=True).start()

    def _data_action_available(self) -> bool:
        if self._busy or self._recovery_busy or self._data_mutating:
            from tkinter import messagebox
            messagebox.showinfo(
                '책먹는 몬스터',
                '지금 기록을 처리하고 있어요. 처리가 끝난 뒤 다시 시도해 주세요.',
                parent=self.root,
            )
            return False
        return True

    def _destructive_data_action_available(self) -> bool:
        if not self._data_action_available():
            return False
        try:
            draft = self.runtime.drafts.load()
        except Exception:
            draft = None
        if draft is not None:
            from tkinter import messagebox
            messagebox.showinfo(
                '미제출 초안이 있어요',
                '아직 몬스터에게 먹이지 않은 기록 초안이 남아 있어요.\n'
                '기록 읽기나 전체 초기화 전에 초안을 먼저 먹이거나 비워 주세요.',
                parent=self.root,
            )
            return False
        return True

    def _refresh_after_profile_change(self) -> None:
        self._visual_revision = -1
        self._book_display_to_id.clear()
        if self._sprite_cache is not None:
            self._sprite_cache.invalidate()
        state = self.runtime.store.load_state()
        self._visual_form_id = state.form_id
        self._pet_state = 'idle'
        self._draw()

    def export_reading_seed(self) -> None:
        if not self._data_action_available():
            return
        from tkinter import filedialog, messagebox

        suggested = f"책먹는몬스터-기록-{datetime.now().strftime('%Y%m%d')}.bookeater-seed"
        chosen = filedialog.asksaveasfilename(
            parent=self.root,
            title='기록 내보내기',
            defaultextension='.bookeater-seed',
            initialfile=suggested,
            filetypes=(('책먹는 몬스터 기록', '*.bookeater-seed'), ('모든 파일', '*.*')),
        )
        if not chosen:
            return
        destination = Path(chosen)
        try:
            summary = export_profile_seed(self.runtime.database_path, destination)
        except Exception:
            messagebox.showerror(
                '내보내기 실패',
                '기록 파일을 만들지 못했어요. 기존 기록은 변경하지 않았습니다.',
                parent=self.root,
            )
            return
        draft_note = '\n미제출 초안은 아직 기록이 아니므로 내보내기에 포함되지 않습니다.' if self.runtime.drafts.load() else ''
        messagebox.showinfo(
            '내보내기 완료',
            f'책 {summary.book_count}권 · 기록 {summary.note_count}개를 저장했어요.\n'
            f'현재 유전정보·성장흐름·도감·친밀도도 함께 들어 있습니다.{draft_note}\n\n'
            f'{destination}',
            parent=self.root,
        )

    def plant_reading_seed(self) -> None:
        if not self._destructive_data_action_available():
            return
        from tkinter import filedialog, messagebox

        chosen = filedialog.askopenfilename(
            parent=self.root,
            title='심을 기록 파일 선택',
            filetypes=(('책먹는 몬스터 기록', '*.bookeater-seed'), ('모든 파일', '*.*')),
        )
        if not chosen:
            return
        try:
            _payload, summary = read_seed(chosen)
        except SeedFormatError:
            messagebox.showerror(
                '심을 수 없는 파일',
                '파일이 손상되었거나 이 버전에서 읽을 수 없는 기록입니다.\n현재 기록은 변경하지 않았습니다.',
                parent=self.root,
            )
            return
        except Exception:
            messagebox.showerror('심기 실패', '파일을 읽지 못했어요. 현재 기록은 변경하지 않았습니다.', parent=self.root)
            return

        ok = messagebox.askyesno(
            '기록 읽기',
            f'책 {summary.book_count}권 · 기록 {summary.note_count}개가 들어 있는 기록을 심을까요?\n\n'
            '현재 책·독서기록·유전정보·성장·도감·친밀도는 이 파일의 내용으로 교체됩니다.\n'
            '자동실행과 화면 설정, 교체 아트는 그대로 유지됩니다.\n'
            '교체 직전에 현재 상태를 자동 백업합니다.',
            parent=self.root,
        )
        if not ok:
            return

        self._data_mutating = True
        try:
            imported, backup = plant_profile_seed(
                self.runtime.database_path, chosen, data_dir=self.runtime.data_dir,
            )
            self._refresh_after_profile_change()
        except Exception:
            messagebox.showerror(
                '심기 실패',
                '기록을 심는 중 문제가 생겼어요. 변경 작업은 취소되었으며 기존 DB는 보존됩니다.',
                parent=self.root,
            )
            return
        finally:
            self._data_mutating = False

        messagebox.showinfo(
            '기록 읽기 완료',
            f'책 {imported.book_count}권 · 기록 {imported.note_count}개와 성장 정보를 심었어요.\n'
            f'교체 전 상태 백업: {backup}',
            parent=self.root,
        )

    def reset_reading_profile(self) -> None:
        if not self._destructive_data_action_available():
            return
        from tkinter import messagebox

        confirmed = messagebox.askyesno(
            '전체 초기화',
            '처음 만난 날로 되돌아가시겠습니까?\n'
            '유전정보와 독서기록을 포함한 모든 상태가 초기화됩니다.\n\n'
            '실행 직전에 독서기록과 몬스터 상태 복구용 파일을 자동으로 만듭니다.\n'
            '계속할까요?',
            parent=self.root,
        )
        if not confirmed:
            return

        self._data_mutating = True
        autostart_was_enabled = can_enable_autostart() and is_autostart_enabled()
        try:
            if autostart_was_enabled:
                set_autostart(False)
            backup = reset_profile(
                self.runtime.database_path, data_dir=self.runtime.data_dir, reset_settings=True,
            )
            self._set_pet_scale(0.75, persist=False)
            self._refresh_after_profile_change()
            if hasattr(self, '_rebuild_main_menu'):
                self._rebuild_main_menu()
        except Exception:
            if autostart_was_enabled:
                try:
                    set_autostart(True)
                except Exception:
                    pass
            messagebox.showerror(
                '초기화 실패',
                '초기화 중 문제가 생겼어요. 변경 작업은 취소되었으며 기존 기록을 유지합니다.',
                parent=self.root,
            )
            return
        finally:
            self._data_mutating = False

        messagebox.showinfo(
            '초기화 완료',
            '새 글씨알 상태로 돌아왔어요.\n'
            f'초기화 전 백업: {backup}',
            parent=self.root,
        )
        # A full reset returns to the actual first meeting, not merely an empty roaming state.
        self.root.after(120, self._open_birth_onboarding)


def run_pet_v9(*, runtime_factory=bootstrap_runtime) -> int:
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
    DesktopPetWindowV9(runtime).run()
    return 0
