import os
import re
import time
from urllib.parse import urlparse

import requests

DOWNLOAD_TIMEOUT = 15
DOWNLOAD_DEADLINE = 60
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024


class MediaError(Exception):
    pass


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
