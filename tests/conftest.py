import pytest

from tests.fakes import FakeVk
from userbot.commands import COMMANDS
from userbot.router import Router
from userbot.store import Store


@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path / "data.json"))


@pytest.fixture
def vk():
    return FakeVk()


@pytest.fixture
def router(vk, store):
    return Router(vk, store, COMMANDS, vk.me_id, sleep=lambda _: None)
