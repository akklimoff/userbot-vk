import ast
from pathlib import Path

import pytest

from userbot.safety import looks_like_command

ROOT = Path(__file__).resolve().parent.parent


def modules_importing(module: str) -> set[str]:
    users = set()
    for path in (ROOT / "userbot").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            if any(n.split(".")[0] == module for n in names):
                users.add(str(path.relative_to(ROOT)))
    return users


def test_vk_api_only_in_vk_module():
    assert modules_importing("vk_api") == {"userbot/vk.py"}


def test_processes_only_in_media_module():
    assert modules_importing("subprocess") == {"userbot/media.py"}


def test_no_shell_calls():
    for path in (ROOT / "userbot").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "os.system" not in source and "shell=True" not in source, path


@pytest.mark.parametrize("text", ["/ban 1", "!help", "бан @x", "Мут", "-смс", "помощь"])
def test_command_like_texts(text):
    assert looks_like_command(text)


@pytest.mark.parametrize("text", [None, "", "✅ | готово", "помощь нужна?", "смс пришло", "🚑 Доступные команды"])
def test_plain_texts(text):
    assert not looks_like_command(text)
