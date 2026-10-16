import pytest

from tests.fakes import CHAT, OWNER, STRANGER, FakeVk, message, user
from userbot.commands import COMMANDS
from userbot.router import Router

TRUSTED = 3
TARGET = 5


@pytest.fixture
def vk():
    return FakeVk(users={TRUSTED: user(TRUSTED), TARGET: user(TARGET)})


def trust(router):
    router.handle(message(f"/trust {TRUSTED}"))


def test_owner_grants_and_revokes_trust(router, store, vk):
    trust(router)
    assert store.get("trusted") == [TRUSTED]
    router.handle(message(f"/untrust {TRUSTED}"))
    assert store.get("trusted") == []


def test_owner_cannot_trust_self(router, store):
    router.handle(message(f"/trust {OWNER}"))
    assert store.get("trusted") is None


def test_trusted_gets_report_in_dm_and_command_is_removed(router, store, vk):
    trust(router)
    router.handle(message(f"/ignore {TARGET}", from_id=TRUSTED, message_id=200))
    assert store.get("ignore") == [TARGET]
    assert vk.sent[-1]["peer_id"] == TRUSTED and "в игноре" in vk.sent[-1]["text"]
    assert all(m["peer_id"] != CHAT for m in vk.sent)
    assert vk.deleted[-1] == ([200], True) and vk.edited == []


def test_stranger_cannot_run_owner_commands(router, store):
    router.handle(message(f"/ignore {TARGET}", from_id=STRANGER))
    assert store.get("ignore") is None


def test_trusted_cannot_manage_trust(router, store):
    trust(router)
    router.handle(message(f"/trust {STRANGER}", from_id=TRUSTED))
    router.handle(message(f"/untrust {TRUSTED}", from_id=TRUSTED))
    assert store.get("trusted") == [TRUSTED]


def test_trusted_bypasses_disable(router, store, vk):
    trust(router)
    store.toggle("disabled")
    router.handle(message("/uid 5", from_id=TRUSTED))
    router.handle(message("/uid 5", from_id=STRANGER))
    assert len(vk.sent) == 1


def test_trusted_command_survives_failed_deletion(router, vk):
    trust(router)

    def delete(message_ids, for_all):
        if message_ids == [200]:
            raise RuntimeError("нельзя удалить чужое сообщение")
        vk.deleted.append((message_ids, for_all))

    vk.delete = delete
    router.handle(message("/repeat 2 привет", from_id=TRUSTED, message_id=200))
    assert [m["text"] for m in vk.sent if m["text"] == "привет"] == ["привет", "привет"]


def test_trusted_help_lists_every_command(router, vk):
    trust(router)
    router.handle(message("/911", from_id=TRUSTED))
    text = vk.sent[-1]["text"]
    assert all(name in text for c in COMMANDS for name in c.names)


def test_trusted_list(router, vk):
    trust(router)
    router.handle(message("/trusted"))
    assert "Имя3 Фамилия" in vk.sent[-1]["text"] and vk.sent[-1]["peer_id"] == OWNER


def test_owner_messages_in_trusted_dialog_are_deleted_for_all(store):
    import time
    vk = FakeVk(users={TRUSTED: user(TRUSTED)}, history=[{"id": 99, "from_id": OWNER, "date": int(time.time())}])
    router = Router(vk, store, COMMANDS, OWNER, sleep=lambda _: None)
    trust(router)
    router.handle(message("/del 1", from_id=TRUSTED, peer_id=TRUSTED, message_id=200))
    assert vk.deleted[-1] == ([99], True)
