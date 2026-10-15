from userbot.context import Access, Command, Context

SECTIONS = (
    (Access.PUBLIC, "💖 Для всех"),
    (Access.TRUSTED, "👑 Владелец и доверенные"),
    (Access.OWNER, "👸 Только владелец"),
)
FOOTER = "💅 Человека можно указать ответом на его сообщение, ссылкой, @упоминанием или ID"


def user_id(ctx: Context) -> None:
    user = ctx.target("/uid @ник")
    ctx.answer(f"🪪 ID пользователя: {user['id']}")


def command_line(command: Command) -> str:
    usage = f" {command.usage}" if command.usage else ""
    return f"{command.icon} {', '.join(command.names)}{usage} — {command.description}"


def help_text(commands: list[Command], access: Access) -> str:
    shown = Access.OWNER if access >= Access.TRUSTED else Access.PUBLIC
    blocks = ["🌸 Команды бота 🌸"]
    for level, title in SECTIONS:
        if level <= shown:
            blocks.append("\n".join([title, *(command_line(c) for c in commands if c.access == level)]))
    blocks.append(FOOTER)
    return "\n\n".join(blocks)


def show_help(ctx: Context) -> None:
    ctx.send(help_text(list(ctx.commands), ctx.access))


COMMANDS = [
    Command(("/uid", "/userid"), user_id, "узнать ID человека", icon="🪪", usage="[кто]"),
    Command(("/911", "/112", "/help"), show_help, "этот список", icon="🧚‍♀️"),
]
