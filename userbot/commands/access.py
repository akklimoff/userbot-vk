from userbot.context import (ERROR, INVALID, SUCCESS, SUCCESS_NO, TRUSTED_USERS, Access, Command, Context,
                             mention)

BANNED = "banned"
BANNED_PEERS = "banned_peers"
IGNORED = "ignore"
DISABLED = "disabled"


# иначе доверенный обходил бы правило «доверием управляет только владелец», блокируя других доверенных
def protect_trusted(ctx: Context, user: dict) -> None:
    if not ctx.is_owner and user["id"] in ctx.store.get(TRUSTED_USERS, []):
        ctx.fail(f"{INVALID} {mention(user)} — доверенный, это может сделать только владелец.")


def ban(ctx: Context) -> None:
    user = ctx.target("/ban [пользователь]")
    if user["id"] == ctx.owner_id:
        ctx.fail(f"{INVALID} Нельзя заблокировать самого себя!")
    protect_trusted(ctx, user)
    if not ctx.store.add_to(BANNED, user["id"]):
        ctx.fail(f"{INVALID} {mention(user)} уже заблокирован.")
    ctx.answer(f"{SUCCESS} {mention(user)} был заблокирован!")


def unban(ctx: Context) -> None:
    user = ctx.target("/unban [пользователь]")
    if not ctx.store.remove_from(BANNED, user["id"]):
        ctx.fail(f"{INVALID} {mention(user)} не заблокирован.")
    ctx.answer(f"{SUCCESS} {mention(user)} был разблокирован!")


def ban_chat(ctx: Context) -> None:
    if not ctx.store.add_to(BANNED_PEERS, ctx.peer_id):
        ctx.fail(f"{INVALID} Данная беседа уже заблокирована.")
    ctx.answer(f"{SUCCESS} Данная беседа была заблокирована!")


def unban_chat(ctx: Context) -> None:
    if not ctx.store.remove_from(BANNED_PEERS, ctx.peer_id):
        ctx.fail(f"{INVALID} Данная беседа не заблокирована.")
    ctx.answer(f"{SUCCESS} Данная беседа была разблокирована!")


def ignore(ctx: Context) -> None:
    user = ctx.target("/ignore [пользователь]")
    if user["id"] == ctx.owner_id:
        ctx.fail(f"{ERROR} Нельзя игнорировать самого себя!")
    protect_trusted(ctx, user)
    if not ctx.store.add_to(IGNORED, user["id"]):
        ctx.fail(f"{INVALID} {mention(user)} уже игнорируется.")
    ctx.answer(f"{SUCCESS} {mention(user)} теперь будет игнорироваться!")


def unignore(ctx: Context) -> None:
    user = ctx.target("/unignore [пользователь]")
    if not ctx.store.remove_from(IGNORED, user["id"]):
        ctx.fail(f"{INVALID} {mention(user)} не игнорируется.")
    ctx.answer(f"{SUCCESS} {mention(user)} был удалён из списка игнорируемых!")


def disable(ctx: Context) -> None:
    if ctx.store.toggle(DISABLED):
        ctx.flash(f"{SUCCESS_NO} Общедоступные функции были успешно отключены!")
    else:
        ctx.flash(f"{SUCCESS} Общедоступные функции были успешно включены!")


def trust(ctx: Context) -> None:
    user = ctx.target("/trust [пользователь]")
    if user["id"] == ctx.owner_id:
        ctx.fail(f"{INVALID} Владельцу и так доступны все команды.")
    if not ctx.store.add_to(TRUSTED_USERS, user["id"]):
        ctx.fail(f"{INVALID} {mention(user)} уже доверенный.")
    ctx.answer(f"{SUCCESS} {mention(user)} теперь доверенный: может пользоваться командами владельца.")


def untrust(ctx: Context) -> None:
    user = ctx.target("/untrust [пользователь]")
    if not ctx.store.remove_from(TRUSTED_USERS, user["id"]):
        ctx.fail(f"{INVALID} {mention(user)} не доверенный.")
    ctx.answer(f"{SUCCESS_NO} {mention(user)} больше не доверенный.")


def list_trusted(ctx: Context) -> None:
    ids = ctx.store.get(TRUSTED_USERS, [])
    if not ids:
        ctx.fail(f"{INVALID} Доверенных нет.")
    users = {u["id"]: u for u in ctx.vk.users(ids)}
    names = [mention(users[user_id]) if user_id in users else f"id{user_id}" for user_id in ids]
    ctx.answer("🤝 Доверенные: " + ", ".join(names))


COMMANDS = [
    Command(("/ban",), ban, "заблокировать доступ к боту пользователю", access=Access.TRUSTED),
    Command(("/ban_chat",), ban_chat, "заблокировать чат (бот не будет в нем работать)", access=Access.TRUSTED),
    Command(("/unban",), unban, "разблокировать пользователя", access=Access.TRUSTED),
    Command(("/unban_chat",), unban_chat, "разблокировать чат", access=Access.TRUSTED),
    Command(("/ignore",), ignore, "добавить пользователя в игнор (его сообщения будут удаляться для вас)",
            access=Access.TRUSTED),
    Command(("/unignore",), unignore, "удалить пользователя из игнора", access=Access.TRUSTED),
    Command(("/disable",), disable, "отключить или включить бота для общедоступного использования",
            access=Access.TRUSTED),
    Command(("/trust",), trust, "сделать пользователя доверенным: ему доступны команды владельца",
            access=Access.OWNER),
    Command(("/untrust",), untrust, "убрать пользователя из доверенных", access=Access.OWNER),
    Command(("/trusted",), list_trusted, "список доверенных", access=Access.OWNER),
]
