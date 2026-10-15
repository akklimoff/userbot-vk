import logging
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from userbot.safety import looks_like_command
from userbot.store import Store

log = logging.getLogger("userbot-vk")

ERROR = "❗ |"
INVALID = "⚠️ |"
PROCESS = "⚡ |"
SUCCESS = "✅ |"
SUCCESS_NO = "❎ |"
# пустой символ: VK не даёт отредактировать сообщение в пустую строку
BLANK = "&#13;"


class Abort(Exception):
    """Команда уже сообщила пользователю, почему не выполнилась."""


@dataclass(frozen=True)
class Command:
    names: tuple[str, ...]
    run: Callable[["Context"], None]
    description: str
    owner_only: bool = False


@dataclass
class Context:
    vk: object
    store: Store
    owner_id: int
    message: dict
    commands: Sequence[Command] = field(default=())
    sleep: Callable[[float], None] = time.sleep
    triggers_command: Callable[[str], bool] = lambda _: False

    @property
    def args(self) -> list[str]:
        return self.message["text"].split()

    @property
    def peer_id(self) -> int:
        return self.message["peer_id"]

    @property
    def from_id(self) -> int:
        return self.message["from_id"]

    @property
    def is_owner(self) -> bool:
        return self.from_id == self.owner_id

    @property
    def reply_message(self) -> dict | None:
        return self.message.get("reply_message")

    @property
    def for_all(self) -> bool:
        return self.peer_id != self.from_id

    def rest(self, skip: int) -> str:
        parts = self.message["text"].split(None, skip)
        return parts[skip] if len(parts) > skip else ""

    def is_command_like(self, text: str | None) -> bool:
        words = (text or "").split()
        return looks_like_command(text) or bool(words) and self.triggers_command(words[0].lower())

    # бот пишет от лица владельца, и long poll вернёт ему же его сообщение как команду владельца
    def post(self, text: str | None = None, **params) -> bool:
        if self.is_command_like(text):
            log.warning("Сообщение в %s похоже на команду бота и не отправлено", self.peer_id)
            return False
        self.vk.send(self.peer_id, text, **params)
        return True

    def send(self, text: str | None = None, reply: bool = True, **params) -> bool:
        return self.post(text, reply_to=self.message["id"] if reply else None, **params)

    def edit(self, text: str) -> None:
        self.vk.edit(self.peer_id, self.message["id"], text)

    def delete(self) -> None:
        self.vk.delete([self.message["id"]], self.for_all)

    def flash(self, text: str, seconds: float = 3) -> None:
        self.edit(text)
        self.sleep(seconds)
        self.delete()

    def answer(self, text: str) -> None:
        """Владельцу — правкой его же сообщения, остальным — ответом."""
        if self.is_owner:
            self.edit(text)
        else:
            self.send(text)

    def fail(self, text: str, seconds: float = 3) -> None:
        if self.is_owner:
            self.flash(text, seconds)
        else:
            self.send(text)
        raise Abort()

    def target(self, usage: str, fields: str | None = None) -> dict:
        if self.reply_message is not None:
            user = self.vk.user(self.reply_message["from_id"], fields)
        else:
            args = self.args
            user = self.vk.user(user_ref(args[1]), fields) if len(args) > 1 else None
        if user is None:
            self.fail(f"{ERROR} Необходимо ответить на сообщение пользователя или указать на него ссылку: {usage}")
        return user


def user_ref(text: str) -> str:
    link = re.search(r"vk\.com/([A-Za-z0-9_.]+)", text)
    if link:
        return link.group(1)
    mention = re.search(r"\[id(\d+)\|", text)
    if mention:
        return mention.group(1)
    return text.lstrip("@")


def mention(user: dict) -> str:
    return f"[id{user['id']}|{user['first_name']} {user['last_name']}]"
