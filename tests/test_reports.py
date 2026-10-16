import pytest

from tests.fakes import CHAT, OWNER, STRANGER, FakeVk, in_peer, message, user
from userbot import media

TRUSTED = 3


@pytest.fixture
def vk():
    return FakeVk(users={TRUSTED: user(TRUSTED), 9: user(9)})


@pytest.fixture
def trusted(router, store):
    store.add_to("trusted", TRUSTED)
    return router


def test_owner_success_leaves_nothing(router, vk, store):
    router.handle(message("/ignore 9"))
    assert store.get("ignore") == [9]
    assert vk.sent == [] and vk.deleted == [([100], True)]


def test_owner_info_goes_to_saved_messages(router, vk):
    router.handle(message("/911"))
    assert in_peer(vk, CHAT) == [] and "Команды бота" in in_peer(vk, OWNER)[0]["text"]
    assert vk.deleted == [([100], True)]


def test_owner_error_goes_to_saved_messages(router, vk):
    router.handle(message("/ignore"))
    assert in_peer(vk, CHAT) == [] and "о ком речь" in in_peer(vk, OWNER)[0]["text"]


def test_command_in_saved_messages_is_deleted_only_for_owner(router, vk):
    router.handle(message("/911", peer_id=OWNER))
    assert vk.deleted == [([100], False)]


def test_trusted_command_falls_back_to_deleting_for_owner(trusted, vk, store):
    def delete(message_ids, for_all):
        if for_all:
            raise RuntimeError("нельзя удалить чужое сообщение")
        vk.deleted.append((list(message_ids), for_all))

    vk.delete = delete
    trusted.handle(message("/ignore 9", from_id=TRUSTED))
    assert store.get("ignore") == [9]
    assert vk.deleted == [([100], False)]
    assert [m["peer_id"] for m in vk.sent] == [TRUSTED]


def test_stranger_gets_answer_only_in_existing_dm(router, vk):
    router.handle(message("/help", from_id=STRANGER))
    assert vk.sent == [] and vk.deleted == [([100], True)]
    router.handle(message("/help", from_id=STRANGER, peer_id=STRANGER, message_id=101))
    assert [m["peer_id"] for m in vk.sent] == [STRANGER]


def test_communities_are_never_messaged(router, vk):
    router.handle(message("/help", from_id=-5, peer_id=-5))
    assert vk.sent == []


def test_owner_sees_disable_state(router, vk):
    router.handle(message("/disable"))
    assert "выключены" in in_peer(vk, OWNER)[0]["text"]


def test_owner_learns_number_of_unnamed_voice(router, vk, monkeypatch, tmp_path):
    monkeypatch.setattr(media, "download", lambda url, d, s: str(tmp_path / "v.ogg"))
    voice = {"type": "audio_message", "audio_message": {"link_ogg": "https://x/v.ogg"}}
    router.handle(message("/sa", reply_message={"id": 5, "from_id": 9, "attachments": [voice]}))
    assert "«1»" in in_peer(vk, OWNER)[0]["text"]
    router.handle(message("/sa привет", reply_message={"id": 5, "from_id": 9, "attachments": [voice]}))
    assert len(vk.sent) == 1


def test_owner_saved_voice_replaces_command_quietly(router, vk, store):
    store.put_new("saved_audio", "k", "audio_message1_2")
    router.handle(message("/ag k", reply_message={"id": 5, "from_id": 9, "attachments": []}))
    assert vk.edited == [(CHAT, 100, "&#13;")] and vk.deleted == [([100], True)]
    assert vk.sent == [{"peer_id": CHAT, "text": None, "attachment": "audio_message1_2", "reply_to": 5}]


def test_closed_dm_does_not_break_command(trusted, vk, store):
    def send(peer_id, text=None, **params):
        raise RuntimeError("личка закрыта")

    vk.send = send
    trusted.handle(message("/ignore 9", from_id=TRUSTED))
    assert store.get("ignore") == [9] and vk.deleted == [([100], True)]
