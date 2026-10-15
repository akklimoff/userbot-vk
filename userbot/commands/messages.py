import logging
import random
import re
import time

from userbot.attachments import attachment_id, first_attachment, reattach_ids
from userbot.context import BLANK, ERROR, INVALID, Command, Context

log = logging.getLogger("userbot-vk")

DEFAULT_TTL = 86400
ALLOWED_TTL = (15, 60, 300, 900, 3600, 18000, 86400)
TTL_UNITS = {"s": 1, "с": 1, "m": 60, "м": 60, "h": 3600, "ч": 3600, "d": 86400, "д": 86400}
# VK удаляет у всех только сообщения моложе суток
DELETE_FOR_ALL_WINDOW = 86400
MAX_DELETE = 200
MAX_REPEAT = 20
COMMAND_LIKE = f"{INVALID} Такой текст бот принял бы за команду, поэтому не отправляю."


def parse_ttl(word: str) -> int | None:
    match = re.fullmatch(r"(\d+)([a-zа-я])", word.lower())
    if match is None or match.group(2) not in TTL_UNITS:
        return None
    return int(match.group(1)) * TTL_UNITS[match.group(2)]


def delete_messages(ctx: Context) -> None:
    args = ctx.args
    if len(args) < 2 or not args[1].isdecimal() or not 1 <= int(args[1]) <= MAX_DELETE:
        ctx.fail(f"{INVALID} Необходимо ввести количество сообщений от 1 до {MAX_DELETE}.")
    count, wipe = int(args[1]), len(args) >= 3
    ctx.delete()
    now = time.time()
    ids = []
    for message in ctx.vk.history(ctx.peer_id, ctx.message["id"]):
        if len(ids) >= count or now - message["date"] > DELETE_FOR_ALL_WINDOW:
            break
        if message["from_id"] != ctx.owner_id:
            continue
        if wipe:
            try:
                ctx.vk.edit(ctx.peer_id, message["id"], BLANK)
            except Exception:
                log.warning("Не удалось стереть сообщение %s в %s", message["id"], ctx.peer_id)
            ctx.sleep(random.uniform(0.25, 0.75))
        ids.append(message["id"])
    if ids:
        ctx.vk.delete(ids, ctx.for_all)


def own_media(ctx: Context) -> dict | None:
    reply = ctx.reply_message
    attachment = first_attachment(reply) if reply and reply["from_id"] == ctx.owner_id else None
    return attachment if attachment and attachment["type"] in ("audio_message", "sticker") else None


def resend_own_media(ctx: Context, attachment: dict, ttl: int) -> None:
    ctx.vk.delete([ctx.reply_message["id"]], ctx.for_all)
    if attachment["type"] == "sticker":
        ctx.post(sticker_id=attachment["sticker"]["sticker_id"], expire_ttl=ttl)
    else:
        ctx.post(attachment=attachment_id("audio_message", attachment["audio_message"]), expire_ttl=ttl)


def invisible(ctx: Context) -> None:
    args = ctx.args
    ttl = parse_ttl(args[1]) if len(args) > 1 else None
    if ttl is not None and ttl not in ALLOWED_TTL:
        ctx.fail(f"{ERROR} Неверное время исчезающего сообщения, возможные варианты: 15 сек, 1 минута, 5 минут, "
                 f"15 минут, 1 час, 5 часов, 1 день.", seconds=5)
    text = ctx.rest(2 if ttl else 1)
    attachments = reattach_ids(ctx.message)
    forward = ",".join(str(m["id"]) for m in ctx.message.get("fwd_messages") or [] if m.get("id"))
    media = own_media(ctx)
    if not (text or attachments or forward or media):
        ctx.fail(f"{ERROR} Необходимо написать сообщение или ответить на стикер / голосовое сообщение.", seconds=1)
    if ctx.is_command_like(text):
        ctx.fail(COMMAND_LIKE)
    ttl = ttl or DEFAULT_TTL
    ctx.edit(BLANK)
    ctx.delete()
    if not text and media:
        resend_own_media(ctx, media, ttl)
        return
    reply = ctx.reply_message
    ctx.post(text or None, attachment=attachments or None, forward=forward or None, expire_ttl=ttl,
             reply_to=reply["id"] if reply else None)


def repeat(ctx: Context) -> None:
    args = ctx.args
    if len(args) < 3 or not args[1].isdecimal() or not 1 <= int(args[1]) <= MAX_REPEAT:
        ctx.fail(f"{ERROR} Использование: /repeat [количество 1-{MAX_REPEAT}] [сообщение]", seconds=1)
    text = ctx.rest(2)
    if ctx.is_command_like(text):
        ctx.fail(COMMAND_LIKE)
    ctx.delete()
    for _ in range(int(args[1])):
        try:
            if not ctx.send(text, reply=False):
                return
        except Exception:
            log.warning("Повтор в %s прерван ошибкой VK", ctx.peer_id)
            return
        ctx.sleep(random.uniform(0, 2.5))


COMMANDS = [
    Command(("/del",), delete_messages, "удалить свои сообщения: /del [количество] [любое слово — сначала стереть]",
            owner_only=True),
    Command(("/i", "/и"), invisible, "отправить исчезающее сообщение: /i [15s|1m|5m|15m|1h|5h|1d] [текст]",
            owner_only=True),
    Command(("/repeat",), repeat, "повторить сообщение: /repeat [количество] [текст]", owner_only=True),
]
