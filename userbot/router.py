import logging
import time
from collections.abc import Callable, Collection, Sequence

from userbot.commands.access import DISABLED, IGNORED
from userbot.context import ERROR, TRUSTED_USERS, Abort, Command, Context
from userbot.media import MediaError
from userbot.store import Store

log = logging.getLogger("userbot-vk")


class Router:
    def __init__(self, vk, store: Store, commands: Sequence[Command], owner_id: int,
                 sleep: Callable[[float], None] = time.sleep, own_accounts: Collection[int] = ()):
        self._vk = vk
        self._store = store
        self._commands = commands
        self._owner_id = owner_id
        self._sleep = sleep
        self._own_accounts = own_accounts
        self._by_name = {name: c for c in commands for name in c.names}

    def handle(self, message: dict) -> None:
        if not self._accepts(message):
            return
        command = self.command_for(message["text"].split()[0].lower())
        if command is None:
            return
        ctx = Context(self._vk, self._store, self._owner_id, message, self._commands, self._sleep,
                      lambda word: self.command_for(word) is not None)
        if ctx.access < command.access:
            return
        try:
            command.run(ctx)
        except Abort:
            pass
        except MediaError as e:
            log.warning("Команда %s в %s: %s", command.names[0], message["peer_id"], e)
            ctx.report(f"{ERROR} Не удалось обработать файл — попробуйте другой")
        except Exception:
            log.exception("Команда %s в %s упала", command.names[0], message["peer_id"])
            ctx.report(f"{ERROR} Не удалось выполнить команду, попробуйте ещё раз")
        finally:
            ctx.delete()

    def privileged(self, author: int | None) -> bool:
        return author == self._owner_id or author in self._store.get(TRUSTED_USERS, [])

    def wants(self, text: str, author: int | None, peer_id: int) -> bool:
        if author in self._store.get(IGNORED, []):
            return True
        if self.from_other_account(author):
            return False
        if not self.privileged(author) and self._store.get(DISABLED, False):
            return False
        words = text.split()
        return bool(words) and self.command_for(words[0].lower()) is not None

    # бот каждого аккаунта видит команды остальных как чужие, и в общей беседе ответили бы все боты сразу
    def from_other_account(self, author: int | None) -> bool:
        return author != self._owner_id and author in self._own_accounts

    def command_for(self, word: str) -> Command | None:
        return self._by_name.get(word)

    def _accepts(self, message: dict) -> bool:
        author = message["from_id"]
        if author == self._owner_id and self._vk.sent_by_bot(message.get("random_id")):
            return False
        privileged = self.privileged(author)
        if author in self._store.get(IGNORED, []):
            self._vk.delete([message["id"]], False)
            return False
        if self.from_other_account(author):
            return False
        if not privileged and self._store.get(DISABLED, False):
            return False
        return bool((message.get("text") or "").strip())
