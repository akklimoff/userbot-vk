import os
import re
import subprocess
import threading
import time
from contextlib import contextmanager
from urllib.parse import urlparse

import requests

DOWNLOAD_TIMEOUT = 15
DOWNLOAD_DEADLINE = 60
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
TOOL_TIMEOUT = 120
HEAVY_JOBS = 2

# внешним программам не передаём окружение с VK_TOKEN: уязвимость чтения файлов в них не должна раскрыть токен
TOOL_ENV = {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "HOME": "/tmp"}
# ffmpeg читает только локальный файл: плейлисты (HLS, concat) не должны тянуть что-то из сети или с диска
FFMPEG = ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-protocol_whitelist", "file"]

VOICE_EFFECTS = {
    "1": "chorus=0.5:0.9:50|60|40:0.4|0.32|0.3:0.25|0.4|0.3:2|2.3|1.3,vibrato=f=15",
    "2": "chorus=0.5:0.9:50|60|40:0.4|0.32|0.3:0.25|0.4|0.3:2|2.3|1.3,vibrato=f=35",
    "3": "chorus=0.5:0.9:50|60|40:0.4|0.32|0.3:0.25|0.4|0.3:2|2.3|1.3,vibrato=f=10",
    "4": "afftfilt=real='hypot(re,im)*sin(0)':imag='hypot(re,im)*cos(0)':win_size=512:overlap=0.75",
}


class MediaError(Exception):
    pass


class MediaBusy(MediaError):
    pass


_heavy = threading.BoundedSemaphore(HEAVY_JOBS)


# ffmpeg съедает CPU и сотни мегабайт: без лимита публичные команды кладут контейнер по OOM
@contextmanager
def heavy_slot():
    if not _heavy.acquire(blocking=False):
        raise MediaBusy()
    try:
        yield
    finally:
        _heavy.release()


def local_name(url: str, default_suffix: str) -> str:
    suffix = os.path.splitext(urlparse(url).path)[1].lower()
    return "input" + (suffix if re.fullmatch(r"\.[a-z0-9]{1,5}", suffix) else default_suffix)


def download(url: str, directory: str, default_suffix: str) -> str:
    if urlparse(url).scheme != "https":
        raise MediaError("файл доступен не по https")
    path = os.path.join(directory, local_name(url, default_suffix))
    deadline = time.monotonic() + DOWNLOAD_DEADLINE
    try:
        with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as response:
            response.raise_for_status()
            size = 0
            with open(path, "wb") as f:
                for chunk in response.iter_content(64 * 1024):
                    size += len(chunk)
                    if size > MAX_DOWNLOAD_BYTES:
                        raise MediaError("файл больше 50 МБ")
                    if time.monotonic() > deadline:
                        raise MediaError("файл качается слишком долго")
                    f.write(chunk)
    except requests.RequestException as e:
        raise MediaError(f"не удалось скачать файл: {e}") from e
    return path


def run_tool(args: list[str]) -> None:
    try:
        subprocess.run(args, check=True, capture_output=True, timeout=TOOL_TIMEOUT, env=TOOL_ENV)
    except (OSError, subprocess.SubprocessError) as e:
        raise MediaError(f"{args[0]} не отработал: {e}") from e


def apply_voice_effect(source: str, target: str, effect: str) -> None:
    run_tool([*FFMPEG, "-i", source, "-af", VOICE_EFFECTS[effect], target])
