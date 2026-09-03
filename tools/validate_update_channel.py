from __future__ import annotations

"""Reject update-channel rollback and mutation of an already published version."""

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.services.update_check import parse_version


def validate_transition(existing: dict[str, Any], candidate: dict[str, Any]) -> None:
    existing_version = parse_version(str(existing.get('latest_version') or ''))
    candidate_version = parse_version(str(candidate.get('latest_version') or ''))
    if candidate_version < existing_version:
        raise ValueError('update channel rollback is forbidden')
    same_version = not (existing_version < candidate_version) and not (
        candidate_version < existing_version
    )
    if same_version and existing != candidate:
        raise ValueError('an already published version manifest is immutable')


def _load(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError(f'manifest must be a JSON object: {path}')
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('existing')
    parser.add_argument('candidate')
    args = parser.parse_args()
    validate_transition(_load(args.existing), _load(args.candidate))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
