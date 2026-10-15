import logging
import os
import time
from collections.abc import Callable
from concurrent.futures import Executor, ThreadPoolExecutor

from userbot.commands import COMMANDS
from userbot.config import Settings
from userbot.router import Router
from userbot.store import Store
from userbot.vk import CHAT_PEER_OFFSET, Incoming, VkClient

log = logging.getLogger("userbot-vk")

RECONNECT_SECONDS = 5.0
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


# messages.getById на каждое сообщение каждой беседы забивал бы лимит VK (~3 запроса в секунду на токен),
# поэтому полное сообщение читается только для команд, игнора и журнала
def process(vk, router: Router, incoming: Incoming, log_messages: bool) -> None:
    if not log_messages and not router.wants(incoming.text, incoming.author):
        return
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


def listen_forever(vk, router: Router, pool: Executor, log_messages: bool,
                   sleep: Callable[[float], None] = time.sleep) -> None:
    while True:
        try:
            for incoming in vk.listen():
                pool.submit(process, vk, router, incoming, log_messages)
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
        listen_forever(vk, router, pool, settings.log_messages)


if __name__ == "__main__":
    run()
