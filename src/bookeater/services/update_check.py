from __future__ import annotations

"""Opt-in, read-only update checking for BookEater.

The desktop never self-replaces its executable and never modifies the user database here.  A user
must explicitly press the update-check button, and a newer installer is only opened in the default
browser after another explicit click.  Production manifests must use HTTPS; localhost HTTP is
accepted for development tests.
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ..version import APP_VERSION

UPDATE_MANIFEST_ENV = 'BOOKEATER_UPDATE_MANIFEST'
UPDATE_ENDPOINT_FILE = Path('resources/update_manifest_endpoint.txt')
MAX_MANIFEST_BYTES = 128 * 1024
_SHA256_RE = re.compile(r'^[0-9a-fA-F]{64}$')
_VERSION_RE = re.compile(r'^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$')


class UpdateUnavailable(RuntimeError):
    pass


class UpdateManifestError(RuntimeError):
    pass


@dataclass(frozen=True)
class ParsedVersion:
    major: int
    minor: int
    patch: int
    prerelease: tuple[tuple[int, int | str], ...]

    def _key(self):
        # Stable releases sort after prereleases with the same numeric triplet.
        return (self.major, self.minor, self.patch, 1 if not self.prerelease else 0, self.prerelease)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, ParsedVersion):
            return NotImplemented
        return self._key() < other._key()


@dataclass(frozen=True)
class UpdateManifest:
    latest_version: str
    installer_url: str
    sha256: str
    notes: str


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: str
    manifest: UpdateManifest

    @property
    def update_available(self) -> bool:
        return parse_version(self.current_version) < parse_version(self.manifest.latest_version)


def parse_version(value: str) -> ParsedVersion:
    match = _VERSION_RE.fullmatch(str(value or '').strip())
    if not match:
        raise ValueError(f'invalid app version: {value!r}')
    pre: list[tuple[int, int | str]] = []
    raw_pre = match.group(4)
    if raw_pre:
        for token in raw_pre.split('.'):
            if token.isdigit():
                pre.append((0, int(token)))
            else:
                pre.append((1, token.lower()))
    return ParsedVersion(int(match.group(1)), int(match.group(2)), int(match.group(3)), tuple(pre))


def _safe_https_url(value: Any, *, name: str, allow_local_http: bool = True) -> str:
    text = str(value or '').strip()
    parsed = urlparse(text)
    if parsed.username or parsed.password or not parsed.netloc:
        raise UpdateManifestError(f'invalid {name}')
    host = (parsed.hostname or '').lower()
    local = host in {'localhost', '127.0.0.1', '::1'}
    if parsed.scheme != 'https' and not (allow_local_http and parsed.scheme == 'http' and local):
        raise UpdateManifestError(f'{name} must use HTTPS')
    return text


def update_manifest_endpoint(
    *,
    resource_root: str | Path,
    environ: dict[str, str] | None = None,
) -> str | None:
    env = os.environ if environ is None else environ
    override = str(env.get(UPDATE_MANIFEST_ENV, '') or '').strip()
    if override:
        try:
            return _safe_https_url(override, name='update manifest endpoint')
        except UpdateManifestError:
            return None

    path = Path(resource_root) / UPDATE_ENDPOINT_FILE
    if not path.is_file():
        return None
    try:
        for raw in path.read_text(encoding='utf-8').splitlines():
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            return _safe_https_url(line, name='update manifest endpoint')
    except (OSError, UnicodeDecodeError, UpdateManifestError):
        return None
    return None


@dataclass(frozen=True)
class UpdateChecker:
    endpoint: str
    opener: Callable[..., Any] = urlopen
    timeout: float = 6.0

    def __post_init__(self) -> None:
        object.__setattr__(self, 'endpoint', _safe_https_url(self.endpoint, name='update manifest endpoint'))

    def fetch_manifest(self) -> UpdateManifest:
        request = Request(
            self.endpoint,
            headers={'Accept': 'application/json', 'User-Agent': f'BookEater/{APP_VERSION}'},
        )
        try:
            response = self.opener(request, timeout=max(1.0, float(self.timeout)))
            length = response.headers.get('Content-Length') if getattr(response, 'headers', None) else None
            if length and int(length) > MAX_MANIFEST_BYTES:
                raise UpdateManifestError('update manifest is too large')
            raw = response.read(MAX_MANIFEST_BYTES + 1)
        except UpdateManifestError:
            raise
        except Exception as exc:
            raise UpdateUnavailable('update server could not be reached') from exc
        if len(raw) > MAX_MANIFEST_BYTES:
            raise UpdateManifestError('update manifest is too large')
        try:
            payload = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UpdateManifestError('update manifest is invalid JSON') from exc
        if not isinstance(payload, dict):
            raise UpdateManifestError('update manifest must be an object')

        latest = str(payload.get('latest_version') or '').strip()
        try:
            parse_version(latest)
        except ValueError as exc:
            raise UpdateManifestError('update manifest has invalid latest_version') from exc
        installer_url = _safe_https_url(payload.get('installer_url'), name='installer URL')
        sha256 = str(payload.get('sha256') or '').strip().lower()
        if not _SHA256_RE.fullmatch(sha256):
            raise UpdateManifestError('update manifest has invalid sha256')
        notes = str(payload.get('notes') or '').strip()
        if len(notes) > 4000:
            raise UpdateManifestError('update notes are too long')
        return UpdateManifest(latest, installer_url, sha256, notes)

    def check(self, *, current_version: str = APP_VERSION) -> UpdateCheckResult:
        # Validate our own version too, so a packaging/version drift fails closed rather than
        # producing a misleading update result.
        parse_version(current_version)
        return UpdateCheckResult(current_version, self.fetch_manifest())


def configured_update_checker(
    *,
    resource_root: str | Path,
    environ: dict[str, str] | None = None,
) -> UpdateChecker | None:
    endpoint = update_manifest_endpoint(resource_root=resource_root, environ=environ)
    if not endpoint:
        return None
    try:
        return UpdateChecker(endpoint)
    except UpdateManifestError:
        return None
