import os
import tempfile
from collections.abc import Callable

from userbot import media
from userbot.attachments import image_source
from userbot.context import ERROR, INVALID, Command, Context

NEED_IMAGE = f"{ERROR} Нужна фотография — прикрепите её или ответьте на фото или стикер"
DIST_USAGE = f"{INVALID} Так: /d или /d 1…10 — чем больше число, тем сильнее жмых"
MAX_CAPTION = 200


def dist_percent(args: list[str]) -> int | None:
    if len(args) < 2:
        return 50
    if not args[1].isdecimal() or not 1 <= int(args[1]) <= 10:
        return None
    return 50 - 5 * (int(args[1]) - 1)


def transform(ctx: Context, source: tuple[str, str], change: Callable[[str, str], None]) -> None:
    url, kind = source
    with media.heavy_slot(), tempfile.TemporaryDirectory() as tmp:
        result = os.path.join(tmp, "result.png")
        change(media.download(url, tmp, ".png"), result)
        if kind == "sticker":
            attachment = ctx.vk.upload_graffiti(result, ctx.peer_id)
        else:
            attachment = ctx.vk.upload_photo(result, ctx.peer_id)
    ctx.result(attachment=attachment)


def dist(ctx: Context) -> None:
    source = image_source(ctx.message)
    if source is None:
        ctx.fail(NEED_IMAGE)
    percent = dist_percent(ctx.args)
    if percent is None:
        ctx.fail(DIST_USAGE)
    transform(ctx, source, lambda src, dst: media.liquid_rescale(src, dst, percent))


def negative(ctx: Context) -> None:
    source = image_source(ctx.message)
    if source is None:
        ctx.fail(NEED_IMAGE)
    transform(ctx, source, media.negate)


def caption(ctx: Context) -> None:
    source = image_source(ctx.message)
    text = ctx.rest(1)
    if source is None or source[1] != "photo" or not text:
        ctx.fail(f"{ERROR} Нужны фото и текст: /t ваш текст")
    if len(text) > MAX_CAPTION:
        ctx.fail(f"{INVALID} Подпись длиннее {MAX_CAPTION} символов — покороче, пожалуйста")
    transform(ctx, source, lambda src, dst: media.add_caption(src, dst, text))


COMMANDS = [
    Command(("/d", "/dist"), dist, "жмых фото или стикера", icon="🫧", usage="[1-10]"),
    Command(("/n", "/negative"), negative, "негатив фото или стикера", icon="🪞"),
    Command(("/t", "/text"), caption, "подпись к фото, до 200 символов", icon="💌", usage="[текст]"),
]
