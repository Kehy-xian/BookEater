from __future__ import annotations

import json
import sys

from bookeater.desktop import run_desktop
from bookeater.pet_window_v11 import run_pet_v11
from bookeater.runtime import bootstrap_runtime
from bookeater.services.catalog import CatalogClient, configured_catalog_client
from bookeater.services.data_transfer import SEED_FORMAT, SEED_VERSION


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
        'form_id': state.form_id,
        'species': view.species,
    }
    print(json.dumps(payload, ensure_ascii=True))
    return 0 if all((
        payload['db_ok'], payload['model_loaded'], payload['analysis_is_mapping'],
        payload['journal_ready'], payload['encyclopedia_ready'], payload['settings_ready'],
        payload['care_ready'], payload['drafts_ready'], payload['seed_transfer_ready'],
        payload['catalog_module_ready'],
    )) else 3


if __name__ == '__main__':
    if '--smoke' in sys.argv:
        raise SystemExit(_smoke())
    if '--full-window' in sys.argv:
        raise SystemExit(run_desktop())
    raise SystemExit(run_pet_v11())
