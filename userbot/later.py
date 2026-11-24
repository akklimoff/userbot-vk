import heapq
import itertools
import logging
import threading
import time
from collections.abc import Callable

log = logging.getLogger("userbot-vk")

_pending: list[tuple[float, int, Callable[[], None]]] = []
_changed = threading.Condition()
_order = itertools.count()
_worker: threading.Thread | None = None


# один поток на все отложенные действия: по таймеру на каждое потоки упёрлись бы в pids_limit контейнера
def run_later(delay: float, action: Callable[[], None]) -> None:
    global _worker
    with _changed:
        heapq.heappush(_pending, (time.monotonic() + delay, next(_order), action))
        if _worker is None:
            _worker = threading.Thread(target=_run, name="later", daemon=True)
            _worker.start()
        _changed.notify()


def _run() -> None:
    while True:
        with _changed:
            while not _pending or _pending[0][0] > time.monotonic():
                _changed.wait(_pending[0][0] - time.monotonic() if _pending else None)
            action = heapq.heappop(_pending)[2]
        try:
            action()
        except Exception:
            log.exception("Отложенное действие упало")
