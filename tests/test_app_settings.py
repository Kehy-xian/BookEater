from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.services.windows_autostart import startup_command
from bookeater.storage.settings import AppSettingsStore


def test_settings_bool_roundtrip_survives_reopen(tmp_path):
    db = tmp_path / 'game.sqlite3'
    first = AppSettingsStore(db)
    assert first.get_bool('intro_seen', False) is False
    first.set_bool('intro_seen', True)
    first.set_bool('intro_drop_enabled', False)

    second = AppSettingsStore(db)
    assert second.get_bool('intro_seen') is True
    assert second.get_bool('intro_drop_enabled', True) is False


def test_startup_command_quotes_paths_with_spaces():
    assert startup_command(r'C:\Program Files\BookEater\BookEater.exe') == (
        '"C:\\Program Files\\BookEater\\BookEater.exe"'
    )


def test_settings_clear_restores_missing_key_defaults(tmp_path):
    settings = AppSettingsStore(tmp_path / 'game.sqlite3')
    settings.set_bool('intro_drop_enabled', False)
    settings.set_bool('autostart_enabled', True)
    settings.clear()
    assert settings.get_bool('intro_drop_enabled', True) is True
    assert settings.get('autostart_enabled') is None
