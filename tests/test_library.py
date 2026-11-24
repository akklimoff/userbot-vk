import pytest

from tests.fakes import OWNER, STRANGER, message
from userbot import main, media
from userbot.library import Library, file_name

VOICE = {"type": "audio_message", "audio_message": {"owner_id": 3, "id": 7, "link_ogg": "https://x/v.ogg"}}
CIRCLE = {"type": "video", "video": {"type": "video_message", "owner_id": 9, "id": 7, "access_key": "k"}}


@pytest.fixture(autouse=True)
def downloaded_voice(monkeypatch, tmp_path):
    source = tmp_path / "v.ogg"
    source.write_bytes(b"OggS-voice")
    monkeypatch.setattr(media, "download", lambda url, directory, suffix: str(source))


def replying(text, attachment):
    return message(text, reply_message={"id": 5, "from_id": STRANGER, "attachments": [attachment]})


def test_saved_voice_is_kept_as_a_file_of_the_account(router, library_dir):
    router.handle(replying("/сгс привет мир", VOICE))
    assert (library_dir / "привет мир.ogg").read_bytes() == b"OggS-voice"


def test_deleted_voice_loses_its_file(router, library_dir):
    router.handle(replying("/сгс привет", VOICE))
    router.handle(message("/угс привет"))
    assert list(library_dir.iterdir()) == []


def test_taken_name_keeps_the_first_file(router, library_dir, tmp_path):
    router.handle(replying("/сгс привет", VOICE))
    (tmp_path / "v.ogg").write_bytes(b"OggS-other")
    router.handle(replying("/сгс привет", VOICE))
    assert (library_dir / "привет.ogg").read_bytes() == b"OggS-voice"


def test_circle_has_no_file(router, library_dir):
    router.handle(replying("/сгс круг", CIRCLE))
    assert not library_dir.exists() or list(library_dir.iterdir()) == []


def test_voice_is_saved_even_when_the_file_cannot_be_written(router, store, library_dir):
    library_dir.parent.mkdir(parents=True, exist_ok=True)
    library_dir.write_text("не папка")
    router.handle(replying("/сгс привет", VOICE))
    assert store.get("saved_audio") == {"привет": "audio_message1_10"}


@pytest.mark.parametrize("key, name", [("привет мир", "привет мир.ogg"), ("../../etc/passwd", "%2E.%2F..%2Fetc%2Fpasswd.ogg"),
                                       (".скрытое", "%2Eскрытое.ogg"), ("a%2Fb", "a%252Fb.ogg"), ("a/b", "a%2Fb.ogg")])
def test_file_name_stays_inside_the_account_directory(key, name):
    assert file_name(key) == name


def test_each_account_has_its_own_directory(tmp_path):
    assert main.library_path(str(tmp_path), OWNER) == str(tmp_path / str(OWNER))
    Library(main.library_path(str(tmp_path), OWNER)).keep("1", __file__)
    assert (tmp_path / str(OWNER) / "1.ogg").exists()
