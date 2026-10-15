import logging
import os
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from concurrent.futures import Executor, ThreadPoolExecutor

from userbot.commands import COMMANDS
from userbot.config import Settings
from userbot.router import Router
from userbot.store import Store
from userbot.vk import CHAT_PEER_OFFSET, Incoming, VkClient

log = logging.getLogger("userbot-vk")

RECONNECT_SECONDS = 5.0
STRANGER_COMMANDS_PER_MINUTE = 5
STRANGER_BACKLOG = 32
ATTACHMENT_NAMES = {
    "audio_message": "голосовое сообщение",
    "audio": "аудиозапись",
    "sticker": "стикер",
    "photo": "фотография",
    "video": "видео",
    "doc": "документ",
    "graffiti": "граффити",
    "link": "ссылка",
}


def summary(message: dict) -> str:
    text = " ".join((message.get("text") or "").split())
    if text:
        return text
    attachments = message.get("attachments") or []
    if attachments:
        kind = attachments[0]["type"]
        return f"• {ATTACHMENT_NAMES.get(kind, kind)}"
    return "• пересланные сообщения"


def log_message(vk, message: dict) -> None:
    peer_id = message["peer_id"]
    place = vk.peer_title(peer_id) + ("" if peer_id > CHAT_PEER_OFFSET else " [ЛС]")
    log.info("[%s / %s]: %s", place, vk.peer_title(message["from_id"]), summary(message))


class RateLimit:
    def __init__(self, per_minute: int, now: Callable[[], float] = time.monotonic):
        self._per_minute = per_minute
        self._now = now
        self._hits: dict[int | None, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, author: int | None) -> bool:
        now = self._now()
        with self._lock:
            hits = self._hits[author]
            while hits and now - hits[0] > 60:
                hits.popleft()
            if len(hits) >= self._per_minute:
                return False
            hits.append(now)
            return True


# Все запросы токена идут через одну блокировку vk_api (~3 в секунду): getById на каждое сообщение каждой беседы
# и команды чужих без лимита задержали бы команды владельца на минуты и привели бы к капче
class Dispatcher:
    def __init__(self, vk, router: Router, pool: Executor, log_messages: bool,
                 limit: RateLimit | None = None, backlog: int = STRANGER_BACKLOG):
        self._vk = vk
        self._router = router
        self._pool = pool
        self._log_messages = log_messages
        self._limit = limit or RateLimit(STRANGER_COMMANDS_PER_MINUTE)
        self._backlog = threading.BoundedSemaphore(backlog)

    def dispatch(self, incoming: Incoming) -> None:
        if self._vk.sent_by_bot(incoming.random_id):
            return
        wanted = self._router.wants(incoming.text, incoming.author, incoming.peer_id)
        if not wanted and not self._log_messages:
            return
        if self._router.privileged(incoming.author):
            self._pool.submit(process, self._vk, self._router, incoming, self._log_messages)
            return
        if wanted and not self._limit.allow(incoming.author):
            log.info("Команды от %s чаще %d в минуту, пропускаю", incoming.author, STRANGER_COMMANDS_PER_MINUTE)
            return
        if not self._backlog.acquire(blocking=False):
            log.warning("Очередь чужих сообщений переполнена, сообщение %s пропущено", incoming.message_id)
            return
        self._pool.submit(process, self._vk, self._router, incoming, self._log_messages) \
            .add_done_callback(lambda _: self._backlog.release())


def process(vk, router: Router, incoming: Incoming, log_messages: bool) -> None:
    try:
        message = vk.message(incoming.message_id)
    except Exception:
        log.exception("Не удалось прочитать сообщение %s", incoming.message_id)
        return
    if log_messages:
        try:
            log_message(vk, message)
        except Exception:
            log.warning("Не удалось записать в журнал сообщение %s", incoming.message_id)
    try:
        router.handle(message)
    except Exception:
        log.exception("Ошибка обработки сообщения %s", incoming.message_id)


def listen_forever(vk, dispatcher: Dispatcher, sleep: Callable[[float], None] = time.sleep) -> None:
    while True:
        try:
            for incoming in vk.listen():
                dispatcher.dispatch(incoming)
        except Exception:
            log.exception("Long poll упал, переподключение через %.0f с", RECONNECT_SECONDS)
        sleep(RECONNECT_SECONDS)


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings()
    vk = VkClient(settings.vk_token)
    store = Store(os.path.join(settings.state_dir, "data.json"))
    router = Router(vk, store, COMMANDS, vk.me_id)
    log.info("userbot-vk запущен, id=%s", vk.me_id)
    with ThreadPoolExecutor(max_workers=settings.workers) as pool:
        listen_forever(vk, Dispatcher(vk, router, pool, settings.log_messages))


if __name__ == "__main__":
    run()
