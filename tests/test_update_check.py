from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.services.update_check import (
    UpdateChecker,
    UpdateManifestError,
    configured_update_checker,
    parse_version,
    update_manifest_endpoint,
)
from bookeater.version import APP_VERSION


class FakeResponse:
    def __init__(self, payload: object, headers=None):
        self.data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.headers = headers or {}

    def read(self, limit: int):
        return self.data[:limit]


def valid_manifest(version='0.1.0'):
    return {
        'latest_version': version,
        'installer_url': 'https://downloads.example.com/BookEater-Setup.exe',
        'sha256': 'a' * 64,
        'notes': '안전한 업데이트',
    }


def test_version_order_handles_prerelease_without_forcing_dev_above_release():
    assert parse_version('0.1.0-dev') < parse_version('0.1.0')
    assert parse_version('0.1.0') < parse_version('0.1.1-dev')
    assert not (parse_version('1.0.0') < parse_version('0.9.9'))


def test_update_check_only_reports_newer_manifest_and_never_downloads_installer():
    seen = {}

    def opener(request, timeout):
        seen['url'] = request.full_url
        seen['user_agent'] = request.headers.get('User-agent')
        return FakeResponse(valid_manifest('0.1.0'))

    checker = UpdateChecker('https://updates.example.com/latest.json', opener=opener)
    result = checker.check(current_version='0.1.0-dev')
    assert result.update_available is True
    assert result.manifest.installer_url.endswith('BookEater-Setup.exe')
    assert seen['url'] == 'https://updates.example.com/latest.json'
    assert 'BookEater/' in (seen['user_agent'] or '')


def test_same_or_older_version_is_not_an_update():
    checker = UpdateChecker(
        'https://updates.example.com/latest.json',
        opener=lambda request, timeout: FakeResponse(valid_manifest('0.1.0-dev')),
    )
    assert checker.check(current_version='0.1.0-dev').update_available is False


def test_manifest_requires_https_urls_and_sha256():
    bad_url = valid_manifest()
    bad_url['installer_url'] = 'http://downloads.example.com/setup.exe'
    with pytest.raises(UpdateManifestError):
        UpdateChecker(
            'https://updates.example.com/latest.json',
            opener=lambda request, timeout: FakeResponse(bad_url),
        ).fetch_manifest()

    bad_sha = valid_manifest()
    bad_sha['sha256'] = 'not-a-hash'
    with pytest.raises(UpdateManifestError):
        UpdateChecker(
            'https://updates.example.com/latest.json',
            opener=lambda request, timeout: FakeResponse(bad_sha),
        ).fetch_manifest()


def test_endpoint_file_and_environment_override_fail_closed(tmp_path):
    resources = tmp_path / 'resources'
    resources.mkdir()
    endpoint_file = resources / 'update_manifest_endpoint.txt'
    endpoint_file.write_text('# comment\nhttps://updates.example.com/latest.json\n', encoding='utf-8')
    assert update_manifest_endpoint(resource_root=tmp_path, environ={}) == 'https://updates.example.com/latest.json'
    assert update_manifest_endpoint(
        resource_root=tmp_path,
        environ={'BOOKEATER_UPDATE_MANIFEST': 'https://override.example.com/latest.json'},
    ) == 'https://override.example.com/latest.json'
    assert update_manifest_endpoint(
        resource_root=tmp_path,
        environ={'BOOKEATER_UPDATE_MANIFEST': 'http://evil.example.com/latest.json'},
    ) is None


def test_unconfigured_update_checker_is_cleanly_disabled(tmp_path):
    assert configured_update_checker(resource_root=tmp_path, environ={}) is None


def test_installer_and_python_version_sources_are_in_sync():
    iss = (ROOT / 'installer' / 'BookEater.iss').read_text(encoding='utf-8')
    assert f'#define MyAppVersion "{APP_VERSION}"' in iss
