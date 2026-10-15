from userbot.context import (INVALID, SUCCESS, SUCCESS_NO, TRUSTED_USERS, Access, Command, Context,
                             full_name)

BANNED = "banned"
BANNED_PEERS = "banned_peers"
IGNORED = "ignore"
DISABLED = "disabled"


# иначе доверенный обходил бы правило «доверием управляет только владелец», блокируя других доверенных
def protect_trusted(ctx: Context, user: dict) -> None:
    if not ctx.is_owner and user["id"] in ctx.store.get(TRUSTED_USERS, []):
        ctx.fail(f"{INVALID} {full_name(user)} — доверенный, тут решает только владелец")


def ban(ctx: Context) -> None:
    user = ctx.target("/ban @ник")
    if user["id"] == ctx.owner_id:
        ctx.fail(f"{INVALID} Себя заблокировать нельзя")
    protect_trusted(ctx, user)
    if not ctx.store.add_to(BANNED, user["id"]):
        ctx.fail(f"{INVALID} {full_name(user)} уже заблокирован")
    ctx.done(f"{SUCCESS} {full_name(user)} заблокирован — бот больше не отвечает ему")


def unban(ctx: Context) -> None:
    user = ctx.target("/unban @ник")
    if not ctx.store.remove_from(BANNED, user["id"]):
        ctx.fail(f"{INVALID} {full_name(user)} и так не заблокирован")
    ctx.done(f"{SUCCESS} {full_name(user)} разблокирован")


def ban_chat(ctx: Context) -> None:
    if not ctx.store.add_to(BANNED_PEERS, ctx.peer_id):
        ctx.fail(f"{INVALID} Беседа уже заблокирована")
    ctx.done(f"{SUCCESS} Беседа заблокирована — здесь бот слушает только владельца и доверенных")


def unban_chat(ctx: Context) -> None:
    if not ctx.store.remove_from(BANNED_PEERS, ctx.peer_id):
        ctx.fail(f"{INVALID} Беседа и так не заблокирована")
    ctx.done(f"{SUCCESS} Беседа разблокирована")


def ignore(ctx: Context) -> None:
    user = ctx.target("/ignore @ник")
    if user["id"] == ctx.owner_id:
        ctx.fail(f"{INVALID} Себя игнорировать нельзя")
    protect_trusted(ctx, user)
    if not ctx.store.add_to(IGNORED, user["id"]):
        ctx.fail(f"{INVALID} {full_name(user)} уже в игноре")
    ctx.done(f"{SUCCESS} {full_name(user)} в игноре — его сообщения будут исчезать")


def unignore(ctx: Context) -> None:
    user = ctx.target("/unignore @ник")
    if not ctx.store.remove_from(IGNORED, user["id"]):
        ctx.fail(f"{INVALID} {full_name(user)} и так не в игноре")
    ctx.done(f"{SUCCESS} {full_name(user)} больше не в игноре")


def disable(ctx: Context) -> None:
    if ctx.store.toggle(DISABLED):
        ctx.answer(f"{SUCCESS_NO} Команды для всех выключены — бот слушает только своих")
    else:
        ctx.answer(f"{SUCCESS} Команды для всех снова включены")


def trust(ctx: Context) -> None:
    user = ctx.target("/trust @ник")
    if user["id"] == ctx.owner_id:
        ctx.fail(f"{INVALID} Владельцу и так можно всё")
    if not ctx.store.add_to(TRUSTED_USERS, user["id"]):
        ctx.fail(f"{INVALID} {full_name(user)} уже доверенный")
    ctx.done(f"💍 {full_name(user)} теперь доверенный — может пользоваться командами владельца")


def untrust(ctx: Context) -> None:
    user = ctx.target("/untrust @ник")
    if not ctx.store.remove_from(TRUSTED_USERS, user["id"]):
        ctx.fail(f"{INVALID} {full_name(user)} и так не доверенный")
    ctx.done(f"{SUCCESS_NO} {full_name(user)} больше не доверенный")


def list_trusted(ctx: Context) -> None:
    ids = ctx.store.get(TRUSTED_USERS, [])
    if not ids:
        ctx.fail(f"{INVALID} Доверенных пока нет")
    users = {u["id"]: u for u in ctx.vk.users(ids)}
    names = [full_name(users[user_id]) if user_id in users else f"id{user_id}" for user_id in ids]
    ctx.answer("\n".join(["👯‍♀️ Доверенные", "", *(f"💍 {name}" for name in names)]))


COMMANDS = [
    Command(("/блок", "/ban"), ban, "бот перестанет отвечать человеку", Access.TRUSTED, "🚫", "[кто]"),
    Command(("/разблок", "/unban"), unban, "снять блокировку", Access.TRUSTED, "🌸", "[кто]"),
    Command(("/блокчат", "/ban_chat"), ban_chat, "в этой беседе бот слушает только владельца и доверенных",
            Access.TRUSTED, "🔒"),
    Command(("/разблокчат", "/unban_chat"), unban_chat, "вернуть бота в беседу для всех", Access.TRUSTED, "🔓"),
    Command(("/игнор", "/ignore"), ignore, "сообщения человека будут исчезать у владельца",
            Access.TRUSTED, "🙈", "[кто]"),
    Command(("/разигнор", "/unignore"), unignore, "убрать из игнора", Access.TRUSTED, "🙉", "[кто]"),
    Command(("/выкл", "/пауза", "/disable"), disable, "выключить или включить команды для всех", Access.TRUSTED, "💤"),
    Command(("/довер", "/trust"), trust, "сделать доверенным: ему доступны команды владельца",
            Access.OWNER, "💍", "[кто]"),
    Command(("/недовер", "/untrust"), untrust, "убрать из доверенных", Access.OWNER, "💔", "[кто]"),
    Command(("/доверенные", "/trusted"), list_trusted, "список доверенных", Access.OWNER, "👯‍♀️"),
]
