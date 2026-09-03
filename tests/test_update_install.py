from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.services.update_check import UpdateManifest
from bookeater.services.update_install import (
    UpdateDownloadError,
    UpdateLaunchError,
    VerifiedInstaller,
    download_verified_installer,
    launch_verified_installer,
)


class ChunkedResponse:
    def __init__(
        self,
        data: bytes,
        *,
        declared_size: int | None = None,
        final_url: str = 'https://downloads.example.com/BookEater-Setup.exe',
    ):
        self.data = data
        self.offset = 0
        self.headers = {} if declared_size is None else {'Content-Length': str(declared_size)}
        self.final_url = final_url

    def read(self, limit: int) -> bytes:
        chunk = self.data[self.offset:self.offset + max(1, min(limit, 7))]
        self.offset += len(chunk)
        return chunk

    def geturl(self) -> str:
        return self.final_url


def manifest_for(data: bytes, *, version: str = '0.2.0') -> UpdateManifest:
    return UpdateManifest(
        version,
        'https://downloads.example.com/BookEater-Setup.exe',
        hashlib.sha256(data).hexdigest(),
        '안전 업데이트',
    )


def test_download_publishes_only_hash_verified_windows_executable(tmp_path):
    data = b'MZ' + b'bookeater-installer' * 5
    seen = {}

    def opener(request, timeout):
        seen['url'] = request.full_url
        seen['timeout'] = timeout
        return ChunkedResponse(data, declared_size=len(data))

    verified = download_verified_installer(
        manifest_for(data),
        updates_dir=tmp_path,
        opener=opener,
    )
    assert verified.path.name == 'BookEater-Setup-0.2.0.exe'
    assert verified.path.read_bytes() == data
    assert verified.sha256 == hashlib.sha256(data).hexdigest()
    assert verified.size_bytes == len(data)
    assert seen['url'].startswith('https://')
    assert not list(tmp_path.glob('*.download'))


def test_hash_mismatch_or_non_executable_never_leaves_installable_file(tmp_path):
    good = b'MZexpected'
    bad = b'MZtampered'
    with pytest.raises(UpdateDownloadError, match='SHA-256'):
        download_verified_installer(
            manifest_for(good),
            updates_dir=tmp_path,
            opener=lambda request, timeout: ChunkedResponse(bad),
        )
    assert not list(tmp_path.iterdir())

    html = b'<html>not an installer</html>'
    with pytest.raises(UpdateDownloadError, match='Windows executable'):
        download_verified_installer(
            manifest_for(html),
            updates_dir=tmp_path,
            opener=lambda request, timeout: ChunkedResponse(html),
        )
    assert not list(tmp_path.iterdir())


def test_declared_or_streamed_oversize_is_rejected_and_cleaned(tmp_path):
    data = b'MZ0123456789'
    with pytest.raises(UpdateDownloadError, match='size'):
        download_verified_installer(
            manifest_for(data),
            updates_dir=tmp_path,
            opener=lambda request, timeout: ChunkedResponse(data, declared_size=999),
            max_bytes=20,
        )
    with pytest.raises(UpdateDownloadError, match='maximum'):
        download_verified_installer(
            manifest_for(data),
            updates_dir=tmp_path,
            opener=lambda request, timeout: ChunkedResponse(data),
            max_bytes=8,
        )
    assert not list(tmp_path.iterdir())


def test_insecure_installer_redirect_is_rejected_and_cleaned(tmp_path):
    data = b'MZredirected-installer'
    with pytest.raises(UpdateDownloadError, match='redirect'):
        download_verified_installer(
            manifest_for(data),
            updates_dir=tmp_path,
            opener=lambda request, timeout: ChunkedResponse(
                data,
                final_url='http://evil.example.com/BookEater-Setup.exe',
            ),
        )
    assert not list(tmp_path.iterdir())


def test_matching_cached_installer_is_reused_without_network(tmp_path):
    data = b'MZcached-installer'
    path = tmp_path / 'BookEater-Setup-0.2.0.exe'
    path.write_bytes(data)

    def no_network(*args, **kwargs):
        raise AssertionError('verified cache should avoid another download')

    verified = download_verified_installer(
        manifest_for(data),
        updates_dir=tmp_path,
        opener=no_network,
    )
    assert verified.path == path


def test_launch_rechecks_file_and_never_uses_a_shell(tmp_path):
    data = b'MZlaunch-installer'
    path = tmp_path / 'BookEater-Setup-0.2.0.exe'
    path.write_bytes(data)
    verified = VerifiedInstaller(path, hashlib.sha256(data).hexdigest(), len(data), '0.2.0')
    calls = []

    def fake_popen(args, **kwargs):
        calls.append((args, kwargs))
        return object()

    launch_verified_installer(verified, platform='win32', popen=fake_popen)
    assert calls == [([str(path)], {'shell': False, 'close_fds': True})]

    path.write_bytes(data + b'tampered')
    with pytest.raises(UpdateLaunchError, match='changed'):
        launch_verified_installer(verified, platform='win32', popen=fake_popen)
    with pytest.raises(UpdateLaunchError, match='Windows'):
        launch_verified_installer(verified, platform='linux', popen=fake_popen)
