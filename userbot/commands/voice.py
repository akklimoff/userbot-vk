import logging
import re
import tempfile

from userbot import media
from userbot.attachments import circle_id, is_circle_id, voice_url
from userbot.context import ERROR, INVALID, SUCCESS, Access, Command, Context, full_name, user_ref
from userbot.library import Shelf

SAVED = "saved_audio"
NEED_VOICE_OR_CIRCLE = f"{ERROR} Нужно ответить на голосовое или кружочек"

# упоминание «[id1|Имя Фамилия]» содержит пробел, по словам его не разобрать
MENTION = re.compile(r"\[id(\d+)\|[^\]]*\]\s*(.*)", re.DOTALL)

log = logging.getLogger("userbot-vk")


# без ответа голосовое или кружочек можно переслать вместе с командой
def source(ctx: Context) -> dict:
    return ctx.reply_message or ctx.message


def reupload_voice(ctx: Context, url: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        return ctx.vk.upload_voice(media.download(url, tmp, ".ogg"), ctx.peer_id)


def require_voice_or_circle(ctx: Context) -> None:
    if voice_url(source(ctx)) is None and circle_id(source(ctx)) is None:
        ctx.fail(NEED_VOICE_OR_CIRCLE)


# VK не даёт загрузить кружочек, поэтому его копия — ссылка на оригинал, а голосовое загружается заново
def copy_of_reply(ctx: Context) -> tuple[str, bool]:
    url = voice_url(source(ctx))
    if url is not None:
        return reupload_voice(ctx, url), False
    circle = circle_id(source(ctx))
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
    url = voice_url(source(ctx))
    if url is None:
        save_circle(ctx, key)
    else:
        save_voice(ctx, key, url)
    what = "Кружочек сохранён" if url is None else "Голосовое сохранено"
    text = f"{SUCCESS} {what} как «{key}» — отправить: /гс {key}"
    if named:
        ctx.done(text)
    else:
        ctx.answer(text)


def save_circle(ctx: Context, key: str) -> None:
    if not ctx.store.put_new(SAVED, key, circle_id(source(ctx))):
        ctx.fail(taken(key))


def save_voice(ctx: Context, key: str, url: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = media.download(url, tmp, ".ogg")
        if not ctx.store.put_new(SAVED, key, ctx.vk.upload_voice(path, ctx.peer_id)):
            ctx.fail(taken(key))
        if ctx.library is not None:
            ctx.library.keep(key, path)


def split_account(text: str) -> tuple[str, str]:
    mention = MENTION.fullmatch(text)
    if mention:
        return mention.group(1), mention.group(2).strip()
    ref, _, rest = text.partition(" ")
    return ref, rest.strip()


# аккаунт, подключившийся позже, дописывает себя в общий словарь из своего потока — читаем его копию
def other_shelves(ctx: Context) -> dict[int, Shelf]:
    return {account: shelf for account, shelf in dict(ctx.shelves).items() if account != ctx.owner_id}


def account_by(ctx: Context, ref: str) -> int | None:
    accounts = other_shelves(ctx)
    ref = user_ref(ref)
    number = ref.removeprefix("id")
    if number.isdecimal():
        return int(number) if int(number) in accounts else None
    if not accounts:
        return None
    named = [user["id"] for user in ctx.vk.users(list(accounts))
             if ref.lower() in (user["first_name"].lower(), user["last_name"].lower())]
    if len(named) > 1:
        ctx.fail(f"{INVALID} «{ref}» — это несколько аккаунтов, укажите id: {', '.join(map(str, named))}")
    if named:
        return named[0]
    tagged = ctx.vk.user(ref)
    return tagged["id"] if tagged and tagged["id"] in accounts else None


# чужое голосовое — документ другого аккаунта, VK его не отправит: звук берётся из файла и загружается заново
def foreign_saved(ctx: Context, key: str) -> tuple[str, str, str | None] | None:
    ref, name = split_account(key)
    account = account_by(ctx, ref) if name else None
    if account is None:
        return None
    shelf = other_shelves(ctx)[account]
    attachment = shelf.store.get(SAVED, {}).get(name)
    if attachment is None:
        ctx.fail(f"{INVALID} «{name}» у {account} не сохранено — список в /гсы {account}")
    if is_circle_id(attachment):
        return name, attachment, None
    path = shelf.library.path(name)
    if path is None:
        ctx.fail(f"{ERROR} У голосового «{name}» нет файла — его может отправить только сам аккаунт {account}")
    return name, attachment, path


def send_saved(ctx: Context) -> None:
    key = ctx.rest(1)
    if not key:
        ctx.fail(f"{INVALID} Так: /гс название")
    attachment, path = ctx.store.get(SAVED, {}).get(key), None
    own = attachment is not None
    if not own:
        foreign = foreign_saved(ctx, key) if ctx.is_admin else None
        if foreign is None:
            ctx.fail(missing(key))
        key, attachment, path = foreign
    ctx.hide()
    try:
        if path is not None:
            attachment = ctx.vk.upload_voice(path, ctx.peer_id)
        ctx.result(attachment=attachment)
    except Exception:
        log.warning("Сохранённое «%s» не отправилось в %s", key, ctx.peer_id, exc_info=True)
        what, ending = ("Кружочек", "ся") if is_circle_id(attachment) else ("Голосовое", "ось")
        hint = f" Если так снова и снова — оригинал, скорее всего, удалили, убрать: /угс {key}" if own else ""
        ctx.report(f"{ERROR} {what} «{key}» не отправил{ending}.{hint}")


def delete_saved(ctx: Context) -> None:
    key = ctx.rest(1)
    if not key:
        ctx.fail(f"{INVALID} Так: /угс название")
    if not ctx.store.pop(SAVED, key):
        ctx.fail(missing(key))
    if ctx.library is not None:
        ctx.library.forget(key)
    ctx.done(f"{SUCCESS} «{key}» удалено из сохранённых")


def saved_lines(saved: dict[str, str]) -> list[str]:
    return [f"{'📹' if is_circle_id(attachment) else '🎀'} {key}" for key, attachment in saved.items()]


def account_lines(ctx: Context) -> list[str]:
    counts = {account: len(shelf.store.get(SAVED, {})) for account, shelf in other_shelves(ctx).items()}
    saved = [account for account, count in counts.items() if count]
    names = {user["id"]: full_name(user) for user in ctx.vk.users(saved)} if saved else {}
    return [f"{names.get(account, 'аккаунт')} — {account} ({counts[account]})" for account in saved]


def list_of_account(ctx: Context, ref: str) -> None:
    account = account_by(ctx, split_account(ref)[0])
    if account is None:
        ctx.fail(f"{INVALID} Не знаю такого аккаунта — список в /гсы")
    saved = other_shelves(ctx)[account].store.get(SAVED, {})
    if not saved:
        ctx.fail(f"{INVALID} У {account} пока ничего не сохранено")
    ctx.answer("\n".join([f"📒 Сохранённое у {account} — отправить: /гс {account} название", "", *saved_lines(saved)]))


def list_saved(ctx: Context) -> None:
    if ctx.is_admin and ctx.rest(1):
        list_of_account(ctx, ctx.rest(1))
        return
    saved: dict[str, str] = ctx.store.get(SAVED, {})
    accounts = account_lines(ctx) if ctx.is_admin else []
    if not saved and not accounts:
        ctx.fail(f"{INVALID} Сохранённых голосовых и кружочков пока нет")
    lines = ["📒 Сохранённые голосовые и кружочки", "", *(saved_lines(saved) or ["пока пусто"])]
    if accounts:
        lines += ["", "👥 Другие аккаунты — список: /гсы id, отправить: /гс id название", "", *accounts]
    ctx.answer("\n".join(lines))


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
