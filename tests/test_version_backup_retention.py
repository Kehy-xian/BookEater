from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.services.version_backup import prune_version_backups


def test_retention_keeps_newest_version_backups_only(tmp_path):
    folder = tmp_path / 'backups' / 'version-upgrades'
    folder.mkdir(parents=True)
    files = []
    for i in range(8):
        path = folder / f'pre-version-test-{i:02d}.sqlite3'
        path.write_bytes(str(i).encode())
        # deterministic ascending mtime
        stamp = 1_700_000_000 + i
        path.touch()
        import os
        os.utime(path, (stamp, stamp))
        files.append(path)

    removed = prune_version_backups(tmp_path, keep=5)
    assert len(removed) == 3
    assert [p.name for p in sorted(folder.glob('*.sqlite3'))] == [p.name for p in files[-5:]]


def test_retention_does_not_touch_seed_backups_or_unrelated_files(tmp_path):
    version_folder = tmp_path / 'backups' / 'version-upgrades'
    version_folder.mkdir(parents=True)
    for i in range(3):
        (version_folder / f'pre-version-{i}.sqlite3').write_bytes(b'x')
    seed = tmp_path / 'backups' / 'pre-reset-keep.bookeater-seed'
    seed.parent.mkdir(parents=True, exist_ok=True)
    seed.write_text('seed', encoding='utf-8')
    unrelated = version_folder / 'README.txt'
    unrelated.write_text('keep', encoding='utf-8')

    prune_version_backups(tmp_path, keep=1)
    assert seed.exists()
    assert unrelated.exists()
