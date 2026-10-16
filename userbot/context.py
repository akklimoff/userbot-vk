import html
import logging
import re
import time
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import IntEnum

from userbot.safety import looks_like_command
from userbot.store import Store

log = logging.getLogger("userbot-vk")

ERROR = "💔"
INVALID = "🙅‍♀️"
PROCESS = "💅"
SUCCESS = "✨"
SUCCESS_NO = "🥀"
# пустой символ: VK не даёт отредактировать сообщение в пустую строку
BLANK = "&#13;"
TRUSTED_USERS = "trusted"


class Access(IntEnum):
    PUBLIC = 0
    TRUSTED = 1
    OWNER = 2


class Abort(Exception):
    """Команда уже сообщила пользователю, почему не выполнилась."""


@dataclass(frozen=True)
class Command:
    names: tuple[str, ...]
    run: Callable[["Context"], None]
    description: str
    access: Access = Access.PUBLIC
    icon: str = "🎀"
    usage: str = ""


@dataclass
class Context:
    vk: object
    store: Store
    owner_id: int
    message: dict
    commands: Sequence[Command] = field(default=())
    sleep: Callable[[float], None] = time.sleep
    triggers_command: Callable[[str], bool] = lambda _: False
    deleted: bool = False

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
    def access(self) -> Access:
        if self.is_owner:
            return Access.OWNER
        return Access.TRUSTED if self.from_id in self.store.get(TRUSTED_USERS, []) else Access.PUBLIC

    @property
    def reply_message(self) -> dict | None:
        return self.message.get("reply_message")

    # сообщения в «Избранном» у всех удалять не нужно и нельзя
    @property
    def for_all(self) -> bool:
        return self.peer_id != self.owner_id

    def rest(self, skip: int) -> str:
        parts = self.message["text"].split(None, skip)
        return parts[skip] if len(parts) > skip else ""

    def is_command_like(self, text: str | None) -> bool:
        shown = as_shown(text)
        words = shown.split()
        return looks_like_command(shown) or bool(words) and self.triggers_command(words[0].lower())

    # бот пишет от лица владельца, и long poll вернёт ему же его сообщение как команду владельца
    def post(self, text: str | None = None, peer_id: int | None = None, **params) -> bool:
        if self.is_command_like(text):
            log.warning("Сообщение в %s похоже на команду бота и не отправлено", peer_id or self.peer_id)
            return False
        self.vk.send(peer_id or self.peer_id, text, **params)
        return True

    def result(self, **params) -> bool:
        reply = self.reply_message
        return self.post(reply_to=reply["id"] if reply else None, **params)

    # в чатах после команды ничего не остаётся: отчёт уходит в личку автору, владельцу (from_id == owner_id) — в «Избранное»
    def report(self, text: str) -> None:
        if not self.reaches_author:
            return
        try:
            self.post(text, peer_id=self.from_id)
        except Exception:
            log.info("Не удалось написать в личку %s", self.from_id)

    # личка от аккаунта владельца каждому, кто написал команду в беседе, — путь к капче и ограничениям VK за спам;
    # сообществу не пишем вовсе, чтобы не завести переписку двух ботов
    @property
    def reaches_author(self) -> bool:
        if self.from_id < 0:
            return False
        return self.access >= Access.TRUSTED or self.peer_id == self.from_id

    def answer(self, text: str) -> None:
        self.report(text)

    def done(self, text: str) -> None:
        if not self.is_owner:
            self.report(text)

    def fail(self, text: str) -> None:
        self.report(text)
        raise Abort()

    # чужое сообщение VK даёт удалить у всех только админу беседы — тогда убираем хотя бы у владельца
    def delete(self) -> None:
        if self.deleted:
            return
        self.deleted = True
        message_ids = [self.message["id"]]
        try:
            self.vk.delete(message_ids, self.for_all)
            return
        except Exception:
            if not self.for_all:
                log.info("Не удалось удалить команду в %s", self.peer_id)
                return
        try:
            self.vk.delete(message_ids, False)
        except Exception:
            log.info("Не удалось удалить команду в %s", self.peer_id)

    def hide(self) -> None:
        if self.is_owner:
            try:
                self.vk.edit(self.peer_id, self.message["id"], BLANK)
            except Exception:
                log.info("Не удалось стереть команду в %s", self.peer_id)
        self.delete()

    def target(self, usage: str) -> dict:
        args = self.args
        if len(args) > 1:
            user = self.vk.user(user_ref(args[1]))
        elif self.reply_message is not None:
            user = self.vk.user(self.reply_message["from_id"])
        else:
            user = None
        if user is None:
            self.fail(f"{ERROR} Не понятно, о ком речь — ответьте на сообщение человека или укажите его: {usage}")
        return user


def user_ref(text: str) -> str:
    link = re.search(r"vk\.(?:com|ru)/([A-Za-z0-9_.]+)", text)
    if link:
        return link.group(1)
    mention = re.search(r"\[id(\d+)\|", text)
    if mention:
        return mention.group(1)
    return text.lstrip("@")


# так текст увидит VK после отправки: сущности раскрыты, <br> — перевод строки, невидимые символы (Cf) выброшены;
# иначе «&#47;trust» прошёл бы проверку и вернулся через long poll командой владельца
def as_shown(text: str | None) -> str:
    shown = text or ""
    for _ in range(5):
        decoded = html.unescape(re.sub(r"<br\s*/?>", "\n", shown, flags=re.IGNORECASE))
        if decoded == shown:
            break
        shown = decoded
    return "".join(ch for ch in shown if unicodedata.category(ch) != "Cf")


# без разметки [id…|…]: отчёты уходят в личку, а тег владельца в его же «Избранном» будит других ботов аккаунта
def full_name(user: dict) -> str:
    return f"{user['first_name']} {user['last_name']}"
