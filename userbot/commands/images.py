import os
import tempfile
from collections.abc import Callable

from userbot import media
from userbot.attachments import image_source
from userbot.context import ERROR, INVALID, Command, Context

NEED_IMAGE = f"{ERROR} Необходимо ответить на сообщение с фотографией / стикером, либо прикрепить фотографию."
DIST_USAGE = f"{INVALID} Правильное использование: /d [степень от 1 до 10]"


def dist_percent(args: list[str]) -> int | None:
    if len(args) < 2:
        return 50
    if not args[1].isdecimal() or not 1 <= int(args[1]) <= 10:
        return None
    return 50 - 5 * (int(args[1]) - 1)


def transform(ctx: Context, source: tuple[str, str], change: Callable[[str, str], None]) -> None:
    url, kind = source
    with tempfile.TemporaryDirectory() as tmp:
        result = os.path.join(tmp, "result.png")
        change(media.download(url, tmp, ".png"), result)
        if kind == "sticker":
            attachment = ctx.vk.upload_graffiti(result, ctx.peer_id)
        else:
            attachment = ctx.vk.upload_photo(result, ctx.peer_id)
    ctx.send(attachment=attachment)


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
        ctx.fail(f"{ERROR} Необходимо прикрепить фотографию и написать текст: /text [текст]")
    transform(ctx, source, lambda src, dst: media.add_caption(src, dst, text))


COMMANDS = [
    Command(("/d", "/dist"), dist, "жмых фотографии"),
    Command(("/n", "/negative"), negative, "перевести фотографию в негатив"),
    Command(("/t", "/text"), caption, "добавить текст к фотографии"),
]
