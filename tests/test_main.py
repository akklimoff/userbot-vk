from concurrent.futures import Future

from tests.fakes import CHAT, OWNER, STRANGER, FakeVk, message
from userbot.commands import COMMANDS
from userbot.main import Dispatcher, RateLimit, process
from userbot.router import Router
from userbot.vk import Incoming


class CountingVk(FakeVk):
    def __init__(self, text, author=STRANGER):
        super().__init__()
        self.reads = 0
        self._text = text
        self._author = author

    def message(self, message_id):
        self.reads += 1
        return message(self._text, from_id=self._author, message_id=message_id)


class InlinePool:
    def __init__(self, run=True):
        self.submitted = 0
        self._run = run

    def submit(self, fn, *args):
        self.submitted += 1
        future = Future()
        if self._run:
            fn(*args)
            future.set_result(None)
        return future


def dispatcher(vk, store, pool=None, log_messages=False, **kwargs):
    return Dispatcher(vk, Router(vk, store, COMMANDS, vk.me_id, sleep=lambda _: None), pool or InlinePool(),
                      log_messages, **kwargs)


def test_plain_chatter_is_not_fetched(store):
    vk = CountingVk("просто текст")
    dispatcher(vk, store).dispatch(Incoming(100, CHAT, "просто текст", STRANGER))
    assert vk.reads == 0


def test_commands_are_fetched_and_handled(store):
    vk = CountingVk("/uid 2")
    dispatcher(vk, store).dispatch(Incoming(100, CHAT, "/uid 2", STRANGER))
    assert vk.reads == 1 and vk.sent


def test_banned_author_is_not_fetched(store):
    store.add_to("banned", STRANGER)
    vk = CountingVk("/help")
    dispatcher(vk, store).dispatch(Incoming(100, CHAT, "/help", STRANGER))
    assert vk.reads == 0


def test_own_messages_are_never_dispatched(store):
    vk = CountingVk("/trust 9", author=OWNER)
    vk.own_random_ids.add(777)
    dispatcher(vk, store).dispatch(Incoming(100, CHAT, "/trust 9", OWNER, random_id=777))
    assert vk.reads == 0


def test_strangers_are_rate_limited_but_owner_is_not(store):
    vk = CountingVk("/help")
    clock = [0.0]
    d = dispatcher(vk, store, limit=RateLimit(2, now=lambda: clock[0]))
    for _ in range(4):
        d.dispatch(Incoming(100, CHAT, "/help", STRANGER))
    assert vk.reads == 2
    clock[0] = 61
    d.dispatch(Incoming(100, CHAT, "/help", STRANGER))
    assert vk.reads == 3
    for _ in range(4):
        d.dispatch(Incoming(100, CHAT, "/help", OWNER))
    assert vk.reads == 7


def test_stranger_backlog_is_capped(store):
    pool = InlinePool(run=False)
    d = dispatcher(FakeVk(), store, pool=pool, backlog=2, limit=RateLimit(100))
    for i in range(5):
        d.dispatch(Incoming(i, CHAT, "/help", STRANGER + i))
    assert pool.submitted == 2


def test_logging_failure_does_not_skip_command(store):
    vk = CountingVk("/uid 2")

    def broken(_peer_id):
        raise RuntimeError("нет доступа к беседе")

    vk.peer_title = broken
    process(vk, Router(vk, store, COMMANDS, vk.me_id), Incoming(100, CHAT, "/uid 2", STRANGER), True)
    assert vk.sent
