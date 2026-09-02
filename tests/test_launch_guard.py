from __future__ import annotations

from bookeater import launch_guard
from bookeater.services.single_instance import SingleInstanceGuard


def test_run_guarded_executes_callback_and_releases_guard(monkeypatch):
    closed = []

    class Guard(SingleInstanceGuard):
        def close(self):
            closed.append(True)
            self.handle = None

    monkeypatch.setattr(launch_guard, 'acquire_single_instance', lambda: Guard(True, handle=1))
    called = []

    result = launch_guard.run_guarded(lambda: called.append(True) or 7)

    assert result == 7
    assert called == [True]
    assert closed == [True]


def test_run_guarded_skips_callback_when_another_instance_exists(monkeypatch):
    monkeypatch.setattr(launch_guard, 'acquire_single_instance', lambda: SingleInstanceGuard(False))
    monkeypatch.setattr(launch_guard, '_show_message', lambda *args: None)
    called = []

    result = launch_guard.run_guarded(lambda: called.append(True) or 1)

    assert result == 0
    assert called == []


def test_run_guarded_fails_closed_when_mutex_creation_fails(monkeypatch):
    def fail():
        raise OSError('mutex unavailable')

    monkeypatch.setattr(launch_guard, 'acquire_single_instance', fail)
    monkeypatch.setattr(launch_guard, '_show_message', lambda *args: None)
    called = []

    result = launch_guard.run_guarded(lambda: called.append(True) or 1)

    assert result == 4
    assert called == []
