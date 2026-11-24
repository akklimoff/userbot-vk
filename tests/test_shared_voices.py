import pytest

from tests.fakes import CHAT, OWNER, STRANGER, FakeVk, in_peer, message, user
from userbot.commands import COMMANDS
from userbot.library import Library, Shelf
from userbot.router import Router
from userbot.store import Store

ADMIN = 7
LELYA = 30
YANA, YANA_TWIN = 31, 32
CIRCLE_ID = "video_message9_7_k"


@pytest.fixture
def vk():
    people = {LELYA: {"id": LELYA, "first_name": "Лёля", "last_name": "Даняева"},
              YANA: {"id": YANA, "first_name": "Yana", "last_name": "Nikolaevna"},
              YANA_TWIN: {"id": YANA_TWIN, "first_name": "Yana", "last_name": "Nikolaevna"},
              "lelya_tag": {"id": LELYA, "first_name": "Лёля", "last_name": "Даняева"}, ADMIN: user(ADMIN)}
    return FakeVk(users=people)


def shelf(tmp_path, account, saved, files=()):
    store = Store(str(tmp_path / f"{account}.json"))
    library = Library(str(tmp_path / "saved" / str(account)))
    source = tmp_path / "source.ogg"
    source.write_bytes(f"OggS-{account}".encode())
    for key, attachment in saved.items():
        store.put_new("saved_audio", key, attachment)
    for key in files:
        library.keep(key, str(source))
    return Shelf(store, library)


@pytest.fixture
def shelves(tmp_path, store, library_dir):
    return {OWNER: Shelf(store, Library(str(library_dir))),
            LELYA: shelf(tmp_path, LELYA, {"привет мир": "audio_message30_1_k", "круг": CIRCLE_ID, "старое": "audio_message30_2_k"},
                         files=["привет мир"]),
            YANA: shelf(tmp_path, YANA, {"яна": "audio_message31_1_k"}, files=["яна"]),
            YANA_TWIN: shelf(tmp_path, YANA_TWIN, {})}


@pytest.fixture
def router(vk, store, shelves):
    store.add_to("trusted", ADMIN)
    store.add_to("trusted", STRANGER)
    return Router(vk, store, COMMANDS, vk.me_id, sleep=lambda _: None, library=shelves[OWNER].library,
                  admins=frozenset({ADMIN}), shelves=shelves)


def by_admin(text):
    return message(text, from_id=ADMIN)


@pytest.mark.parametrize("ref", [str(LELYA), f"id{LELYA}", "Лёля", "даняева", "@lelya_tag", "https://vk.com/lelya_tag",
                                 f"[id{LELYA}|Лёля Даняева]"])
def test_admin_sends_voice_of_another_account_as_own_upload(router, vk, tmp_path, ref):
    router.handle(by_admin(f"/гс {ref} привет мир"))
    assert in_peer(vk, CHAT) == [{"peer_id": CHAT, "text": None, "attachment": "audio_message1_10"}]
    [(_, path)] = vk.uploads
    assert open(path, "rb").read() == b"OggS-30"


def test_own_voice_wins_over_account_reference(router, vk, store):
    store.put_new("saved_audio", f"{LELYA} привет мир", "audio_message1_5")
    router.handle(by_admin(f"/гс {LELYA} привет мир"))
    assert in_peer(vk, CHAT)[0]["attachment"] == "audio_message1_5" and vk.uploads == []


def test_admin_sends_circle_of_another_account_by_reference(router, vk):
    router.handle(by_admin(f"/гс {LELYA} круг"))
    assert in_peer(vk, CHAT)[0]["attachment"] == CIRCLE_ID and vk.uploads == []


def test_trusted_user_cannot_reach_other_accounts(router, vk):
    router.handle(message(f"/гс {LELYA} привет мир", from_id=STRANGER))
    assert in_peer(vk, CHAT) == [] and vk.uploads == []


def test_voice_without_file_is_reported(router, vk):
    router.handle(by_admin(f"/гс {LELYA} старое"))
    assert in_peer(vk, CHAT) == []
    assert "нет файла" in in_peer(vk, ADMIN)[0]["text"]


def test_missing_name_in_another_account_is_reported(router, vk):
    router.handle(by_admin(f"/гс {LELYA} нет такого"))
    assert f"/гсы {LELYA}" in in_peer(vk, ADMIN)[0]["text"]


def test_ambiguous_name_asks_for_id(router, vk):
    router.handle(by_admin("/гс Yana яна"))
    text = in_peer(vk, ADMIN)[0]["text"]
    assert in_peer(vk, CHAT) == [] and str(YANA) in text and str(YANA_TWIN) in text


def test_admin_list_shows_accounts_with_ids(router, vk, store):
    store.put_new("saved_audio", "моё", "audio_message1_5")
    router.handle(by_admin("/гсы"))
    text = in_peer(vk, ADMIN)[0]["text"]
    assert "🎀 моё" in text and f"Лёля Даняева — {LELYA} (3)" in text and f"Yana Nikolaevna — {YANA} (1)" in text
    assert str(YANA_TWIN) not in text and "[id" not in text


def test_admin_lists_saved_of_another_account(router, vk):
    router.handle(by_admin(f"/гсы {LELYA}"))
    text = in_peer(vk, ADMIN)[0]["text"]
    assert str(LELYA) in text and "🎀 привет мир" in text and "📹 круг" in text


def test_trusted_user_list_has_no_accounts(router, vk, store):
    store.put_new("saved_audio", "моё", "audio_message1_5")
    router.handle(message("/гсы", from_id=STRANGER))
    assert "Лёля" not in in_peer(vk, STRANGER)[0]["text"]


def test_owner_listed_in_admins_is_admin_on_own_account(vk, store, shelves):
    router = Router(vk, store, COMMANDS, vk.me_id, sleep=lambda _: None, admins=frozenset({OWNER}), shelves=shelves)
    router.handle(message(f"/гс {LELYA} привет мир"))
    assert in_peer(vk, CHAT)[0]["attachment"] == "audio_message1_10"


def test_reports_carry_no_mention_markup(router, vk):
    router.handle(by_admin(f"/гс [id{OWNER}|Я] привет"))
    router.handle(by_admin(f"/гс {LELYA} [id{OWNER}|Я]"))
    assert all("[id" not in sent["text"] for sent in in_peer(vk, ADMIN)) and len(in_peer(vk, ADMIN)) == 2


def test_account_id_works_while_vk_does_not_answer(router, vk):
    vk.users = lambda user_ids: []
    router.handle(by_admin(f"/гс {LELYA} привет мир"))
    router.handle(by_admin(f"/гсы {LELYA}"))
    router.handle(by_admin("/гсы"))
    assert in_peer(vk, CHAT)[0]["attachment"] == "audio_message1_10"
    assert "🎀 привет мир" in in_peer(vk, ADMIN)[0]["text"] and f"аккаунт — {LELYA} (3)" in in_peer(vk, ADMIN)[1]["text"]


def test_failed_foreign_upload_is_reported_without_delete_hint(router, vk):
    def broken(path, peer_id):
        raise RuntimeError("upload failed")

    vk.upload_voice = broken
    router.handle(by_admin(f"/гс {LELYA} привет мир"))
    text = in_peer(vk, ADMIN)[0]["text"]
    assert "не отправилось" in text and "/угс" not in text


def test_trusted_user_list_ignores_account_reference(router, vk, store):
    store.put_new("saved_audio", "моё", "audio_message1_5")
    router.handle(message(f"/гсы {LELYA}", from_id=STRANGER))
    assert "привет мир" not in in_peer(vk, STRANGER)[0]["text"]


def test_oversized_voice_gets_no_file(tmp_path, monkeypatch):
    from userbot import library
    monkeypatch.setattr(library, "MAX_VOICE_BYTES", 3)
    source = tmp_path / "big.ogg"
    source.write_bytes(b"OggS-big")
    Library(str(tmp_path / "lib")).keep("1", str(source))
    assert Library(str(tmp_path / "lib")).path("1") is None


def test_admin_sends_unique_foreign_voice_by_name_alone(router, vk):
    router.handle(by_admin("/гс привет мир"))
    assert in_peer(vk, CHAT)[0]["attachment"] == "audio_message1_10"
    assert open(vk.uploads[0][1], "rb").read() == b"OggS-30"


def test_name_saved_by_several_accounts_needs_an_id(router, vk, shelves, tmp_path):
    shelves[YANA].store.put_new("saved_audio", "привет мир", "audio_message31_2_k")
    router.handle(by_admin("/гс привет мир"))
    text = in_peer(vk, ADMIN)[0]["text"]
    assert in_peer(vk, CHAT) == [] and str(LELYA) in text and str(YANA) in text
    router.handle(by_admin(f"/гс {LELYA} привет мир"))
    assert in_peer(vk, CHAT)[0]["attachment"] == "audio_message1_10"


def test_trusted_user_cannot_send_foreign_voice_by_name(router, vk):
    router.handle(message("/гс привет мир", from_id=STRANGER))
    assert in_peer(vk, CHAT) == [] and vk.uploads == []
