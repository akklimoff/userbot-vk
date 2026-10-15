from userbot.context import SUCCESS, Command, Context

CREDITS = "🐺 Разработчики: [id171812976|тык], [id163653953|тык] [id413636725|тык]"
REPOSITORY = "❔ Полный список команд и обновления: https://github.com/akklimoff/userbot-vk"


def user_id(ctx: Context) -> None:
    user = ctx.target("/uid [пользователь]")
    ctx.answer(f"{SUCCESS} ID пользователя: {user['id']}")


def command_lines(commands: list[Command]) -> str:
    return "\n".join(f"{', '.join(c.names)} -- {c.description}" for c in commands)


def help_text(commands: list[Command], for_owner: bool) -> str:
    text = "🚑 Доступные команды >>\n" + command_lines([c for c in commands if not c.owner_only])
    if for_owner:
        text += "\n\n❗️ Команды владельца:\n" + command_lines([c for c in commands if c.owner_only])
        text += f"\n\n{CREDITS}\n{REPOSITORY}"
    else:
        text += f"\n\n{CREDITS}"
    return text


def show_help(ctx: Context) -> None:
    ctx.send(help_text(list(ctx.commands), ctx.is_owner))


COMMANDS = [
    Command(("/uid", "/userid"), user_id, "получить ID пользователя"),
    Command(("/911", "/112", "/help"), show_help, "список команд"),
]
