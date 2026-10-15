from tests.fakes import STRANGER, FakeVk, message
from userbot.commands import COMMANDS
from userbot.main import process
from userbot.router import Router
from userbot.vk import Incoming


class CountingVk(FakeVk):
    def __init__(self, text):
        super().__init__()
        self.reads = 0
        self._text = text

    def message(self, message_id):
        self.reads += 1
        return message(self._text, from_id=STRANGER, message_id=message_id)


def test_plain_chatter_is_not_fetched(store):
    vk = CountingVk("просто текст")
    process(vk, Router(vk, store, COMMANDS, vk.me_id), Incoming(100, "просто текст", STRANGER), False)
    assert vk.reads == 0


def test_commands_are_fetched_and_handled(store):
    vk = CountingVk("/uid 2")
    process(vk, Router(vk, store, COMMANDS, vk.me_id), Incoming(100, "/uid 2", STRANGER), False)
    assert vk.reads == 1 and vk.sent


def test_logging_failure_does_not_skip_command(store):
    vk = CountingVk("/uid 2")

    def broken(_peer_id):
        raise RuntimeError("нет доступа к беседе")

    vk.peer_title = broken
    process(vk, Router(vk, store, COMMANDS, vk.me_id), Incoming(100, "/uid 2", STRANGER), True)
    assert vk.sent
