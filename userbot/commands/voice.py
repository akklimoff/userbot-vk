import logging
import tempfile

from userbot import media
from userbot.attachments import circle_id, is_circle_id, voice_url
from userbot.context import ERROR, INVALID, SUCCESS, Access, Command, Context

SAVED = "saved_audio"
NEED_VOICE_OR_CIRCLE = f"{ERROR} Нужно ответить на голосовое или кружочек"

log = logging.getLogger("userbot-vk")


def reupload_voice(ctx: Context, url: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        return ctx.vk.upload_voice(media.download(url, tmp, ".ogg"), ctx.peer_id)


def require_voice_or_circle(ctx: Context) -> None:
    if voice_url(ctx.reply_message) is None and circle_id(ctx.reply_message) is None:
        ctx.fail(NEED_VOICE_OR_CIRCLE)


# VK не даёт загрузить кружочек, поэтому его копия — ссылка на оригинал, а голосовое загружается заново
def copy_of_reply(ctx: Context) -> tuple[str, bool]:
    url = voice_url(ctx.reply_message)
    if url is not None:
        return reupload_voice(ctx, url), False
    circle = circle_id(ctx.reply_message)
    if circle is None:
        ctx.fail(NEED_VOICE_OR_CIRCLE)
    return circle, True


def copy(ctx: Context) -> None:
    require_voice_or_circle(ctx)
    ctx.delete()
    attachment, _ = copy_of_reply(ctx)
    ctx.post(attachment=attachment)


def next_free_number(saved: dict) -> str:
    number = 1
    while str(number) in saved:
        number += 1
    return str(number)


def taken(key: str) -> str:
    return f"{INVALID} «{key}» уже сохранено — выберите другое название"


def missing(key: str) -> str:
    return f"{INVALID} «{key}» не сохранено — список в /гсы"


def save(ctx: Context) -> None:
    require_voice_or_circle(ctx)
    saved = ctx.store.get(SAVED, {})
    named = ctx.rest(1)
    key = named or next_free_number(saved)
    if key in saved:
        ctx.fail(taken(key))
    attachment, circle = copy_of_reply(ctx)
    if not ctx.store.put_new(SAVED, key, attachment):
        ctx.fail(taken(key))
    what = "Кружочек сохранён" if circle else "Голосовое сохранено"
    text = f"{SUCCESS} {what} как «{key}» — отправить: /гс {key}"
    if named:
        ctx.done(text)
    else:
        ctx.answer(text)


def send_saved(ctx: Context) -> None:
    key = ctx.rest(1)
    if not key:
        ctx.fail(f"{INVALID} Так: /гс название")
    attachment = ctx.store.get(SAVED, {}).get(key)
    if attachment is None:
        ctx.fail(missing(key))
    ctx.hide()
    if not is_circle_id(attachment):
        ctx.result(attachment=attachment)
        return
    try:
        ctx.result(attachment=attachment)
    except Exception:
        log.warning("Сохранённый кружочек не отправился в %s", ctx.peer_id, exc_info=True)
        ctx.report(f"{ERROR} Кружочек «{key}» не отправился. Если так снова и снова — оригинал, скорее всего, "
                   f"удалили, убрать: /угс {key}")


def delete_saved(ctx: Context) -> None:
    key = ctx.rest(1)
    if not key:
        ctx.fail(f"{INVALID} Так: /угс название")
    if not ctx.store.pop(SAVED, key):
        ctx.fail(missing(key))
    ctx.done(f"{SUCCESS} «{key}» удалено из сохранённых")


def list_saved(ctx: Context) -> None:
    saved: dict[str, str] = ctx.store.get(SAVED, {})
    if not saved:
        ctx.fail(f"{INVALID} Сохранённых голосовых и кружочков пока нет")
    lines = [f"{'📹' if is_circle_id(attachment) else '🎀'} {key}" for key, attachment in saved.items()]
    ctx.answer("\n".join(["📒 Сохранённые голосовые и кружочки", "", *lines]))


COMMANDS = [
    Command(("/кгс", "/копия", "/copy"), copy, "скопировать чужое голосовое или кружочек (ответом)",
            Access.TRUSTED, "🎙"),
    Command(("/сгс", "/сохр", "/sa", "/save_audio"), save,
            "сохранить голосовое или кружочек (ответом), без названия — под номером", Access.TRUSTED, "💾", "[название]"),
    Command(("/гс", "/голос", "/ag", "/aget"), send_saved, "отправить сохранённое голосовое или кружочек",
            Access.TRUSTED, "💿", "[название]"),
    Command(("/угс", "/удгс", "/ad", "/adelete"), delete_saved, "удалить сохранённое голосовое или кружочек",
            Access.TRUSTED, "🗑", "[название]"),
    Command(("/гсы", "/моигс", "/alist"), list_saved, "список сохранённых голосовых и кружочков", Access.TRUSTED, "📒"),
]
