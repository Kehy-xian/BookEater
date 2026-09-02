from __future__ import annotations

"""Shared interactive launch guard.

Every user-facing entry point must pass through this helper so the desktop pet, the full-window
UI, Python module execution and Windows auto-start cannot become concurrent writers of one local
profile.
"""

from collections.abc import Callable

from .services.single_instance import acquire_single_instance


def _show_message(kind: str, text: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        if kind == 'error':
            messagebox.showerror('책먹는 몬스터', text)
        else:
            messagebox.showinfo('책먹는 몬스터', text)
        root.destroy()
    except Exception:
        # The guard itself is more important than a notification. Headless/dev launches may have
        # no usable Tk display, in which case returning the safe exit code is sufficient.
        pass


def run_guarded(callback: Callable[[], int]) -> int:
    try:
        guard = acquire_single_instance()
    except Exception:
        _show_message('error', '중복 실행 방지 장치를 시작하지 못해 실행을 중단했어요.')
        return 4

    if not guard.acquired:
        _show_message('info', '책먹는 몬스터가 이미 실행 중이에요.')
        return 0

    try:
        return int(callback())
    finally:
        guard.close()
