import json

import pytest
from pydantic import ValidationError

from tests.fakes import CHAT, OWNER, STRANGER, FakeVk, message
from userbot import main
from userbot.commands import COMMANDS
from userbot.config import Settings
from userbot.main import Dispatcher, serve, serve_account, state_path
from userbot.router import Router
from userbot.vk import Incoming

OTHER_ACCOUNT = 3


@pytest.fixture(autouse=True)
def no_env_tokens(monkeypatch):
    for name in ("VK_TOKEN", "ACCESS_TOKEN", "VK_TOKENS"):
        monkeypatch.delenv(name, raising=False)


def settings(**values) -> Settings:
    return Settings(_env_file=None, **values)


def test_tokens_join_vk_token_and_vk_tokens_without_duplicates():
    assert settings(VK_TOKEN="a", VK_TOKENS=" b, a,,c ").tokens == ["a", "b", "c"]


def test_vk_tokens_alone_are_enough():
    assert settings(VK_TOKENS="a,b").tokens == ["a", "b"]


def test_some_token_is_required():
    with pytest.raises(ValidationError):
        settings(VK_TOKENS=" , ")


def test_failed_account_restarts_the_container(monkeypatch):
    def broken(*args):
        raise PermissionError("state недоступен")

    exits = []
    monkeypatch.setattr(main, "serve_account", broken)
    monkeypatch.setattr(main.os, "_exit", exits.append)
    serve(1, "a", settings(VK_TOKEN="a"), {})
    assert exits == [1]


def test_legacy_state_is_copied_to_first_account(tmp_path):
    (tmp_path / "data.json").write_text(json.dumps({"banned": [5]}))
    path = state_path(str(tmp_path), OWNER, first=True)
    assert json.loads(open(path).read()) == {"banned": [5]}
    assert (tmp_path / "data.json").exists()


def test_legacy_state_is_not_given_to_other_accounts(tmp_path):
    (tmp_path / "data.json").write_text("{}")
    state_path(str(tmp_path), OTHER_ACCOUNT, first=False)
    assert (tmp_path / "data.json").exists() and not (tmp_path / f"{OTHER_ACCOUNT}.json").exists()


def test_legacy_state_never_overwrites_account_state(tmp_path):
    (tmp_path / "data.json").write_text(json.dumps({"banned": [5]}))
    (tmp_path / f"{OWNER}.json").write_text(json.dumps({"banned": [7]}))
    state_path(str(tmp_path), OWNER, first=True)
    assert json.loads((tmp_path / f"{OWNER}.json").read_text()) == {"banned": [7]}


@pytest.fixture
def shared_router(vk, store):
    return Router(vk, store, COMMANDS, vk.me_id, sleep=lambda _: None, own_accounts={OWNER: 1, OTHER_ACCOUNT: 2})


def test_commands_of_other_own_accounts_are_skipped(shared_router, vk):
    shared_router.handle(message("/ид 2", from_id=OTHER_ACCOUNT))
    assert vk.sent == [] and vk.deleted == []


def test_own_account_and_strangers_still_run_commands(shared_router, vk):
    shared_router.handle(message("/ид 2", from_id=STRANGER, peer_id=STRANGER))
    shared_router.handle(message("/скажи ура"))
    assert [m["text"] for m in vk.sent][-1] == "ура" and len(vk.sent) == 2


def test_other_account_messages_are_not_fetched(shared_router, vk):
    fetched = []
    vk.message = lambda message_id: fetched.append(message_id)
    Dispatcher(vk, shared_router, None, False).dispatch(Incoming(100, CHAT, "/ид 2", OTHER_ACCOUNT))
    assert fetched == []


def test_second_token_of_the_same_account_is_skipped(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "connect", lambda number, token: FakeVk())
    monkeypatch.setattr(main, "listen_forever", lambda *args: pytest.fail("второй токен слушает тот же аккаунт"))
    accounts = {OWNER: 1}
    serve_account(2, "b", settings(VK_TOKEN="a", STATE_DIR=str(tmp_path)), accounts)
    assert accounts == {OWNER: 1}


def test_connect_retries_until_token_works(monkeypatch):
    attempts = []

    def flaky_client(token):
        attempts.append(token)
        if len(attempts) < 3:
            raise RuntimeError("invalid token")
        return "client"

    monkeypatch.setattr(main, "VkClient", flaky_client)
    pauses = []
    assert main.connect(1, "a", sleep=pauses.append) == "client"
    assert len(attempts) == 3 and pauses == [main.CONNECT_RETRY_SECONDS] * 2
