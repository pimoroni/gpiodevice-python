import os
import select
import sys
import threading
from unittest import mock

import pytest


@pytest.fixture
def gpiodevice_mod():
    """Import gpiodevice with gpiod (and gpiod.line) mocked so watch.py loads."""
    sys.modules["gpiod"] = mock.MagicMock()
    sys.modules["gpiod.line"] = mock.MagicMock()
    for name in [m for m in sys.modules if m == "gpiodevice" or m.startswith("gpiodevice.")]:
        del sys.modules[name]
    import gpiodevice
    yield gpiodevice
    sys.modules.pop("gpiod.line", None)


class FakeEvent:
    def __init__(self, line_offset):
        self.line_offset = line_offset


class FakeRequest:
    """A gpiod.LineRequest stand-in backed by an os.pipe, so select/poll work for real."""

    def __init__(self):
        self._r, self._w = os.pipe()
        os.set_blocking(self._r, False)
        self.fd = self._r
        self._events = []
        self.released = False

    def fire(self, *offsets):
        self._events.extend(FakeEvent(o) for o in offsets)
        os.write(self._w, b"x")

    def read_edge_events(self):
        try:
            os.read(self._r, 4096)
        except BlockingIOError:
            pass
        events, self._events = self._events, []
        return events

    def wait_edge_events(self, timeout):
        seconds = timeout.total_seconds() if timeout is not None else None
        readable, _, _ = select.select([self._r], [], [], seconds)
        return bool(readable)

    def release(self):
        self.released = True


def test_watch_dispatches_per_line(gpiodevice_mod):
    req = FakeRequest()
    seen = []
    done = threading.Event()

    def handler(event):
        seen.append(event.line_offset)
        done.set()

    with gpiodevice_mod.Watch(req, {5: handler}):
        req.fire(5)
        assert done.wait(1.0)
    assert seen == [5]


def test_watch_single_callable_for_all_lines(gpiodevice_mod):
    req = FakeRequest()
    seen = []
    done = threading.Event()

    def handler(event):
        seen.append(event.line_offset)
        if len(seen) == 2:
            done.set()

    with gpiodevice_mod.Watch(req, handler):
        req.fire(2, 9)
        assert done.wait(1.0)
    assert sorted(seen) == [2, 9]


def test_watch_ignores_unhandled_line(gpiodevice_mod):
    req = FakeRequest()
    seen = []
    with gpiodevice_mod.Watch(req, {5: seen.append}):
        req.fire(6)  # no handler for line 6
        threading.Event().wait(0.15)
    assert seen == []


def test_watch_stop_joins_thread(gpiodevice_mod):
    req = FakeRequest()
    watch = gpiodevice_mod.Watch(req, lambda e: None).start()
    assert watch._thread.is_alive()
    watch.stop()
    assert watch._thread is None


def test_watch_close_releases_when_managed(gpiodevice_mod):
    req = FakeRequest()
    gpiodevice_mod.Watch(req, lambda e: None, manage_request=True).start().close()
    assert req.released is True

    req2 = FakeRequest()
    gpiodevice_mod.Watch(req2, lambda e: None).start().close()
    assert req2.released is False  # caller owns it


def test_wait_for_edge_returns_event(gpiodevice_mod):
    req = FakeRequest()
    req.fire(7)
    event = gpiodevice_mod.wait_for_edge(req, timeout=1.0)
    assert event.line_offset == 7


def test_wait_for_edge_filters_by_line(gpiodevice_mod):
    req = FakeRequest()
    req.fire(3)  # not the line we want; only event available
    assert gpiodevice_mod.wait_for_edge(req, line=4, timeout=0.05) is None


def test_wait_for_edge_timeout(gpiodevice_mod):
    req = FakeRequest()
    assert gpiodevice_mod.wait_for_edge(req, timeout=0.05) is None
    with pytest.raises(TimeoutError):
        gpiodevice_mod.wait_for_edge(req, timeout=0.05, raise_on_timeout=True)
