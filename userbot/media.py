import os
import re
import shutil
import subprocess
import textwrap
import threading
import time
from contextlib import contextmanager
from urllib.parse import urlparse

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

DOWNLOAD_TIMEOUT = 15
DOWNLOAD_DEADLINE = 60
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
MAX_PIXELS = 40_000_000
IMAGE_FORMATS = ("JPEG", "PNG", "WEBP", "GIF")
TOOL_TIMEOUT = 120
FONT_SIZE = 24
HEAVY_JOBS = 2
MAX_RESCALE_SIDE = 1024
FONT_CANDIDATES = ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "Arial Unicode.ttf")

# внешним программам не передаём окружение с VK_TOKEN: уязвимость чтения файлов в них не должна раскрыть токен
TOOL_ENV = {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "HOME": "/tmp",
            "MAGICK_THREAD_LIMIT": "1", "MAGICK_MEMORY_LIMIT": "256MiB", "MAGICK_AREA_LIMIT": "64MP"}
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


# ffmpeg и seam carving ImageMagick съедают CPU и сотни мегабайт: без лимита публичные команды кладут контейнер по OOM
@contextmanager
def heavy_slot():
    if not _heavy.acquire(blocking=False):
        raise MediaBusy()
    try:
        yield
    finally:
        _heavy.release()


def open_image(path: str) -> Image.Image:
    try:
        image = Image.open(path, formats=IMAGE_FORMATS)
        if image.width * image.height > MAX_PIXELS:
            raise MediaError("картинка слишком большая")
        image.load()
    except (OSError, Image.DecompressionBombError) as e:
        raise MediaError(f"не удалось открыть картинку: {e}") from e
    return image


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


def song_to_voice(source: str, target: str) -> None:
    run_tool([*FFMPEG, "-i", source, "-acodec", "pcm_s32le", "-ar", "44100", "-ac", "1", "-b:a", "256k", target])


# ImageMagick получает только PNG, пересобранный Pillow: его декодеры SVG/MVG/MSL до чужого файла не доходят
def liquid_rescale(source: str, target: str, percent: int) -> None:
    clean = os.path.join(os.path.dirname(target), "clean.png")
    image = open_image(source)
    image.thumbnail((MAX_RESCALE_SIDE, MAX_RESCALE_SIDE))
    image.save(clean, format="PNG")
    # в Debian с ImageMagick 7 есть только magick, в старых сборках — только convert
    binary = "magick" if shutil.which("magick") else "convert"
    run_tool([binary, f"png:{clean}", "-liquid-rescale", f"{percent}x{percent}%", f"png:{target}"])


def negate(source: str, target: str) -> None:
    image = open_image(source)
    if image.mode in ("P", "LA", "PA") or "transparency" in image.info:
        image = image.convert("RGBA")
    if image.mode == "RGBA":
        *colors, alpha = image.split()
        inverted = ImageOps.invert(Image.merge("RGB", colors))
        Image.merge("RGBA", (*inverted.split(), alpha)).save(target, format="PNG")
    else:
        ImageOps.invert(image.convert("RGB")).save(target, format="PNG")


def caption_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, FONT_SIZE)
        except OSError:
            continue
    return ImageFont.load_default(FONT_SIZE)


# текст рисуется Pillow, а не ImageMagick: в label: строка с @ читает файл с диска, а через shell — выполняет команды
def add_caption(source: str, target: str, text: str) -> None:
    picture = ImageOps.expand(ImageOps.expand(open_image(source).convert("RGB"), 3, "black"), 2, "white")
    font = caption_font()
    draw = ImageDraw.Draw(picture)
    chars_per_line = max(10, picture.width // max(1, int(draw.textlength("о", font=font))))
    caption = "\n".join(textwrap.wrap(text, chars_per_line)) or " "
    left, top, right, bottom = draw.multiline_textbbox((0, 0), caption, font=font, align="center")
    width = max(picture.width, right - left) + 40
    canvas = Image.new("RGB", (width, picture.height + (bottom - top) + 70), "black")
    canvas.paste(picture, ((width - picture.width) // 2, 20))
    ImageDraw.Draw(canvas).multiline_text((width // 2, picture.height + 40), caption, fill="white", font=font,
                                          anchor="ma", align="center")
    canvas.save(target, format="PNG")
