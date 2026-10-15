import re

from userbot.context import ERROR, INVALID, SUCCESS, Access, Command, Context

ASSOC = "assoc"
# только слово с необязательным префиксом: эмодзи-ассоциация совпала бы с началом ответов бота и заглушила их
ALIAS = re.compile(r"[/!+\-]?\w+")


def list_assoc(ctx: Context) -> None:
    assocs: dict[str, str] = ctx.store.get(ASSOC, {})
    if not assocs:
        ctx.fail(f"{INVALID} У Вас нет ассоциаций.")
    by_command: dict[str, list[str]] = {}
    for alias, command in assocs.items():
        by_command.setdefault(command, []).append(alias)
    lines = [f"{command}: {', '.join(aliases)}" for command, aliases in by_command.items()]
    ctx.answer("📖 Ассоциации:<br>" + ";<br>".join(lines))


def set_assoc(ctx: Context) -> None:
    args = ctx.args
    if len(args) < 3:
        ctx.fail(f"{INVALID} Правильное использование: /assoc_set [команда] [ассоциация]")
    command, alias = args[1].lower(), args[2].lower()
    names = {name for c in ctx.commands for name in c.names}
    target = next((c for c in ctx.commands if command in c.names), None)
    if target is None:
        ctx.fail(f"{ERROR} Такой команды нет, учтите, что необходимо писать команду полностью.\n"
                 f"👉🏻 Например: /ban")
    if target.access > ctx.access:
        ctx.fail(f"{ERROR} Недостаточно прав, чтобы назначать ассоциации этой команде.")
    if not ALIAS.fullmatch(alias):
        ctx.fail(f"{INVALID} Ассоциация — одно слово из букв и цифр, можно с /, !, + или - в начале.")
    if alias in names:
        ctx.fail(f"{ERROR} `{alias}` уже является командой!")
    if not ctx.store.put_new(ASSOC, alias, command):
        ctx.fail(f"{ERROR} Ассоциация `{alias}` уже существует!")
    ctx.flash(f"{SUCCESS} Создана новая ассоциация для команды {command}: `{alias}`!", seconds=5)


def delete_assoc(ctx: Context) -> None:
    alias = ctx.rest(1).lower()
    if not alias:
        ctx.fail(f"{INVALID} Правильное использование: /assoc_del [ассоциация]")
    if not ctx.store.pop(ASSOC, alias):
        ctx.fail(f"{INVALID} Ассоциации с таким ключом нет!")
    ctx.flash(f"{SUCCESS} Ассоциация `{alias}` была успешно удалена.")


COMMANDS = [
    Command(("/assoc",), list_assoc, "список ассоциаций", access=Access.TRUSTED),
    Command(("/assoc_set",), set_assoc, "добавить ассоциацию", access=Access.TRUSTED),
    Command(("/assoc_del",), delete_assoc, "удалить ассоциацию", access=Access.TRUSTED),
]
