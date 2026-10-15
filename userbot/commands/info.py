from userbot.context import SUCCESS, Access, Command, Context


def user_id(ctx: Context) -> None:
    user = ctx.target("/uid [пользователь]")
    ctx.answer(f"{SUCCESS} ID пользователя: {user['id']}")


def command_lines(commands: list[Command]) -> str:
    return "\n".join(f"{', '.join(c.names)} -- {c.description}" for c in commands)


def section(commands: list[Command], access: Access) -> str:
    return command_lines([c for c in commands if c.access == access])


def help_text(commands: list[Command], access: Access) -> str:
    text = "🚑 Доступные команды >>\n" + section(commands, Access.PUBLIC)
    if access >= Access.TRUSTED:
        text += "\n\n❗️ Команды владельца и доверенных:\n" + section(commands, Access.TRUSTED)
        text += "\n\n👑 Только владелец:\n" + section(commands, Access.OWNER)
    return text


def show_help(ctx: Context) -> None:
    ctx.send(help_text(list(ctx.commands), ctx.access))


COMMANDS = [
    Command(("/uid", "/userid"), user_id, "получить ID пользователя"),
    Command(("/911", "/112", "/help"), show_help, "список команд"),
]
