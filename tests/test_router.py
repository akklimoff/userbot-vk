from tests.fakes import CHAT, OWNER, STRANGER, message


def test_owner_command_is_ignored_for_others(router, vk):
    router.handle(message("/ignore 5", from_id=STRANGER))
    assert vk.sent == [] and vk.edited == []


def test_public_command_answers_anyone(router, vk):
    router.handle(message("/uid 2", from_id=STRANGER, peer_id=STRANGER))
    assert vk.sent[0]["text"].endswith("ID пользователя: 2")
    assert vk.sent[0]["peer_id"] == STRANGER and "reply_to" not in vk.sent[0]


def test_unknown_word_is_ignored(router, vk):
    router.handle(message("привет всем"))
    assert vk.sent == [] and vk.edited == []


def test_ignored_user_message_is_deleted_only_for_owner(router, vk, store):
    store.add_to("ignore", STRANGER)
    router.handle(message("/help", from_id=STRANGER))
    assert vk.deleted == [([100], False)]
    assert vk.sent == []


def test_disabled_bot_serves_only_owner(router, vk, store):
    store.toggle("disabled")
    router.handle(message("/help", from_id=STRANGER))
    router.handle(message("/help", from_id=OWNER))
    assert len(vk.sent) == 1


def test_media_failure_is_reported(router, vk, monkeypatch):
    from userbot import media

    def broken(*_):
        raise media.MediaError("нет сети")

    monkeypatch.setattr(media, "download", broken)
    voice = {"type": "audio_message", "audio_message": {"link_ogg": "https://x/v.ogg"}}
    router.handle(message("/copy", reply_message={"id": 5, "from_id": STRANGER, "attachments": [voice]}))
    assert "Не удалось обработать файл" in vk.sent[0]["text"] and vk.sent[0]["peer_id"] == OWNER


def test_unexpected_error_is_reported(router, vk, monkeypatch):
    def broken(*_args, **_kwargs):
        raise RuntimeError("VK упал")

    monkeypatch.setattr(vk, "user", broken)
    router.handle(message("/uid 2", from_id=STRANGER, peer_id=STRANGER))
    assert "Не удалось выполнить команду" in vk.sent[0]["text"] and vk.sent[0]["peer_id"] == STRANGER


def test_wants_only_commands_and_ignored_authors(router, store):
    store.add_to("ignore", 7)
    assert router.wants("/help", STRANGER, CHAT)
    assert router.wants("что угодно", 7, CHAT)
    assert not router.wants("просто текст", STRANGER, CHAT)
    assert not router.wants("", STRANGER, CHAT)
