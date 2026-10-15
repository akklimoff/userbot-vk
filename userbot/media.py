import os
import re
import shutil
import subprocess
import textwrap
from urllib.parse import urlparse

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

DOWNLOAD_TIMEOUT = 30
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
TOOL_TIMEOUT = 120
FONT_SIZE = 24
FONT_CANDIDATES = ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "Arial Unicode.ttf")

VOICE_EFFECTS = {
    "1": "chorus=0.5:0.9:50|60|40:0.4|0.32|0.3:0.25|0.4|0.3:2|2.3|1.3,vibrato=f=15",
    "2": "chorus=0.5:0.9:50|60|40:0.4|0.32|0.3:0.25|0.4|0.3:2|2.3|1.3,vibrato=f=35",
    "3": "chorus=0.5:0.9:50|60|40:0.4|0.32|0.3:0.25|0.4|0.3:2|2.3|1.3,vibrato=f=10",
    "4": "afftfilt=real='hypot(re,im)*sin(0)':imag='hypot(re,im)*cos(0)':win_size=512:overlap=0.75",
}


class MediaError(Exception):
    pass


def local_name(url: str, default_suffix: str) -> str:
    suffix = os.path.splitext(urlparse(url).path)[1].lower()
    return "input" + (suffix if re.fullmatch(r"\.[a-z0-9]{1,5}", suffix) else default_suffix)


def download(url: str, directory: str, default_suffix: str) -> str:
    path = os.path.join(directory, local_name(url, default_suffix))
    try:
        with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as response:
            response.raise_for_status()
            size = 0
            with open(path, "wb") as f:
                for chunk in response.iter_content(64 * 1024):
                    size += len(chunk)
                    if size > MAX_DOWNLOAD_BYTES:
                        raise MediaError("файл больше 50 МБ")
                    f.write(chunk)
    except requests.RequestException as e:
        raise MediaError(f"не удалось скачать файл: {e}") from e
    return path


def run_tool(args: list[str]) -> None:
    try:
        subprocess.run(args, check=True, capture_output=True, timeout=TOOL_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as e:
        raise MediaError(f"{args[0]} не отработал: {e}") from e


def apply_voice_effect(source: str, target: str, effect: str) -> None:
    run_tool(["ffmpeg", "-y", "-loglevel", "error", "-i", source, "-af", VOICE_EFFECTS[effect], target])


def song_to_voice(source: str, target: str) -> None:
    run_tool(["ffmpeg", "-y", "-loglevel", "error", "-i", source,
              "-acodec", "pcm_s32le", "-ar", "44100", "-ac", "1", "-b:a", "256k", target])


def liquid_rescale(source: str, target: str, percent: int) -> None:
    # в Debian с ImageMagick 7 есть только magick, в старых сборках — только convert
    binary = "magick" if shutil.which("magick") else "convert"
    run_tool([binary, source, "-liquid-rescale", f"{percent}x{percent}%", f"png:{target}"])


def negate(source: str, target: str) -> None:
    image = Image.open(source)
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
    picture = ImageOps.expand(ImageOps.expand(Image.open(source).convert("RGB"), 3, "black"), 2, "white")
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
