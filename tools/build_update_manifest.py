from __future__ import annotations

"""Build the small signed-by-hash update manifest consumed by the desktop.

This tool does not publish anything. CI/release automation can upload the generated JSON and the
installer to the same HTTPS release host. The desktop only checks this manifest after user action.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.services.update_check import parse_version
from bookeater.version import APP_VERSION


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validate_installer_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('installer URL must be public HTTPS without embedded credentials')
    return value


def build_manifest(*, installer: Path, installer_url: str, version: str, notes: str = '') -> dict[str, str]:
    if not installer.is_file():
        raise FileNotFoundError(installer)
    parse_version(version)
    url = validate_installer_url(installer_url)
    clean_notes = str(notes or '').strip()
    if len(clean_notes) > 4000:
        raise ValueError('notes are too long')
    return {
        'latest_version': version,
        'installer_url': url,
        'sha256': sha256_file(installer),
        'notes': clean_notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--installer', required=True, type=Path)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--version', default=APP_VERSION)
    parser.add_argument('--notes', default='')
    args = parser.parse_args()

    manifest = build_manifest(
        installer=args.installer,
        installer_url=args.url,
        version=args.version,
        notes=args.notes,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_name(args.output.name + '.tmp')
    temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
