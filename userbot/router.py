import logging
import time
from collections.abc import Callable, Sequence

from userbot.commands.access import BANNED, BANNED_PEERS, DISABLED, IGNORED
from userbot.commands.assoc import ASSOC
from userbot.context import ERROR, Abort, Command, Context
from userbot.media import MediaError
from userbot.store import Store

log = logging.getLogger("userbot-vk")


class Router:
    def __init__(self, vk, store: Store, commands: Sequence[Command], owner_id: int,
                 sleep: Callable[[float], None] = time.sleep):
        self._vk = vk
        self._store = store
        self._commands = commands
        self._owner_id = owner_id
        self._sleep = sleep
        self._by_name = {name: c for c in commands for name in c.names}

    def handle(self, message: dict) -> None:
        if not self._accepts(message):
            return
        command = self.command_for(message["text"].split()[0].lower())
        if command is None or (command.owner_only and message["from_id"] != self._owner_id):
            return
        ctx = Context(self._vk, self._store, self._owner_id, message, self._commands, self._sleep)
        try:
            command.run(ctx)
        except Abort:
            pass
        except MediaError as e:
            log.warning("Команда %s в %s: %s", command.names[0], message["peer_id"], e)
            try:
                ctx.fail(f"{ERROR} Не удалось обработать файл, попробуйте другой.")
            except Abort:
                pass

    def command_for(self, word: str) -> Command | None:
        return self._by_name.get(self._store.get(ASSOC, {}).get(word, word))

    def _accepts(self, message: dict) -> bool:
        author, owner = message["from_id"], message["from_id"] == self._owner_id
        if author in self._store.get(IGNORED, []):
            self._vk.delete([message["id"]], False)
            return False
        if author in self._store.get(BANNED, []):
            return False
        if not owner and message["peer_id"] in self._store.get(BANNED_PEERS, []):
            return False
        if not owner and self._store.get(DISABLED, False):
            return False
        return bool((message.get("text") or "").strip())
