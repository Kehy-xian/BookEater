from __future__ import annotations

"""Per-user single-instance guard for the Windows desktop pet.

Auto-start and a manual shortcut can otherwise launch two pets against the same local profile.
Windows uses a named mutex. Non-Windows development runs are deliberately unrestricted.
"""

from dataclasses import dataclass
import ctypes
import getpass
import hashlib
import os
import sys
from typing import Any

ERROR_ALREADY_EXISTS = 183
MUTEX_PREFIX = 'Local\\BookEater-'


def instance_mutex_name(*, user_hint: str | None = None, data_dir_hint: str | None = None) -> str:
    # Scope the mutex to the current Windows logon session (Local\) and profile location. Hashing
    # avoids exposing a username/path in the kernel object name and supports test/dev data dirs.
    user = str(user_hint if user_hint is not None else getpass.getuser())
    data = str(data_dir_hint if data_dir_hint is not None else os.environ.get('BOOKEATER_DATA_DIR', 'default'))
    digest = hashlib.sha256(f'{user}\0{data}'.encode('utf-8', 'replace')).hexdigest()[:24]
    return MUTEX_PREFIX + digest


@dataclass
class SingleInstanceGuard:
    acquired: bool
    handle: int | None = None
    kernel32: Any | None = None

    def close(self) -> None:
        if self.handle and self.kernel32 is not None:
            try:
                self.kernel32.CloseHandle(self.handle)
            finally:
                self.handle = None

    def __enter__(self) -> 'SingleInstanceGuard':
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def acquire_single_instance(
    *,
    name: str | None = None,
    platform: str | None = None,
) -> SingleInstanceGuard:
    platform = sys.platform if platform is None else platform
    if not str(platform).startswith('win'):
        return SingleInstanceGuard(True)

    mutex_name = name or instance_mutex_name()
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel32.CreateMutexW
    create.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    create.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_bool

    ctypes.set_last_error(0)
    handle = create(None, False, mutex_name)
    if not handle:
        raise OSError(ctypes.get_last_error(), 'CreateMutexW failed')
    already = ctypes.get_last_error() == ERROR_ALREADY_EXISTS
    if already:
        kernel32.CloseHandle(handle)
        return SingleInstanceGuard(False)
    return SingleInstanceGuard(True, int(handle), kernel32)


def windows_mutex_self_test() -> bool:
    """Packaged CI helper: the second acquisition of one name must be rejected on Windows."""
    if not sys.platform.startswith('win'):
        return True
    name = instance_mutex_name(user_hint='ci-self-test', data_dir_hint=str(os.getpid()))
    first = acquire_single_instance(name=name)
    try:
        if not first.acquired:
            return False
        second = acquire_single_instance(name=name)
        try:
            return not second.acquired
        finally:
            second.close()
    finally:
        first.close()
