import logging
import os
import re
import shutil
from dataclasses import dataclass

from userbot.store import Store

# голосовое VK — сотни килобайт; предел не даёт доверенному забить диск хоста файлами по 50 МБ
MAX_VOICE_BYTES = 10 * 1024 * 1024

log = logging.getLogger("userbot-vk")


# название задаёт пользователь: «/» увёл бы файл из папки аккаунта, ведущая точка — спрятала; «%» кодируется,
# чтобы разные названия не сошлись в одно имя файла
def file_name(key: str) -> str:
    safe = re.sub(r"[/\\%\x00-\x1f]", lambda found: f"%{ord(found.group()):02X}", key)
    if safe.startswith("."):
        safe = "%2E" + safe[1:]
    return f"{safe}.ogg"


class Library:
    """Файлы сохранённых голосовых одного аккаунта. Ссылка на документ VK живёт в Store, здесь — сам звук."""

    def __init__(self, directory: str):
        self._directory = directory

    # сохранённое голосовое работает и без файла, поэтому сбой диска не срывает команду
    def keep(self, key: str, source: str) -> None:
        path = os.path.join(self._directory, file_name(key))
        try:
            if os.path.getsize(source) > MAX_VOICE_BYTES:
                log.warning("Голосовое «%s» слишком большое, файл не записан", key)
                return
            os.makedirs(self._directory, exist_ok=True)
            shutil.copyfile(source, f"{path}.tmp")
            os.replace(f"{path}.tmp", path)
        except OSError:
            log.warning("Файл голосового «%s» не записан в %s", key, self._directory, exc_info=True)

    def forget(self, key: str) -> None:
        try:
            os.remove(os.path.join(self._directory, file_name(key)))
        except FileNotFoundError:
            pass
        except OSError:
            log.warning("Файл голосового «%s» не удалён из %s", key, self._directory, exc_info=True)

    def path(self, key: str) -> str | None:
        path = os.path.join(self._directory, file_name(key))
        return path if os.path.isfile(path) else None


@dataclass(frozen=True)
class Shelf:
    store: Store
    library: Library
