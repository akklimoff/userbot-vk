import threading
import time
from collections import deque
from collections.abc import Iterator
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
        return self._api.messages.getById(message_ids=message_id)["items"][0]

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

    def user(self, user_id: int | str, fields: str | None = None) -> dict | None:
        users = self.users([user_id], fields)
        return users[0] if users else None

    def users(self, user_ids: list[int | str], fields: str | None = None) -> list[dict]:
        try:
            return self._api.users.get(user_ids=user_ids, **({"fields": fields} if fields else {}))
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

    def privacy_value(self, key: str) -> dict:
        for setting in self._api.account.getPrivacySettings()["settings"]:
            if setting["key"] == key:
                return setting.get("value") or {}
        return {}

    def set_privacy_allowed(self, key: str, owners: list[int]) -> None:
        self._api.account.setPrivacy(key=key, value=",".join(map(str, owners)) if owners else "only_me")

    def upload_voice(self, path: str, peer_id: int) -> str:
        doc = self._upload.audio_message(path, peer_id=peer_id)["audio_message"]
        return attachment_id("audio_message", doc)

    def upload_photo(self, path: str, peer_id: int) -> str:
        return attachment_id("photo", self._upload.photo_messages(path, peer_id=peer_id)[0])

    def upload_graffiti(self, path: str, peer_id: int) -> str:
        return attachment_id("graffiti", self._upload.graffiti(path, peer_id=peer_id)["graffiti"])
