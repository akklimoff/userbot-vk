from userbot.context import (INVALID, SUCCESS, SUCCESS_NO, TRUSTED_USERS, Access, Command, Context,
                             full_name)

IGNORED = "ignore"
DISABLED = "disabled"


# иначе доверенный обходил бы правило «доверием управляет только владелец», игнорируя других доверенных
def protect_trusted(ctx: Context, user: dict) -> None:
    if not ctx.is_owner and user["id"] in ctx.store.get(TRUSTED_USERS, []):
        ctx.fail(f"{INVALID} {full_name(user)} — доверенный, тут решает только владелец")


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
    Command(("/игнор", "/ignore"), ignore, "сообщения человека будут исчезать у владельца",
            Access.TRUSTED, "🙈", "[кто]"),
    Command(("/разигнор", "/unignore"), unignore, "убрать из игнора", Access.TRUSTED, "🙉", "[кто]"),
    Command(("/выкл", "/пауза", "/disable"), disable, "выключить или включить команды для всех", Access.TRUSTED, "💤"),
    Command(("/довер", "/trust"), trust, "сделать доверенным: ему доступны команды владельца",
            Access.OWNER, "💍", "[кто]"),
    Command(("/недовер", "/untrust"), untrust, "убрать из доверенных", Access.OWNER, "💔", "[кто]"),
    Command(("/доверенные", "/trusted"), list_trusted, "список доверенных", Access.OWNER, "👯‍♀️"),
]
