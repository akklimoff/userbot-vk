from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache

import vk_api
from vk_api import VkUpload
from vk_api.longpoll import VkEventType, VkLongPoll
from vk_api.utils import get_random_id

from userbot.attachments import attachment_id

CHAT_PEER_OFFSET = 2_000_000_000


@dataclass(frozen=True)
class Incoming:
    message_id: int
    text: str
    author: int | None


class VkClient:
    def __init__(self, token: str):
        self._session = vk_api.VkApi(token=token)
        self._api = self._session.get_api()
        self._upload = VkUpload(self._session)
        self.me_id: int = self._api.users.get()[0]["id"]

    def listen(self) -> Iterator[Incoming]:
        for event in VkLongPoll(self._session).listen():
            if event.type == VkEventType.MESSAGE_NEW:
                author = self.me_id if event.from_me else getattr(event, "user_id", None)
                yield Incoming(event.message_id, getattr(event, "message", "") or "", author)

    def message(self, message_id: int) -> dict:
        return self._api.messages.getById(message_ids=message_id)["items"][0]

    def send(self, peer_id: int, text: str | None = None, attachment: str | None = None,
             reply_to: int | None = None, forward: str | None = None, expire_ttl: int | None = None,
             sticker_id: int | None = None) -> int:
        params = {"message": text, "attachment": attachment, "reply_to": reply_to, "forward_messages": forward,
                  "expire_ttl": expire_ttl, "sticker_id": sticker_id}
        return self._api.messages.send(peer_id=peer_id, random_id=get_random_id(),
                                       **{k: v for k, v in params.items() if v is not None})

    def edit(self, peer_id: int, message_id: int, text: str) -> None:
        self._api.messages.edit(peer_id=peer_id, message_id=message_id, message=text)

    def delete(self, message_ids: list[int], for_all: bool) -> None:
        self._api.messages.delete(message_ids=message_ids, delete_for_all=int(for_all))

    def history(self, peer_id: int, start_message_id: int, count: int = 200) -> list[dict]:
        return self._api.messages.getHistory(peer_id=peer_id, start_message_id=start_message_id,
                                             count=count)["items"]

    def user(self, user_id: int | str, fields: str | None = None) -> dict | None:
        try:
            users = self._api.users.get(user_ids=user_id, **({"fields": fields} if fields else {}))
        except vk_api.ApiError:
            return None
        return users[0] if users else None

    @lru_cache(maxsize=1024)
    def peer_title(self, peer_id: int) -> str:
        if peer_id > CHAT_PEER_OFFSET:
            return self._api.messages.getChatPreview(peer_id=peer_id)["preview"]["title"]
        if peer_id < 0:
            return self._api.groups.getById(group_id=-peer_id)[0]["name"]
        user = self._api.users.get(user_ids=peer_id)[0]
        return f"{user['first_name']} {user['last_name']}"

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

