from __future__ import annotations

from bookeater.services.single_instance import (
    MUTEX_PREFIX,
    SingleInstanceGuard,
    acquire_single_instance,
    instance_mutex_name,
    windows_mutex_self_test,
)


def test_mutex_name_is_stable_scoped_and_does_not_leak_identity():
    first = instance_mutex_name(user_hint='reader@example', data_dir_hint=r'C:\Users\reader\BookEater')
    same = instance_mutex_name(user_hint='reader@example', data_dir_hint=r'C:\Users\reader\BookEater')
    other_user = instance_mutex_name(user_hint='other', data_dir_hint=r'C:\Users\reader\BookEater')
    other_data = instance_mutex_name(user_hint='reader@example', data_dir_hint=r'D:\Portable\BookEater')

    assert first == same
    assert first.startswith(MUTEX_PREFIX)
    assert first != other_user
    assert first != other_data
    assert 'reader' not in first.lower()
    assert 'users' not in first.lower()
    assert len(first) == len(MUTEX_PREFIX) + 24


def test_non_windows_development_runs_are_not_locked():
    guard = acquire_single_instance(platform='linux')
    assert guard.acquired is True
    assert guard.handle is None
    guard.close()


def test_guard_closes_native_handle_once():
    class FakeKernel32:
        def __init__(self):
            self.closed = []

        def CloseHandle(self, handle):
            self.closed.append(handle)
            return True

    kernel = FakeKernel32()
    guard = SingleInstanceGuard(True, handle=1234, kernel32=kernel)
    guard.close()
    guard.close()

    assert kernel.closed == [1234]
    assert guard.handle is None


def test_context_manager_releases_handle():
    class FakeKernel32:
        def __init__(self):
            self.closed = []

        def CloseHandle(self, handle):
            self.closed.append(handle)
            return True

    kernel = FakeKernel32()
    with SingleInstanceGuard(True, handle=77, kernel32=kernel) as guard:
        assert guard.acquired is True
        assert guard.handle == 77

    assert kernel.closed == [77]
    assert guard.handle is None


def test_mutex_self_test_is_noop_success_off_windows(monkeypatch):
    monkeypatch.setattr('bookeater.services.single_instance.sys.platform', 'linux')
    assert windows_mutex_self_test() is True
