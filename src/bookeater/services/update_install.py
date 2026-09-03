from __future__ import annotations

"""Explicit, verified Windows-installer download and launch.

The update manifest is fetched separately.  This module only runs after a player chooses to
download an available update.  Bytes are written to a disposable ``updates`` directory, checked
against the manifest SHA-256, and atomically published.  Launch requires a second explicit player
confirmation in the UI and re-verifies the file immediately before execution.
"""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
from typing import Any, Callable
from urllib.request import Request, urlopen

from .update_check import UpdateManifest, _safe_https_url, _safe_response_url, parse_version
from ..version import APP_VERSION


MAX_INSTALLER_BYTES = 1024 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 1024 * 1024
_SHA256_RE = re.compile(r'^[0-9a-fA-F]{64}$')
_SAFE_VERSION_RE = re.compile(r'[^0-9A-Za-z.-]+')
_DOWNLOAD_LOCK = threading.Lock()


class UpdateDownloadError(RuntimeError):
    """The installer could not be downloaded or did not match the trusted manifest."""


class UpdateLaunchError(RuntimeError):
    """A verified installer could not be launched safely."""


@dataclass(frozen=True)
class VerifiedInstaller:
    path: Path
    sha256: str
    size_bytes: int
    version: str


def _installer_path(updates_dir: str | Path, version: str) -> Path:
    parse_version(version)
    safe_version = _SAFE_VERSION_RE.sub('-', version).strip('.-')
    if not safe_version:
        raise UpdateDownloadError('update version is not safe for a local filename')
    return Path(updates_dir) / f'BookEater-Setup-{safe_version}.exe'


def _sha256_file(path: Path, *, max_bytes: int = MAX_INSTALLER_BYTES) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open('rb') as stream:
            while True:
                chunk = stream.read(DOWNLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise UpdateDownloadError('installer exceeds the maximum allowed size')
                digest.update(chunk)
    except UpdateDownloadError:
        raise
    except OSError as exc:
        raise UpdateDownloadError('installer could not be read') from exc
    return digest.hexdigest(), size


def _validate_manifest(manifest: UpdateManifest) -> tuple[str, str]:
    try:
        parse_version(manifest.latest_version)
        url = _safe_https_url(manifest.installer_url, name='installer URL')
    except Exception as exc:
        raise UpdateDownloadError('update manifest is not safe to download') from exc
    expected = str(manifest.sha256 or '').strip().lower()
    if not _SHA256_RE.fullmatch(expected):
        raise UpdateDownloadError('update manifest has an invalid installer hash')
    return url, expected


def _verified_existing(path: Path, *, expected: str, version: str, max_bytes: int) -> VerifiedInstaller | None:
    if not path.is_file():
        return None
    try:
        actual, size = _sha256_file(path, max_bytes=max_bytes)
        if size > 0 and actual == expected:
            return VerifiedInstaller(path, actual, size, version)
    except UpdateDownloadError:
        pass
    try:
        path.unlink()
    except OSError:
        pass
    return None


def download_verified_installer(
    manifest: UpdateManifest,
    *,
    updates_dir: str | Path,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 45.0,
    max_bytes: int = MAX_INSTALLER_BYTES,
) -> VerifiedInstaller:
    """Download, hash-check and atomically retain the installer described by ``manifest``."""
    url, expected = _validate_manifest(manifest)
    max_bytes = max(1, int(max_bytes))
    destination = _installer_path(updates_dir, manifest.latest_version)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with _DOWNLOAD_LOCK:
        existing = _verified_existing(
            destination,
            expected=expected,
            version=manifest.latest_version,
            max_bytes=max_bytes,
        )
        if existing is not None:
            return existing

        temp = destination.with_name(
            f'.{destination.name}.{os.getpid()}-{threading.get_ident()}.download'
        )
        temp.unlink(missing_ok=True)
        request = Request(
            url,
            headers={
                'Accept': 'application/octet-stream',
                'User-Agent': f'BookEater/{APP_VERSION}',
            },
        )
        response = None
        try:
            response = opener(request, timeout=max(1.0, float(timeout)))
            try:
                _safe_response_url(response, url, name='final installer URL')
            except Exception as exc:
                raise UpdateDownloadError('installer redirect is not safe') from exc
            length = response.headers.get('Content-Length') if getattr(response, 'headers', None) else None
            if length is not None:
                try:
                    declared = int(length)
                except (TypeError, ValueError) as exc:
                    raise UpdateDownloadError('installer has an invalid Content-Length') from exc
                if declared < 1 or declared > max_bytes:
                    raise UpdateDownloadError('installer size is outside the allowed range')

            digest = hashlib.sha256()
            size = 0
            first = b''
            with temp.open('xb') as stream:
                while True:
                    chunk = response.read(DOWNLOAD_CHUNK_BYTES)
                    if not chunk:
                        break
                    if not isinstance(chunk, (bytes, bytearray)):
                        raise UpdateDownloadError('installer download returned invalid bytes')
                    if not first:
                        first = bytes(chunk[:2])
                    size += len(chunk)
                    if size > max_bytes:
                        raise UpdateDownloadError('installer exceeds the maximum allowed size')
                    stream.write(chunk)
                    digest.update(chunk)
                stream.flush()
                os.fsync(stream.fileno())

            if size < 2 or first != b'MZ':
                raise UpdateDownloadError('download is not a Windows executable')
            actual = digest.hexdigest()
            if actual != expected:
                raise UpdateDownloadError('installer SHA-256 does not match the update manifest')
            temp.replace(destination)
            return VerifiedInstaller(destination, actual, size, manifest.latest_version)
        except UpdateDownloadError:
            temp.unlink(missing_ok=True)
            raise
        except Exception as exc:
            temp.unlink(missing_ok=True)
            raise UpdateDownloadError('installer download failed') from exc
        finally:
            close = getattr(response, 'close', None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass


def launch_verified_installer(
    installer: VerifiedInstaller,
    *,
    platform: str | None = None,
    popen: Callable[..., Any] = subprocess.Popen,
) -> Any:
    """Re-check and launch one installer without a shell.  The caller closes the app afterward."""
    platform = sys.platform if platform is None else platform
    if not str(platform).startswith('win'):
        raise UpdateLaunchError('installer launch is available only on Windows')
    path = Path(installer.path)
    if path.suffix.lower() != '.exe' or not path.is_file():
        raise UpdateLaunchError('verified installer is missing')
    try:
        actual, size = _sha256_file(path)
    except UpdateDownloadError as exc:
        raise UpdateLaunchError('installer could not be re-verified') from exc
    if actual != installer.sha256 or size != installer.size_bytes:
        raise UpdateLaunchError('installer changed after download')
    try:
        return popen([str(path)], shell=False, close_fds=True)
    except Exception as exc:
        raise UpdateLaunchError('installer could not be started') from exc
