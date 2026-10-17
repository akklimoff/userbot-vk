import pytest

from tests.fakes import CHAT, OWNER, STRANGER, in_peer, message
from userbot import automation
from userbot.automation import AUTO_ACCEPT, AUTO_CLEAN, AUTO_UNFOLLOW, ETERNAL_ONLINE, Autopilot
from userbot.vk import Throttled


class Clock:
    def __init__(self):
        self.now = 0.0
        self.pauses = []

    def sleep(self, seconds):
        self.pauses.append(seconds)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def autopilot(vk, store, clock):
    return Autopilot(vk, store, sleep=clock.sleep, now=lambda: clock.now)


@pytest.mark.parametrize("command, key", [("/автоприём", AUTO_ACCEPT), ("/autounfollow", AUTO_UNFOLLOW),
                                          ("/автоочистка", AUTO_CLEAN), ("/онлайн", ETERNAL_ONLINE)])
def test_one_command_switches_on_and_off(router, vk, store, command, key):
    router.handle(message(command))
    assert store.get(key) is True and "включено" in in_peer(vk, OWNER)[-1]["text"]
    router.handle(message(command))
    assert store.get(key) is False and "выключено" in in_peer(vk, OWNER)[-1]["text"]
    assert in_peer(vk, CHAT) == []


def test_strangers_cannot_switch(router, store):
    router.handle(message("/онлайн", from_id=STRANGER))
    assert store.get(ETERNAL_ONLINE) is None


def test_nothing_happens_while_switched_off(autopilot, vk):
    vk.incoming, vk.outgoing, vk.dead = [5], [6], [7]
    autopilot.tick()
    assert vk.online == 0 and vk.added == [] and vk.removed == []


def test_online_is_renewed_before_it_expires(autopilot, vk, store, clock):
    store.toggle(ETERNAL_ONLINE)
    autopilot.tick()
    clock.now = automation.ONLINE_EVERY - 1
    autopilot.tick()
    clock.now = automation.ONLINE_EVERY
    autopilot.tick()
    assert vk.online == 2


def test_jobs_do_their_friend_work(autopilot, vk, store):
    vk.incoming, vk.outgoing, vk.dead = [5], [6], [7]
    for key in (AUTO_ACCEPT, AUTO_UNFOLLOW, AUTO_CLEAN):
        store.toggle(key)
    autopilot.tick()
    assert vk.added == [5] and vk.removed == [6, 7]


def test_friend_actions_are_paced(autopilot, vk, store, clock):
    vk.incoming = list(range(100, 100 + automation.ACTIONS_PER_RUN + 5))
    store.toggle(AUTO_ACCEPT)
    autopilot.tick()
    assert len(vk.added) == automation.ACTIONS_PER_RUN
    assert clock.pauses == [automation.ACTION_PAUSE] * automation.ACTIONS_PER_RUN
    clock.now = automation.TICK_SECONDS
    autopilot.tick()
    assert len(vk.added) == automation.ACTIONS_PER_RUN + 5


def test_new_requests_wait_for_the_next_check(autopilot, vk, store, clock):
    vk.incoming = [5]
    store.toggle(AUTO_ACCEPT)
    autopilot.tick()
    vk.incoming = [6]
    clock.now = automation.FRIENDS_EVERY - 1
    autopilot.tick()
    assert vk.added == [5]
    clock.now = automation.FRIENDS_EVERY
    autopilot.tick()
    assert vk.added == [5, 6]


def test_throttling_pauses_everything(autopilot, vk, store, clock):
    def throttled(user_id):
        raise Throttled("капча")

    vk.add_friend = throttled
    vk.incoming = [5, 6]
    store.toggle(AUTO_ACCEPT)
    store.toggle(ETERNAL_ONLINE)
    autopilot.tick()
    assert vk.online == 1 and clock.pauses == []
    clock.now = automation.THROTTLED_PAUSE - 1
    autopilot.tick()
    assert vk.online == 1
    clock.now = automation.THROTTLED_PAUSE
    autopilot.tick()
    assert vk.online == 2


def test_broken_request_is_skipped_for_good(autopilot, vk, store, clock):
    def add(user_id):
        if user_id == 5:
            raise RuntimeError("пользователь удалён")
        vk.added.append(user_id)
        vk.incoming.remove(user_id)

    vk.add_friend = add
    vk.incoming = [5, 6]
    store.toggle(AUTO_ACCEPT)
    autopilot.tick()
    clock.now = automation.FRIENDS_EVERY
    autopilot.tick()
    assert vk.added == [6] and clock.pauses == [automation.ACTION_PAUSE] * 2


def test_switching_off_stops_a_running_batch(autopilot, vk, store):
    def add(user_id):
        vk.added.append(user_id)
        store.toggle(AUTO_ACCEPT)

    vk.add_friend = add
    vk.incoming = [5, 6, 7]
    store.toggle(AUTO_ACCEPT)
    autopilot.tick()
    assert vk.added == [5]


def test_failed_job_does_not_stop_the_others(autopilot, vk, store):
    def broken():
        raise RuntimeError("VK упал")

    vk.dead_friends = broken
    vk.incoming = [5]
    store.toggle(AUTO_CLEAN)
    store.toggle(AUTO_ACCEPT)
    autopilot.tick()
    assert vk.added == [5]


def test_switching_on_again_runs_at_once(autopilot, vk, store, clock):
    store.toggle(ETERNAL_ONLINE)
    autopilot.tick()
    store.toggle(ETERNAL_ONLINE)
    autopilot.tick()
    store.toggle(ETERNAL_ONLINE)
    clock.now = 1
    autopilot.tick()
    assert vk.online == 2
