from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.validate_update_channel import validate_transition


def manifest(version: str, *, sha256: str = 'a' * 64) -> dict[str, str]:
    return {
        'latest_version': version,
        'installer_url': f'https://downloads.example.com/{version}/BookEater-Setup.exe',
        'sha256': sha256,
        'notes': version,
    }


def test_newer_channel_version_is_allowed():
    validate_transition(manifest('0.1.0-beta.1'), manifest('0.1.0-beta.2'))
    validate_transition(manifest('0.1.0-beta.2'), manifest('0.1.0'))


def test_channel_rollback_is_rejected():
    with pytest.raises(ValueError, match='rollback'):
        validate_transition(manifest('0.2.0'), manifest('0.1.9'))


def test_same_version_is_idempotent_but_cannot_be_replaced():
    published = manifest('0.1.0-beta.1')
    validate_transition(published, dict(published))
    with pytest.raises(ValueError, match='immutable'):
        validate_transition(published, manifest('0.1.0-beta.1', sha256='b' * 64))


def test_release_workflow_never_clobbers_published_assets():
    workflow = (ROOT / '.github' / 'workflows' / 'windows-release.yml').read_text(encoding='utf-8')
    assert '--clobber' not in workflow
    assert 'release already exists; published version assets are immutable' in workflow
    assert 'validate_update_channel.py' in workflow
    assert 'group: bookeater-release-channel' in workflow
    assert 'release trigger commit $env:GITHUB_SHA is not current source head' in workflow
    assert 'git/matching-refs/tags/$tag' in workflow
    assert 'Verify production catalog contract' in workflow
    assert 'PRODUCTION_CATALOG_OK' in workflow
