import os
import tempfile

from userbot import media
from userbot.attachments import source_attachment, voice_url
from userbot.context import ERROR, INVALID, SUCCESS, Access, Command, Context

SAVED = "saved_audio"
NEED_VOICE = f"{ERROR} Нужно ответить на голосовое"
AUDIO_USAGE = (f"{INVALID} Так: /au 1…4 ответом на голосовое\n\n"
               "🎤 1 — обычный жмых\n🔥 2 — сильный\n🍃 3 — слабый\n🤖 4 — робот")


def reupload_voice(ctx: Context, url: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        return ctx.vk.upload_voice(media.download(url, tmp, ".ogg"), ctx.peer_id)


def copy(ctx: Context) -> None:
    url = voice_url(ctx.reply_message)
    if url is None:
        ctx.fail(NEED_VOICE)
    ctx.delete()
    ctx.send(attachment=reupload_voice(ctx, url), reply=False)


def distort(ctx: Context) -> None:
    url = voice_url(ctx.reply_message)
    if url is None:
        ctx.fail(NEED_VOICE)
    args = ctx.args
    if len(args) < 2 or args[1] not in media.VOICE_EFFECTS:
        ctx.fail(AUDIO_USAGE)
    with media.heavy_slot(), tempfile.TemporaryDirectory() as tmp:
        result = os.path.join(tmp, "result.ogg")
        media.apply_voice_effect(media.download(url, tmp, ".ogg"), result, args[1])
        voice = ctx.vk.upload_voice(result, ctx.peer_id)
    ctx.send(attachment=voice)


def song(ctx: Context) -> None:
    attachment = source_attachment(ctx.message)
    audio = attachment.get("audio") if attachment else None
    if not audio or not audio.get("url"):
        ctx.fail(f"{ERROR} Нужна аудиозапись — прикрепите её или ответьте на неё")
    with media.heavy_slot(), tempfile.TemporaryDirectory() as tmp:
        result = os.path.join(tmp, "result.wav")
        media.song_to_voice(media.download(audio["url"], tmp, ".mp3"), result)
        voice = ctx.vk.upload_voice(result, ctx.peer_id)
    ctx.send(attachment=voice, reply=not ctx.is_owner)


def next_free_number(saved: dict) -> str:
    number = 1
    while str(number) in saved:
        number += 1
    return str(number)


def save(ctx: Context) -> None:
    url = voice_url(ctx.reply_message)
    if url is None:
        ctx.fail(NEED_VOICE)
    saved = ctx.store.get(SAVED, {})
    key = ctx.rest(1) or next_free_number(saved)
    if key in saved:
        ctx.fail(f"{INVALID} Голосовое «{key}» уже есть — выберите другое название")
    if not ctx.store.put_new(SAVED, key, reupload_voice(ctx, url)):
        ctx.fail(f"{INVALID} Голосовое «{key}» уже есть — выберите другое название")
    ctx.flash(f"{SUCCESS} Голосовое сохранено как «{key}» — отправить: /ag {key}")


def send_saved(ctx: Context) -> None:
    key = ctx.rest(1)
    if not key:
        ctx.fail(f"{INVALID} Так: /ag название")
    voice = ctx.store.get(SAVED, {}).get(key)
    if voice is None:
        ctx.fail(f"{INVALID} Голосового «{key}» нет — список в /alist")
    ctx.hide()
    reply = ctx.reply_message
    ctx.post(attachment=voice, reply_to=reply["id"] if reply else None)


def delete_saved(ctx: Context) -> None:
    key = ctx.rest(1)
    if not key:
        ctx.fail(f"{INVALID} Так: /ad название")
    if not ctx.store.pop(SAVED, key):
        ctx.fail(f"{INVALID} Голосового «{key}» нет — список в /alist")
    ctx.flash(f"{SUCCESS} Голосовое «{key}» удалено")


def list_saved(ctx: Context) -> None:
    saved = ctx.store.get(SAVED, {})
    if not saved:
        ctx.fail(f"{INVALID} Сохранённых голосовых пока нет")
    ctx.answer("\n".join(["📒 Сохранённые голосовые", "", *(f"🎀 {key}" for key in saved)]))


COMMANDS = [
    Command(("/au", "/audio"), distort, "жмых голосового (ответом)", icon="🎤", usage="[1-4]"),
    Command(("/ma", "/music_audio"), song, "превратить песню в голосовое", icon="🎶"),
    Command(("/copy",), copy, "скопировать чужое голосовое (ответом)", Access.TRUSTED, "🎙"),
    Command(("/sa", "/save_audio"), save, "сохранить голосовое (ответом), без названия — под номером", Access.TRUSTED, "💾", "[название]"),
    Command(("/ag", "/aget"), send_saved, "отправить сохранённое голосовое", Access.TRUSTED, "💿", "[название]"),
    Command(("/ad", "/adelete"), delete_saved, "удалить сохранённое голосовое", Access.TRUSTED, "🗑", "[название]"),
    Command(("/alist",), list_saved, "список сохранённых голосовых", Access.TRUSTED, "📒"),
]
