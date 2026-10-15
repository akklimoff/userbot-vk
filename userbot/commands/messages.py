import logging
import random
import re
import time

from userbot.attachments import attachment_id, first_attachment, reattach_ids
from userbot.context import BLANK, ERROR, INVALID, Access, Command, Context

log = logging.getLogger("userbot-vk")

DEFAULT_TTL = 86400
ALLOWED_TTL = (15, 60, 300, 900, 3600, 18000, 86400)
TTL_UNITS = {"s": 1, "с": 1, "m": 60, "м": 60, "h": 3600, "ч": 3600, "d": 86400, "д": 86400}
# VK удаляет у всех только сообщения моложе суток
DELETE_FOR_ALL_WINDOW = 86400
MAX_DELETE = 200
MAX_REPEAT = 20
COMMAND_LIKE = f"{INVALID} Такой текст бот принял бы за команду, поэтому не отправляю"


def parse_ttl(word: str) -> int | None:
    match = re.fullmatch(r"(\d+)([a-zа-я])", word.lower())
    if match is None or match.group(2) not in TTL_UNITS:
        return None
    return int(match.group(1)) * TTL_UNITS[match.group(2)]


def delete_messages(ctx: Context) -> None:
    args = ctx.args
    if len(args) < 2 or not args[1].isdecimal() or not 1 <= int(args[1]) <= MAX_DELETE:
        ctx.fail(f"{INVALID} Сколько удалить? Так: /del 10 (от 1 до {MAX_DELETE})")
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
        delete_each_on_failure(ctx, ids)


# служебное сообщение в пачке (приглашение, закреп) роняет удаление у всех целиком — тогда удаляем по одному
def delete_each_on_failure(ctx: Context, ids: list[int]) -> None:
    try:
        ctx.vk.delete(ids, ctx.for_all)
        return
    except Exception:
        log.info("Пачку из %d сообщений в %s удалить не вышло, удаляю по одному", len(ids), ctx.peer_id)
    for message_id in ids:
        try:
            ctx.vk.delete([message_id], ctx.for_all)
        except Exception:
            log.warning("Не удалось удалить сообщение %s в %s", message_id, ctx.peer_id)


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
        ctx.fail(f"{ERROR} Такого времени нет — можно 15s, 1m, 5m, 15m, 1h, 5h или 1d")
    text = ctx.rest(2 if ttl else 1)
    attachments = reattach_ids(ctx.message)
    media = own_media(ctx)
    if not (text or attachments or media):
        ctx.fail(f"{ERROR} Нужен текст или ответ на своё голосовое или стикер")
    if ctx.is_command_like(text):
        ctx.fail(COMMAND_LIKE)
    ttl = ttl or DEFAULT_TTL
    ctx.hide()
    if not text and media:
        resend_own_media(ctx, media, ttl)
        return
    reply = ctx.reply_message
    ctx.post(text or None, attachment=attachments or None, expire_ttl=ttl, reply_to=reply["id"] if reply else None)


def repeat(ctx: Context) -> None:
    args = ctx.args
    if len(args) < 3 or not args[1].isdecimal() or not 1 <= int(args[1]) <= MAX_REPEAT:
        ctx.fail(f"{INVALID} Так: /repeat 5 текст (от 1 до {MAX_REPEAT} раз)")
    text = ctx.rest(2)
    if ctx.is_command_like(text):
        ctx.fail(COMMAND_LIKE)
    ctx.delete()
    for _ in range(int(args[1])):
        try:
            if not ctx.post(text):
                return
        except Exception:
            log.warning("Повтор в %s прерван ошибкой VK", ctx.peer_id)
            return
        ctx.sleep(random.uniform(0, 2.5))


COMMANDS = [
    Command(("/del",), delete_messages, "удалить последние сообщения владельца; со словом — сначала стереть текст",
            Access.TRUSTED, "🧹", "[сколько] [слово]"),
    Command(("/i", "/и"), invisible, "исчезающее сообщение", Access.TRUSTED, "🪄", "[15s|1m|5m|15m|1h|5h|1d] [текст]"),
    Command(("/repeat",), repeat, "повторить сообщение", Access.TRUSTED, "💋", "[1-20] [текст]"),
]
