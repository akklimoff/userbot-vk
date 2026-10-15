from userbot.context import ERROR, INVALID, SUCCESS, SUCCESS_NO, Command, Context, mention

BANNED = "banned"
BANNED_PEERS = "banned_peers"
IGNORED = "ignore"
DISABLED = "disabled"


def ban(ctx: Context) -> None:
    user = ctx.target("/ban [пользователь]")
    if user["id"] == ctx.owner_id:
        ctx.fail(f"{INVALID} Нельзя заблокировать самого себя!")
    if not ctx.store.add_to(BANNED, user["id"]):
        ctx.fail(f"{INVALID} {mention(user)} уже заблокирован.")
    ctx.edit(f"{SUCCESS} {mention(user)} был заблокирован!")


def unban(ctx: Context) -> None:
    user = ctx.target("/unban [пользователь]")
    if not ctx.store.remove_from(BANNED, user["id"]):
        ctx.fail(f"{INVALID} {mention(user)} не заблокирован.")
    ctx.edit(f"{SUCCESS} {mention(user)} был разблокирован!")


def ban_chat(ctx: Context) -> None:
    if not ctx.store.add_to(BANNED_PEERS, ctx.peer_id):
        ctx.fail(f"{INVALID} Данная беседа уже заблокирована.")
    ctx.edit(f"{SUCCESS} Данная беседа была заблокирована!")


def unban_chat(ctx: Context) -> None:
    if not ctx.store.remove_from(BANNED_PEERS, ctx.peer_id):
        ctx.fail(f"{INVALID} Данная беседа не заблокирована.")
    ctx.edit(f"{SUCCESS} Данная беседа была разблокирована!")


def ignore(ctx: Context) -> None:
    user = ctx.target("/ignore [пользователь]")
    if user["id"] == ctx.owner_id:
        ctx.fail(f"{ERROR} Нельзя игнорировать самого себя!")
    if not ctx.store.add_to(IGNORED, user["id"]):
        ctx.fail(f"{INVALID} {mention(user)} уже игнорируется.")
    ctx.edit(f"{SUCCESS} {mention(user)} теперь будет игнорироваться!")


def unignore(ctx: Context) -> None:
    user = ctx.target("/unignore [пользователь]")
    if not ctx.store.remove_from(IGNORED, user["id"]):
        ctx.fail(f"{INVALID} {mention(user)} не игнорируется.")
    ctx.edit(f"{SUCCESS} {mention(user)} был удалён из списка игнорируемых!")


def disable(ctx: Context) -> None:
    if ctx.store.toggle(DISABLED):
        ctx.flash(f"{SUCCESS_NO} Общедоступные функции были успешно отключены!")
    else:
        ctx.flash(f"{SUCCESS} Общедоступные функции были успешно включены!")


COMMANDS = [
    Command(("/ban",), ban, "заблокировать доступ к боту пользователю", owner_only=True),
    Command(("/ban_chat",), ban_chat, "заблокировать чат (бот не будет в нем работать)", owner_only=True),
    Command(("/unban",), unban, "разблокировать пользователя", owner_only=True),
    Command(("/unban_chat",), unban_chat, "разблокировать чат", owner_only=True),
    Command(("/ignore",), ignore, "добавить пользователя в игнор (его сообщения будут удаляться для вас)",
            owner_only=True),
    Command(("/unignore",), unignore, "удалить пользователя из игнора", owner_only=True),
    Command(("/disable",), disable, "отключить или включить бота для общедоступного использования",
            owner_only=True),
]
