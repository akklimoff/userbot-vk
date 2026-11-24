import pytest

from tests.fakes import FakeVk
from userbot.commands import COMMANDS
from userbot.library import Library
from userbot.router import Router
from userbot.store import Store


@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path / "data.json"))


@pytest.fixture
def vk():
    return FakeVk()


@pytest.fixture
def library_dir(tmp_path):
    return tmp_path / "saved" / str(FakeVk().me_id)


@pytest.fixture
def router(vk, store, library_dir):
    return Router(vk, store, COMMANDS, vk.me_id, sleep=lambda _: None, library=Library(str(library_dir)))
