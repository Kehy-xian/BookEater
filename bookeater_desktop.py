from __future__ import annotations

import json
import sys

from bookeater.desktop import run_desktop
from bookeater.pet_window_v11 import run_pet_v11
from bookeater.runtime import bootstrap_runtime
from bookeater.services.catalog import CatalogClient, configured_catalog_client
from bookeater.services.data_transfer import SEED_FORMAT, SEED_VERSION
from bookeater.services.single_instance import acquire_single_instance, windows_mutex_self_test


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


def _run_single_pet() -> int:
    try:
        guard = acquire_single_instance()
    except Exception:
        # Failing to create the mutex should fail closed: two simultaneous writers are riskier than
        # refusing one launch. Keep the message independent of the main runtime/database.
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk(); root.withdraw()
            messagebox.showerror('책먹는 몬스터', '중복 실행 방지 장치를 시작하지 못해 실행을 중단했어요.')
            root.destroy()
        except Exception:
            pass
        return 4
    if not guard.acquired:
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk(); root.withdraw()
            messagebox.showinfo('책먹는 몬스터', '책먹는 몬스터가 이미 실행 중이에요.')
            root.destroy()
        except Exception:
            pass
        return 0
    try:
        return run_pet_v11()
    finally:
        guard.close()


if __name__ == '__main__':
    if '--smoke' in sys.argv:
        raise SystemExit(_smoke())
    if '--mutex-smoke' in sys.argv:
        raise SystemExit(0 if windows_mutex_self_test() else 5)
    if '--full-window' in sys.argv:
        raise SystemExit(run_desktop())
    raise SystemExit(_run_single_pet())
