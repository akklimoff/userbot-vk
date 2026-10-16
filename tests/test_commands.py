import pytest

from tests.fakes import CHAT, OWNER, STRANGER, FakeVk, in_peer, message
from userbot.commands import COMMANDS
from userbot.commands.info import help_text
from userbot.commands.messages import parse_ttl
from userbot.context import Access
from userbot.context import user_ref
from userbot.router import Router
from userbot.safety import BARE_WORDS, COMMAND_WORDS, DELETE_WORD


def test_target_from_reply(router, store):
    router.handle(message("/ignore", reply_message={"id": 5, "from_id": STRANGER}))
    assert store.get("ignore") == [STRANGER]


def test_help_depends_on_access():
    public = help_text(COMMANDS, Access.PUBLIC)
    trusted = help_text(COMMANDS, Access.TRUSTED)
    full = help_text(COMMANDS, Access.OWNER)
    assert "/ignore" not in public and "/ignore" in trusted
    assert "/trust" not in public and trusted == full
    assert "[id" not in full and "http" not in full
    assert not any(name in full for name in ("/tc", "/st,", "/groups"))


def test_command_names_are_unique():
    names = [name for c in COMMANDS for name in c.names]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("name", [name for c in COMMANDS for name in c.names])
def test_names_are_not_vk_bot_command_words(name):
    assert name.lstrip("!/-+").rstrip(",.:!") not in COMMAND_WORDS | BARE_WORDS | {DELETE_WORD}


def test_russian_names_run_commands(router, vk):
    router.handle(message("/повтор 2 ура"))
    assert [m["text"] for m in vk.sent] == ["ура"] * 2


@pytest.mark.parametrize("word, ttl", [("15s", 15), ("5м", 300), ("1h", 3600), ("5ч", 18000), ("1d", 86400), ("1д", 86400), ("2x", None),
                                        ("текст", None), ("10", None)])
def test_parse_ttl(word, ttl):
    assert parse_ttl(word) == ttl


def test_invisible_sends_text_with_ttl(router, vk):
    router.handle(message("/i 15s секрет\nвторая строка"))
    assert vk.sent == [{"peer_id": CHAT, "text": "секрет\nвторая строка", "expire_ttl": 15}]
    assert vk.deleted == [([100], True)]


def test_invisible_rejects_unsupported_ttl(router, vk):
    router.handle(message("/i 2h текст"))
    assert in_peer(vk, CHAT) == []
    assert "Такого времени нет" in in_peer(vk, OWNER)[0]["text"]


def test_invisible_resends_own_voice(router, vk):
    voice = {"type": "audio_message", "audio_message": {"owner_id": OWNER, "id": 7, "access_key": "k"}}
    router.handle(message("/i 1m", reply_message={"id": 5, "from_id": OWNER, "attachments": [voice]}))
    assert vk.sent == [{"peer_id": CHAT, "text": None, "attachment": "audio_message1_7_k", "expire_ttl": 60}]
    assert ([5], True) in vk.deleted


def test_repeat_sends_text_n_times(router, vk):
    router.handle(message("/repeat 3 ура"))
    assert [m["text"] for m in vk.sent] == ["ура"] * 3


def test_repeat_never_sends_command_like_text(router, vk):
    router.handle(message("/repeat 3 /ban 5"))
    assert in_peer(vk, CHAT) == []


def test_say_sends_text_once_keeping_lines(router, vk):
    router.handle(message("/скажи привет\nкак дела"))
    assert [m["text"] for m in in_peer(vk, CHAT)] == ["привет\nкак дела"]


def test_say_answers_the_replied_message(router, vk):
    router.handle(message("/эхо ура", reply_message={"id": 5, "from_id": STRANGER}))
    assert in_peer(vk, CHAT)[0]["reply_to"] == 5


def test_say_needs_text(router, vk):
    router.handle(message("/скажи"))
    assert in_peer(vk, CHAT) == []
    assert "/скажи текст" in in_peer(vk, OWNER)[0]["text"]


def test_say_never_sends_command_like_text(router, vk):
    router.handle(message("/скажи бан 5"))
    assert in_peer(vk, CHAT) == []


def test_say_is_not_for_strangers(router, vk):
    router.handle(message("/скажи ура", from_id=STRANGER))
    assert in_peer(vk, CHAT) == []


def test_repeat_validates_count(router, vk):
    router.handle(message("/repeat 50 ура"))
    assert in_peer(vk, CHAT) == []


def test_del_removes_only_own_recent_messages(vk, store):
    import time
    now = int(time.time())
    history = [{"id": 99, "from_id": OWNER, "date": now}, {"id": 98, "from_id": STRANGER, "date": now},
               {"id": 97, "from_id": OWNER, "date": now}, {"id": 96, "from_id": OWNER, "date": now - 90000}]
    vk = FakeVk(history=history)
    Router(vk, store, COMMANDS, OWNER, sleep=lambda _: None).handle(message("/del 5"))
    assert vk.deleted[-1] == ([99, 97], True)


def test_saved_voice_flow(router, vk, store, monkeypatch, tmp_path):
    from userbot import media
    monkeypatch.setattr(media, "download", lambda url, d, s: str(tmp_path / "v.ogg"))
    voice = {"type": "audio_message", "audio_message": {"owner_id": 3, "id": 7, "link_ogg": "https://x/v.ogg"}}
    router.handle(message("/sa привет мир", reply_message={"id": 5, "from_id": STRANGER, "attachments": [voice]}))
    assert store.get("saved_audio") == {"привет мир": "audio_message1_10"}
    router.handle(message("/ag привет мир"))
    assert vk.sent[-1]["attachment"] == "audio_message1_10"
    router.handle(message("/ad привет мир"))
    assert store.get("saved_audio") == {}


def test_saved_voice_without_name_gets_next_number(router, store, monkeypatch, tmp_path):
    from userbot import media
    monkeypatch.setattr(media, "download", lambda url, d, s: str(tmp_path / "v.ogg"))
    store.put_new("saved_audio", "1", "audio_message1_1")
    voice = {"type": "audio_message", "audio_message": {"link_ogg": "https://x/v.ogg"}}
    router.handle(message("/sa", reply_message={"id": 5, "from_id": STRANGER, "attachments": [voice]}))
    assert list(store.get("saved_audio")) == ["1", "2"]


@pytest.mark.parametrize("text, ref", [("https://vk.com/durov", "durov"), ("[id5|Имя]", "5"), ("@nick", "nick"),
                                       ("123", "123")])
def test_user_ref(text, ref):
    assert user_ref(text) == ref


def test_invisible_skips_link_attachments(router, vk):
    link = {"type": "link", "link": {"url": "https://example.com", "title": "x"}}
    photo = {"type": "photo", "photo": {"owner_id": 1, "id": 9, "access_key": "a"}}
    router.handle(message("/i 5m смотри https://example.com", attachments=[link, photo]))
    assert vk.sent == [{"peer_id": CHAT, "text": "смотри https://example.com", "attachment": "photo1_9_a",
                        "expire_ttl": 300}]


def test_invisible_keeps_message_when_text_is_command_like(router, vk):
    router.handle(message("/i 5m /гсы"))
    assert in_peer(vk, CHAT) == []
    assert "принял бы за команду" in in_peer(vk, OWNER)[0]["text"]


def test_busy_media_slots_are_reported(router, vk, monkeypatch):
    from contextlib import contextmanager
    from userbot import media

    @contextmanager
    def busy():
        raise media.MediaBusy()
        yield

    monkeypatch.setattr(media, "heavy_slot", busy)
    voice = {"type": "audio_message", "audio_message": {"link_ogg": "https://x/v.ogg"}}
    router.handle(message("/au 1", from_id=STRANGER, peer_id=STRANGER, reply_message={"id": 5, "from_id": 9,
                                                                                    "attachments": [voice]}))
    assert "занят" in in_peer(vk, STRANGER)[0]["text"]
