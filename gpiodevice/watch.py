"""Edge / interrupt helpers.

gpiod v2 exposes edge events on a ``LineRequest`` (``wait_edge_events`` /
``read_edge_events``), but the async "watch a pin and call me back" pattern -- polling the
request fd, filtering events by line offset, and starting/stopping a background thread
cleanly -- is fiddly and easy to get subtly wrong. This is one canonical implementation.

Three entry points:

* :func:`wait_for_edge` -- block until an edge arrives (or a timeout elapses).
* :class:`Watch` -- a background thread that dispatches per-line callbacks on each edge.
* :func:`watch_pin` -- convenience: request a single pin and return a started :class:`Watch`.
"""
import select
import threading
import time
from datetime import timedelta

import gpiod
from gpiod.line import Bias, Edge


def _as_timedelta(value):
    if value is None or isinstance(value, timedelta):
        return value
    return timedelta(seconds=value)


def wait_for_edge(request, line=None, timeout=None, raise_on_timeout=False):
    """Block until an edge event arrives on ``request``, then return it.

    :param request: a ``gpiod.LineRequest`` configured with edge detection.
    :param line: if given, only events on this line offset are returned.
    :param timeout: seconds (or a ``timedelta``) to wait; ``None`` waits forever.
    :param raise_on_timeout: raise ``TimeoutError`` instead of returning ``None``.
    :returns: the first matching ``gpiod`` edge event, or ``None`` on timeout.
    """
    td = _as_timedelta(timeout)
    end = None if td is None else time.monotonic() + td.total_seconds()

    while True:
        remaining = None if end is None else _as_timedelta(max(0.0, end - time.monotonic()))
        if not request.wait_edge_events(remaining):
            if raise_on_timeout:
                raise TimeoutError("Timed out waiting for edge event")
            return None
        for event in request.read_edge_events():
            if line is None or event.line_offset == line:
                return event
        if end is not None and time.monotonic() >= end:
            if raise_on_timeout:
                raise TimeoutError("Timed out waiting for edge event")
            return None


class Watch:
    """Watch a ``gpiod.LineRequest`` for edge events on a background thread.

    ``handlers`` is either a single callable (invoked for every edge) or a mapping of
    ``{line_offset: callable}``. Each handler is called with the ``gpiod`` edge event.

    The request must already be configured with edge detection. If ``manage_request`` is
    True the request is released when the watch is closed (as with :func:`watch_pin`);
    otherwise the caller keeps ownership.
    """

    def __init__(self, request, handlers, poll_interval=0.1, manage_request=False):
        self._request = request
        if callable(handlers):
            self._default = handlers
            self._handlers = {}
        else:
            self._default = None
            self._handlers = dict(handlers)
        self._poll_interval = poll_interval
        self._manage_request = manage_request
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        """Start the background thread (idempotent)."""
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="gpiodevice-watch", daemon=True)
        self._thread.start()
        return self

    def _run(self):
        poll = select.poll()
        poll.register(self._request.fd, select.POLLIN)
        timeout_ms = int(self._poll_interval * 1000)
        while not self._stop.is_set():
            if not poll.poll(timeout_ms):
                continue
            for event in self._request.read_edge_events():
                handler = self._default or self._handlers.get(event.line_offset)
                if handler is not None:
                    handler(event)

    def stop(self, timeout=1.0):
        """Signal the thread to stop and join it."""
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout)
        return self

    def close(self):
        """Stop the thread and, if we own the request, release it."""
        self.stop()
        if self._manage_request:
            try:
                self._request.release()
            except Exception:
                pass

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.close()
        return False


def watch_pin(pin, edge=Edge.FALLING, bias=Bias.AS_IS, debounce=None, callback=None, consumer="watch"):
    """Request a single ``pin`` for edge detection and return a started :class:`Watch`.

    :param pin: an int line offset or a named pin (e.g. ``"GPIO4"``), as for ``get_pin``.
    :param edge: which edge(s) to detect (``gpiod.line.Edge``).
    :param bias: line bias (``gpiod.line.Bias``).
    :param debounce: debounce period in seconds (or a ``timedelta``).
    :param callback: called with the edge event on each edge.
    """
    from . import get_pin  # local import avoids an import cycle with the package __init__

    settings = gpiod.LineSettings(
        edge_detection=edge,
        bias=bias,
        debounce_period=_as_timedelta(debounce) or timedelta(0),
    )
    request, offset = get_pin(pin, consumer, settings)
    return Watch(request, {offset: callback}, manage_request=True).start()
