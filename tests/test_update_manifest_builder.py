from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

from tools.build_update_manifest import build_manifest
from bookeater.version import APP_VERSION


def test_manifest_builder_hashes_exact_installer_bytes(tmp_path):
    installer = tmp_path / 'BookEater-Setup.exe'
    installer.write_bytes(b'bookeater-installer-test-bytes')
    manifest = build_manifest(
        installer=installer,
        installer_url='https://downloads.example.com/BookEater-Setup.exe',
        version=APP_VERSION,
        notes='테스트',
    )
    assert manifest['latest_version'] == APP_VERSION
    assert manifest['sha256'] == hashlib.sha256(installer.read_bytes()).hexdigest()
    assert manifest['installer_url'].startswith('https://')


def test_manifest_builder_rejects_non_https_or_missing_installer(tmp_path):
    installer = tmp_path / 'BookEater-Setup.exe'
    installer.write_bytes(b'x')
    with pytest.raises(ValueError):
        build_manifest(
            installer=installer,
            installer_url='http://downloads.example.com/BookEater-Setup.exe',
            version=APP_VERSION,
        )
    with pytest.raises(FileNotFoundError):
        build_manifest(
            installer=tmp_path / 'missing.exe',
            installer_url='https://downloads.example.com/BookEater-Setup.exe',
            version=APP_VERSION,
        )
