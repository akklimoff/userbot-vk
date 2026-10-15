import pytest

from tests.fakes import CHAT, OWNER, STRANGER, FakeVk, message, texts, user
from userbot.commands import COMMANDS
from userbot.commands.images import dist_percent
from userbot.commands.info import help_text
from userbot.commands.messages import parse_ttl
from userbot.context import Access
from userbot.context import user_ref
from userbot.router import Router


def test_ban_and_unban_round_trip(router, vk, store):
    router.handle(message("/ban [id2|Имя]"))
    assert store.get("banned") == [STRANGER]
    router.handle(message("/ban 2"))
    assert "уже заблокирован" in texts(vk)[-1]
    router.handle(message("/unban 2"))
    assert store.get("banned") == []


def test_owner_cannot_ban_self(router, vk, store):
    router.handle(message("/ban 1"))
    assert store.get("banned") is None
    assert vk.deleted == [([100], True)]


def test_target_from_reply(router, store):
    router.handle(message("/ignore", reply_message={"id": 5, "from_id": STRANGER}))
    assert store.get("ignore") == [STRANGER]


def test_ban_chat_toggles_current_peer(router, store):
    router.handle(message("/ban_chat"))
    router.handle(message("/unban_chat"))
    assert store.get("banned_peers") == []


def test_assoc_set_requires_existing_command(router, vk, store):
    router.handle(message("/assoc_set /nope x"))
    assert store.get("assoc") is None
    router.handle(message("/assoc_set /uid /d"))
    assert store.get("assoc") is None
    router.handle(message("/assoc_set /UID айди"))
    assert store.get("assoc") == {"айди": "/uid"}
    router.handle(message("/assoc_del айди"))
    assert store.get("assoc") == {}


def test_help_depends_on_access():
    public = help_text(COMMANDS, Access.PUBLIC)
    trusted = help_text(COMMANDS, Access.TRUSTED)
    full = help_text(COMMANDS, Access.OWNER)
    assert "/ban" not in public and "/ban" in trusted
    assert "/trust" not in public and trusted == full
    assert "[id" not in full and "http" not in full
    assert not any(name in full for name in ("/tc", "/st,", "/groups"))


def test_command_names_are_unique():
    names = [name for c in COMMANDS for name in c.names]
    assert len(names) == len(set(names))


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
    assert vk.sent == []
    assert "Такого времени нет" in vk.edited[0][2]


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
    assert vk.sent == []


def test_repeat_validates_count(router, vk):
    router.handle(message("/repeat 50 ура"))
    assert vk.sent == []


def test_del_removes_only_own_recent_messages(vk, store):
    import time
    now = int(time.time())
    history = [{"id": 99, "from_id": OWNER, "date": now}, {"id": 98, "from_id": STRANGER, "date": now},
               {"id": 97, "from_id": OWNER, "date": now}, {"id": 96, "from_id": OWNER, "date": now - 90000}]
    vk = FakeVk(history=history)
    Router(vk, store, COMMANDS, OWNER, sleep=lambda _: None).handle(message("/del 5"))
    assert vk.deleted[-1] == ([99, 97], True)


def test_privacy_open_requires_friend(store):
    vk = FakeVk(users={STRANGER: user(STRANGER, is_friend=0)})
    Router(vk, store, COMMANDS, OWNER, sleep=lambda _: None).handle(
        message("+a", reply_message={"id": 5, "from_id": STRANGER}))
    assert vk.privacy == {}


def test_privacy_open_and_close(router, vk):
    reply = {"id": 5, "from_id": STRANGER}
    router.handle(message("+s", reply_message=reply))
    assert vk.privacy["photos_saved"] == [STRANGER]
    router.handle(message("-сохры", reply_message=reply))
    assert vk.privacy["photos_saved"] == []


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


def test_caption_needs_text(router, vk):
    photo = {"type": "photo", "photo": {"sizes": [{"url": "https://x/a.jpg", "width": 1, "height": 1}]}}
    router.handle(message("/t", from_id=STRANGER, attachments=[photo]))
    assert "Нужны фото и текст" in vk.sent[0]["text"]


@pytest.mark.parametrize("args, percent", [(["/d"], 50), (["/d", "1"], 50), (["/d", "10"], 5), (["/d", "11"], None),
                                           (["/d", "x"], None), (["/d", "0"], None)])
def test_dist_percent(args, percent):
    assert dist_percent(args) == percent


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
    router.handle(message("/i 5m +s"))
    assert vk.sent == []
    assert "принял бы за команду" in vk.edited[0][2]


def test_own_aliases_are_never_posted(router, vk, store):
    store.put_new("assoc", "ау", "/uid")
    router.handle(message("/repeat 2 ау как дела"))
    assert vk.sent == []


def test_privacy_keeps_complex_settings(router, vk):
    vk.privacy_values["photos_saved"] = {"category": "friends", "owners": {"excluded": [7]}}
    router.handle(message("+s", reply_message={"id": 5, "from_id": STRANGER}))
    assert "photos_saved" not in vk.privacy
    assert "настроен сложнее" in vk.edited[0][2]


def test_busy_media_slots_are_reported(router, vk, monkeypatch):
    from contextlib import contextmanager
    from userbot import media

    @contextmanager
    def busy():
        raise media.MediaBusy()
        yield

    monkeypatch.setattr(media, "heavy_slot", busy)
    photo = {"type": "photo", "photo": {"sizes": [{"url": "https://x/a.jpg", "width": 1, "height": 1}]}}
    router.handle(message("/d", from_id=STRANGER, attachments=[photo]))
    assert "занят" in vk.sent[0]["text"]
