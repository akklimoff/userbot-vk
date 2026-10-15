import copy
import json
import logging
import os
import threading
import time
from typing import Any

log = logging.getLogger("userbot-vk")


class Store:
    """Настройки бота в одном JSON-файле; каждая операция — чтение, изменение и атомарная запись под блокировкой."""

    def __init__(self, path: str):
        self._path = path
        self._lock = threading.Lock()
        self._data = self._load()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return copy.deepcopy(self._data.get(key, default))

    def add_to(self, key: str, item: int) -> bool:
        with self._lock:
            items = self._data.get(key) or []
            if item in items:
                return False
            self._save(key, [*items, item])
            return True

    def remove_from(self, key: str, item: int) -> bool:
        with self._lock:
            items = self._data.get(key) or []
            if item not in items:
                return False
            self._save(key, [i for i in items if i != item])
            return True

    def put_new(self, key: str, name: str, value: Any) -> bool:
        with self._lock:
            mapping = self._data.get(key) or {}
            if name in mapping:
                return False
            self._save(key, {**mapping, name: value})
            return True

    def pop(self, key: str, name: str) -> bool:
        with self._lock:
            mapping = self._data.get(key) or {}
            if name not in mapping:
                return False
            self._save(key, {k: v for k, v in mapping.items() if k != name})
            return True

    def toggle(self, key: str) -> bool:
        with self._lock:
            value = not self._data.get(key, False)
            self._save(key, value)
            return value

    def _load(self) -> dict:
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            raise ValueError("ожидался JSON-объект")
        except FileNotFoundError:
            return {}
        except (ValueError, UnicodeDecodeError):
            broken = f"{self._path}.broken-{int(time.time())}"
            os.replace(self._path, broken)
            log.exception("%s не читается, сохранён как %s, начинаю с пустых настроек", self._path, broken)
            return {}

    def _save(self, key: str, value: Any) -> None:
        data = {**self._data, key: value}
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        tmp = f"{self._path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self._path)
        self._data = data
