import threading
import time
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import requests
import vk_api
from vk_api import VkUpload
from vk_api.longpoll import VkEventType, VkLongPoll
from vk_api.utils import get_random_id

from userbot.attachments import attachment_id

CHAT_PEER_OFFSET = 2_000_000_000
HTTP_TIMEOUT = 30
TITLE_TTL_SECONDS = 3600
REMEMBERED_SENT = 5000
# vk_api по умолчанию ходит с v=5.92, где у кружочка нет video.type=video_message и его не отличить от обычного видео
MESSAGES_API_VERSION = "5.131"
MAX_FRIEND_REQUESTS = 1000
FRIENDS_PAGE = 5000
# узлы pu.vk.ru временами массово отвечают 504 HTML-страницей; новый upload_url обычно ведёт на другой узел
UPLOAD_ATTEMPTS = 5
# слишком много запросов, флуд-контроль, ограничение аккаунта
THROTTLE_CODES = frozenset({6, 9, 29})


class Throttled(Exception):
    """VK просит притормозить: продолжать — значит нарваться на ограничение аккаунта."""


@contextmanager
def throttle_aware():
    try:
        yield
    except vk_api.Captcha as e:
        raise Throttled("капча") from e
    except vk_api.ApiError as e:
        if e.code in THROTTLE_CODES:
            raise Throttled(str(e)) from e
        raise


# vk_api не задаёт таймаут и держит общую блокировку на время запроса: одно зависшее соединение остановило бы бота
class TimeoutSession(requests.Session):
    def request(self, *args, **kwargs):
        kwargs.setdefault("timeout", HTTP_TIMEOUT)
        return super().request(*args, **kwargs)


@dataclass(frozen=True)
class Incoming:
    message_id: int
    peer_id: int
    text: str
    author: int | None
    random_id: int = 0


class VkClient:
    def __init__(self, token: str):
        self._session = vk_api.VkApi(token=token, session=TimeoutSession())
        self._api = self._session.get_api()
        self._upload = VkUpload(self._session)
        self._upload.http = TimeoutSession()
        self._longpoll: VkLongPoll | None = None
        self._sent = deque(maxlen=REMEMBERED_SENT)
        self._sent_lock = threading.Lock()
        self._titles: dict[int, tuple[float, str]] = {}
        self.me_id: int = self._api.users.get()[0]["id"]

    # один VkLongPoll на всё время работы: после сетевой ошибки он продолжает с прежнего ts и не теряет события
    def listen(self) -> Iterator[Incoming]:
        if self._longpoll is None:
            self._longpoll = VkLongPoll(self._session)
        for event in self._longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW:
                author = self.me_id if event.from_me else getattr(event, "user_id", None)
                yield Incoming(event.message_id, event.peer_id, getattr(event, "message", "") or "", author,
                               int(getattr(event, "random_id", 0) or 0))

    def message(self, message_id: int) -> dict:
        return self._api.messages.getById(message_ids=message_id, v=MESSAGES_API_VERSION)["items"][0]

    # random_id запоминается до отправки, чтобы long poll не успел вернуть сообщение раньше, чем оно станет «своим»
    def send(self, peer_id: int, text: str | None = None, attachment: str | None = None,
             reply_to: int | None = None, expire_ttl: int | None = None, sticker_id: int | None = None) -> int:
        random_id = get_random_id()
        with self._sent_lock:
            self._sent.append(random_id)
        params = {"message": text, "attachment": attachment, "reply_to": reply_to, "expire_ttl": expire_ttl,
                  "sticker_id": sticker_id}
        return self._api.messages.send(peer_id=peer_id, random_id=random_id,
                                       **{k: v for k, v in params.items() if v is not None})

    def sent_by_bot(self, random_id: int | None) -> bool:
        if not random_id:
            return False
        with self._sent_lock:
            return random_id in self._sent

    def edit(self, peer_id: int, message_id: int, text: str) -> None:
        self._api.messages.edit(peer_id=peer_id, message_id=message_id, message=text)

    def delete(self, message_ids: list[int], for_all: bool) -> None:
        self._api.messages.delete(message_ids=message_ids, delete_for_all=int(for_all))

    def history(self, peer_id: int, start_message_id: int, count: int = 200) -> list[dict]:
        return self._api.messages.getHistory(peer_id=peer_id, start_message_id=start_message_id,
                                             count=count)["items"]

    def user(self, user_id: int | str) -> dict | None:
        users = self.users([user_id])
        return users[0] if users else None

    def users(self, user_ids: list[int | str]) -> list[dict]:
        try:
            return self._api.users.get(user_ids=user_ids)
        except vk_api.ApiError:
            return []

    def peer_title(self, peer_id: int) -> str:
        cached = self._titles.get(peer_id)
        if cached and time.monotonic() - cached[0] < TITLE_TTL_SECONDS:
            return cached[1]
        if peer_id > CHAT_PEER_OFFSET:
            title = self._api.messages.getChatPreview(peer_id=peer_id)["preview"]["title"]
        elif peer_id < 0:
            title = self._api.groups.getById(group_id=-peer_id)[0]["name"]
        else:
            user = self._api.users.get(user_ids=peer_id)[0]
            title = f"{user['first_name']} {user['last_name']}"
        self._titles[peer_id] = (time.monotonic(), title)
        return title

    def upload_voice(self, path: str, peer_id: int) -> str:
        for attempt in range(1, UPLOAD_ATTEMPTS + 1):
            try:
                doc = self._upload.audio_message(path, peer_id=peer_id)["audio_message"]
                return attachment_id("audio_message", doc)
            except requests.RequestException:
                if attempt == UPLOAD_ATTEMPTS:
                    raise

    # заявку от удалённой или заблокированной страницы VK принять не даёт ([177]), а каждая попытка съедает
    # лимит действий с друзьями
    def friend_requests(self, outgoing: bool) -> list[int]:
        with throttle_aware():
            items = self._api.friends.getRequests(out=int(outgoing), need_viewed=1, extended=1,
                                                  count=MAX_FRIEND_REQUESTS)["items"]
        return [item["user_id"] for item in items if not item.get("deactivated")]

    def add_friend(self, user_id: int) -> None:
        with throttle_aware():
            self._api.friends.add(user_id=user_id)

    def delete_friend(self, user_id: int) -> None:
        with throttle_aware():
            self._api.friends.delete(user_id=user_id)

    def dead_friends(self) -> list[int]:
        dead, offset = [], 0
        with throttle_aware():
            while True:
                page = self._api.friends.get(fields="deactivated", count=FRIENDS_PAGE, offset=offset)
                dead += [friend["id"] for friend in page["items"] if friend.get("deactivated")]
                offset += FRIENDS_PAGE
                if offset >= page["count"]:
                    return dead

    def set_online(self) -> None:
        with throttle_aware():
            self._api.account.setOnline(voip=0)
