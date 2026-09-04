from __future__ import annotations

import json
import sys

from bookeater.desktop import run_desktop
from bookeater.launch_guard import run_guarded
from bookeater.pet_window_v12 import run_pet_v12
from bookeater.runtime import bootstrap_runtime
from bookeater.services.catalog import CatalogClient, configured_catalog_client
from bookeater.services.data_transfer import SEED_FORMAT, SEED_VERSION
from bookeater.services.lifecycle_smoke import lifecycle_smoke
from bookeater.services.single_instance import windows_mutex_self_test
from bookeater.services.update_install import download_verified_installer, launch_verified_installer


def _smoke() -> int:
    """Headless packaged-runtime check used by Windows CI."""
    runtime = bootstrap_runtime()
    analysis = runtime.analyzer.analyze('주인공의 선택이 옳았는지 오래 생각했다.')
    view = runtime.feed_service.current_view()
    state = runtime.store.load_state()
    catalog = configured_catalog_client({})
    payload = {
        'db_ok': runtime.database_path.exists(),
        'model_loaded': runtime.analyzer.loaded,
        'analysis_is_mapping': isinstance(analysis, dict),
        'journal_ready': runtime.journal is not None,
        'encyclopedia_ready': runtime.encyclopedia is not None,
        'settings_ready': runtime.settings is not None,
        'care_ready': runtime.care is not None,
        'drafts_ready': runtime.drafts is not None,
        'seed_transfer_ready': SEED_FORMAT == 'bookeater.reading-seed' and SEED_VERSION >= 1,
        # Both states are valid: an unreleased/local build may have no proxy, while a release build
        # may bundle a public HTTPS endpoint. The secret upstream key never belongs in this binary.
        'catalog_module_ready': catalog is None or isinstance(catalog, CatalogClient),
        'catalog_configured': catalog is not None,
        'verified_update_ready': callable(download_verified_installer) and callable(launch_verified_installer),
        'form_id': state.form_id,
        'species': view.species,
    }
    print(json.dumps(payload, ensure_ascii=True))
    return 0 if all((
        payload['db_ok'], payload['model_loaded'], payload['analysis_is_mapping'],
        payload['journal_ready'], payload['encyclopedia_ready'], payload['settings_ready'],
        payload['care_ready'], payload['drafts_ready'], payload['seed_transfer_ready'],
        payload['catalog_module_ready'],
        payload['verified_update_ready'],
    )) else 3


def _lifecycle_smoke() -> int:
    """Exercise the full persistent monster cycle in a disposable profile."""
    payload = lifecycle_smoke()
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    return 0 if payload.get('ok') else 6


if __name__ == '__main__':
    if '--smoke' in sys.argv:
        raise SystemExit(_smoke())
    if '--mutex-smoke' in sys.argv:
        raise SystemExit(0 if windows_mutex_self_test() else 5)
    if '--lifecycle-smoke' in sys.argv:
        raise SystemExit(_lifecycle_smoke())
    if '--full-window' in sys.argv:
        raise SystemExit(run_guarded(run_desktop))
    raise SystemExit(run_guarded(run_pet_v12))
