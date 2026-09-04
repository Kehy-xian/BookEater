from __future__ import annotations

"""Isolated birth-to-new-cycle persistence smoke for packaged builds.

The smoke deliberately uses a temporary profile and deterministic state transitions. Route
selection itself is covered by the growth resolver tests; this check protects the cross-store
contract that is easiest to miss in a packaged Windows build: final locking, memoir creation,
archive preservation and safe active-creature reset.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from bookeater.game.growth_routes import get_growth_form, valid_direct_transition
from bookeater.runtime import bootstrap_runtime, resource_root


_ROUTE = ('starter', 'route_a', 'route_a1', 'route_a1_alpha')


def force_lifecycle_transition(runtime, feed_id: str, target_form: str, entry_count: int) -> None:
    """Advance one valid route edge for isolated automated or visual lifecycle checks."""
    previous = runtime.store.load_state()
    if not valid_direct_transition(previous.form_id, target_form):
        raise RuntimeError(f'invalid smoke transition: {previous.form_id} -> {target_form}')
    runtime.journal.attach_note(
        runtime.store,
        feed_id,
        f'생애주기 테스트 기록 {entry_count}',
        book_id='lifecycle-book',
        progress_text=f'{entry_count}쪽',
    )
    form = get_growth_form(target_form)
    runtime.store.commit_fed(
        feed_id=feed_id,
        expected_revision=previous.revision,
        entry_count=entry_count,
        current_base=previous.current_base,
        stage=form.tier,
        species=target_form,
        stats={'사유': float(entry_count)},
        public_payload={
            'feed_id': feed_id,
            'status': 'fed',
            'message': '생애주기 테스트',
            'growth': None,
        },
        model_version='lifecycle-smoke',
        nutrition_policy='lifecycle-smoke',
        form_id=target_form,
        recent_stats={'사유': float(entry_count)},
    )
    runtime.memoirs.record_evolution(previous.form_id, target_form, entry_count)
    runtime.encyclopedia.unlock(target_form)


def lifecycle_smoke(*, resources: str | Path | None = None) -> dict[str, Any]:
    """Run the complete persistence lifecycle without reading or changing the live profile."""
    with TemporaryDirectory(prefix='bookeater-lifecycle-smoke-') as temp:
        smoke_dir = Path(temp)
        runtime = bootstrap_runtime(
            data_dir=smoke_dir,
            resources=Path(resources) if resources is not None else resource_root(),
        )
        runtime.settings.set('monster_name', '테스트콩')
        runtime.settings.set('favorite_book_title', '어린 왕자')
        runtime.settings.set_bool('intro_seen', True)
        runtime.journal.add_book(
            'lifecycle-book', '생애주기 시험용 책', author='BookEater', status='completed'
        )

        for index, target in enumerate(_ROUTE[1:], start=1):
            force_lifecycle_transition(runtime, f'lifecycle-{index}', target, index * 20)

        final_before = runtime.store.load_state()
        runtime.journal.attach_note(
            runtime.store,
            'lifecycle-locked',
            '최종 성장 뒤에도 기록은 안전하게 저장된다.',
            book_id='lifecycle-book',
            progress_text='완독',
        )
        locked_outcome = runtime.feed_service.retry('lifecycle-locked')
        final_after = runtime.store.load_state()
        final_frozen = (
            locked_outcome.status == 'fed'
            and final_after.form_id == final_before.form_id
            and final_after.entry_count == final_before.entry_count
            and final_after.stats == final_before.stats
        )

        memoir = runtime.memoirs.create_current_book(
            monster_name='테스트콩',
            final_form_id=final_after.form_id,
            favorite_book='어린 왕자',
        )
        notes_before = runtime.store.count_notes()
        books_before = len(runtime.journal.list_books())
        memoir_records = len(memoir.payload.get('records', []))

        runtime.memoirs.begin_new_cycle()
        restarted = runtime.store.load_state()
        report = {
            'isolated_profile': runtime.data_dir == smoke_dir,
            'route_complete': final_before.form_id == _ROUTE[-1] and final_before.stage == 3,
            'final_growth_frozen': final_frozen,
            'memoir_created': memoir.final_form_id == _ROUTE[-1] and memoir_records == notes_before,
            'reading_archive_preserved': (
                runtime.store.count_notes() == notes_before
                and len(runtime.journal.list_books()) == books_before
            ),
            'memoir_preserved': any(
                book.memoir_id == memoir.memoir_id for book in runtime.memoirs.list_books()
            ),
            'new_cycle_started': (
                restarted.form_id == 'starter'
                and restarted.stage == 0
                and restarted.entry_count == 0
                and runtime.settings.get('monster_name') is None
                and runtime.settings.get('favorite_book_title') is None
                and not runtime.settings.get_bool('intro_seen', False)
            ),
        }
        report['ok'] = all(report.values())
        return report
