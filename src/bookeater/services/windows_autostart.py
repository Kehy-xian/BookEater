from __future__ import annotations

import os
import sys

_RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
_VALUE_NAME = 'BookEater'


def can_enable_autostart() -> bool:
    if not sys.platform.startswith('win'):
        return False
    if getattr(sys, 'frozen', False):
        return True
    return os.environ.get('BOOKEATER_ALLOW_DEV_AUTOSTART') == '1'


def startup_command(executable: str | None = None) -> str:
    exe = str(executable or sys.executable).strip().strip('"')
    if not exe:
        raise ValueError('executable path is required')
    return f'"{exe}"'


def set_autostart(enabled: bool) -> None:
    if not sys.platform.startswith('win'):
        raise RuntimeError('Windows autostart is available only on Windows')
    if enabled and not can_enable_autostart():
        raise RuntimeError('autostart is disabled for non-packaged development runs')

    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, _VALUE_NAME)
            except FileNotFoundError:
                pass


def is_autostart_enabled() -> bool:
    if not sys.platform.startswith('win'):
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_QUERY_VALUE) as key:
            value, _kind = winreg.QueryValueEx(key, _VALUE_NAME)
            return str(value).strip() == startup_command()
    except FileNotFoundError:
        return False
