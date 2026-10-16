import subprocess

import pytest

from tests.fakes import OWNER, STRANGER, FakeVk, message, user
from userbot import media
from userbot.commands import COMMANDS
from userbot.context import as_shown, user_ref
from userbot.router import Router

TRUSTED = 3
OTHER_TRUSTED = 4


@pytest.fixture
def vk():
    return FakeVk(users={TRUSTED: user(TRUSTED), OTHER_TRUSTED: user(OTHER_TRUSTED), 9: user(9)})


@pytest.fixture
def trusted(router, store):
    store.add_to("trusted", TRUSTED)
    store.add_to("trusted", OTHER_TRUSTED)
    return router


@pytest.mark.parametrize("text", ["&#47;trust 9", "&amp;#47;trust 9", "<br>/trust 9", "​/trust 9",
                                  "­/ban 9", "&#1082;ик @x"])
def test_disguised_commands_are_never_posted(trusted, vk, text):
    trusted.handle(message(f"/repeat 1 {text}", from_id=TRUSTED))
    assert vk.sent[-1]["text"].endswith("принял бы за команду, поэтому не отправляю")
    assert all(m["text"] != text for m in vk.sent)


def test_as_shown_matches_what_vk_renders():
    assert as_shown("&#47;trust") == "/trust"
    assert as_shown("a<br/>b") == "a\nb"
    assert as_shown("​привет") == "привет"


def test_owner_message_sent_by_bot_is_ignored(router, vk, store):
    vk.own_random_ids.add(555)
    router.handle(message("/trust 9", random_id=555))
    assert store.get("trusted") is None


def test_trusted_cannot_ignore_other_trusted(trusted, store):
    trusted.handle(message(f"/ignore {OTHER_TRUSTED}", from_id=TRUSTED))
    assert store.get("ignore") is None


def test_owner_can_ignore_trusted(trusted, store):
    trusted.handle(message(f"/ignore {OTHER_TRUSTED}"))
    assert store.get("ignore") == [OTHER_TRUSTED]


def test_explicit_target_wins_over_reply(router, store):
    router.handle(message("/ignore 9", reply_message={"id": 5, "from_id": STRANGER}))
    assert store.get("ignore") == [9]


@pytest.mark.parametrize("text, ref", [("https://vk.ru/durov", "durov"), ("vk.com/id5", "id5")])
def test_user_ref_links(text, ref):
    assert user_ref(text) == ref


def test_failure_after_deletion_is_reported_as_new_message(router, vk, monkeypatch, tmp_path):
    monkeypatch.setattr(media, "download", lambda url, d, s: str(tmp_path / "v.ogg"))

    def broken_upload(path, peer_id):
        raise RuntimeError("upload сломался")

    monkeypatch.setattr(vk, "upload_voice", broken_upload)
    voice = {"type": "audio_message", "audio_message": {"link_ogg": "https://x/v.ogg"}}
    router.handle(message("/copy", reply_message={"id": 5, "from_id": STRANGER, "attachments": [voice]}))
    assert vk.deleted == [([100], True)]
    assert "Не удалось выполнить команду" in vk.sent[-1]["text"]
    assert "reply_to" not in vk.sent[-1]


def test_del_falls_back_to_single_deletes(store):
    import time
    now = int(time.time())
    vk = FakeVk(history=[{"id": i, "from_id": OWNER, "date": now} for i in (99, 98, 97)])
    attempts = []

    def delete(ids, for_all):
        attempts.append(list(ids))
        if len(ids) > 1 or ids == [98]:
            raise RuntimeError("служебное сообщение")

    vk.delete = delete
    Router(vk, store, COMMANDS, OWNER, sleep=lambda _: None).handle(message("/del 3"))
    assert attempts[-4:] == [[99, 98, 97], [99], [98], [97]]


def test_download_requires_https(tmp_path):
    with pytest.raises(media.MediaError):
        media.download("http://example.com/a.png", str(tmp_path), ".png")


def test_tools_never_see_the_token(monkeypatch):
    seen = {}

    def fake_run(args, **kwargs):
        seen.update(kwargs["env"])

    monkeypatch.setenv("VK_TOKEN", "secret")
    monkeypatch.setattr(subprocess, "run", fake_run)
    media.run_tool(["ffmpeg"])
    assert "VK_TOKEN" not in seen and "secret" not in seen.values()


def test_ffmpeg_reads_only_local_files():
    assert media.FFMPEG[media.FFMPEG.index("-protocol_whitelist") + 1] == "file"
