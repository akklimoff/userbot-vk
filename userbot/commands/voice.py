import os
import tempfile

from userbot import media
from userbot.attachments import source_attachment, voice_url
from userbot.context import ERROR, INVALID, SUCCESS, Access, Command, Context

SAVED = "saved_audio"
NEED_VOICE = f"{ERROR} Необходимо ответить на голосовое сообщение."
AUDIO_USAGE = (f"{INVALID} Использование команды: /audio [1-4]\n"
               "1 - стандартный жмых\n2 - сильный жмых\n3 - слабый жмых\n4 - робот")


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
        ctx.fail(f"{ERROR} Необходимо прикрепить аудиозапись или ответить на сообщение с аудиозаписью.")
    with media.heavy_slot(), tempfile.TemporaryDirectory() as tmp:
        result = os.path.join(tmp, "result.wav")
        media.song_to_voice(media.download(audio["url"], tmp, ".mp3"), result)
        voice = ctx.vk.upload_voice(result, ctx.peer_id)
    ctx.send(attachment=voice, reply=not ctx.is_owner)


def save(ctx: Context) -> None:
    url = voice_url(ctx.reply_message)
    if url is None:
        ctx.fail(NEED_VOICE)
    key = ctx.rest(1)
    if not key:
        ctx.fail(f"{INVALID} Правильное использование: /sa [ключ]")
    if key in ctx.store.get(SAVED, {}):
        ctx.fail(f"{INVALID} Уже есть голосовое сообщение, сохранённое под таким ключом!")
    if not ctx.store.put_new(SAVED, key, reupload_voice(ctx, url)):
        ctx.fail(f"{INVALID} Уже есть голосовое сообщение, сохранённое под таким ключом!")
    ctx.flash(f"{SUCCESS} Голосовое сообщение успешно сохранено под ключом `{key}`!")


def send_saved(ctx: Context) -> None:
    key = ctx.rest(1)
    if not key:
        ctx.fail(f"{INVALID} Правильное использование: /ag [ключ]")
    voice = ctx.store.get(SAVED, {}).get(key)
    if voice is None:
        ctx.fail(f"{INVALID} Голосового сообщения с таким ключом нет!")
    ctx.hide()
    reply = ctx.reply_message
    ctx.post(attachment=voice, reply_to=reply["id"] if reply else None)


def delete_saved(ctx: Context) -> None:
    key = ctx.rest(1)
    if not key:
        ctx.fail(f"{INVALID} Правильное использование: /adelete [ключ]")
    if not ctx.store.pop(SAVED, key):
        ctx.fail(f"{INVALID} Голосового сообщения с таким ключом нет!")
    ctx.flash(f"{SUCCESS} Голосовое сообщение `{key}` было успешно удалено.")


def list_saved(ctx: Context) -> None:
    saved = ctx.store.get(SAVED, {})
    if not saved:
        ctx.fail(f"{INVALID} У Вас нет сохранённых голосовых сообщений.")
    ctx.answer(f"📖 Сохранённые голосовые сообщения: {', '.join(saved)}")


COMMANDS = [
    Command(("/au", "/audio"), distort, "жмых голосового сообщения"),
    Command(("/ma", "/music_audio"), song, "перевести песню в голосовое сообщение"),
    Command(("/copy",), copy, "скопировать голосовое сообщение", access=Access.TRUSTED),
    Command(("/sa", "/save_audio"), save, "сохранить голосовое сообщение", access=Access.TRUSTED),
    Command(("/ag", "/aget"), send_saved, "отправить сохранённое голосовое сообщение", access=Access.TRUSTED),
    Command(("/ad", "/adelete"), delete_saved, "удалить сохранённое голосовое сообщение", access=Access.TRUSTED),
    Command(("/alist",), list_saved, "список сохранённых голосовых сообщений", access=Access.TRUSTED),
]
