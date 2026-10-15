from functools import partial

from userbot.context import ERROR, INVALID, SUCCESS, SUCCESS_NO, Access, Command, Context, full_name

AUDIOS = ("audios", "аудиозаписям")
SAVED_PHOTOS = ("photos_saved", "сохрам")


def change_access(ctx: Context, section: tuple[str, str], opening: bool) -> None:
    key, label = section
    reply = ctx.reply_message
    if reply is None:
        ctx.fail(f"{ERROR} Нужно ответить на сообщение человека")
    user = ctx.vk.user(reply["from_id"], "is_friend")
    if user is None:
        ctx.fail(f"{ERROR} Не получилось найти этого человека")
    if user["id"] == ctx.owner_id:
        ctx.fail(f"{INVALID} На себя эта команда не действует")
    if opening and not user.get("is_friend"):
        ctx.fail(f"{INVALID} {full_name(user)} не в друзьях")
    value = ctx.vk.privacy_value(key)
    owners = value.get("owners") or {}
    if value.get("category") not in (None, "only_me") or owners.get("excluded") or value.get("lists"):
        ctx.fail(f"{INVALID} Доступ к {label} настроен сложнее, чем «только выбранные люди», — "
                 f"поменяйте его в настройках VK, чтобы ничего не потерять")
    allowed = list(owners.get("allowed") or [])
    if opening and user["id"] in allowed:
        ctx.fail(f"{INVALID} У {full_name(user)} уже есть доступ к {label}")
    if not opening and user["id"] not in allowed:
        ctx.fail(f"{INVALID} У {full_name(user)} и так нет доступа к {label}")
    if opening:
        ctx.vk.set_privacy_allowed(key, [*allowed, user["id"]])
        ctx.done(f"{SUCCESS} {full_name(user)}: доступ к {label} открыт")
    else:
        ctx.vk.set_privacy_allowed(key, [i for i in allowed if i != user["id"]])
        ctx.done(f"{SUCCESS_NO} {full_name(user)}: доступ к {label} закрыт")


COMMANDS = [
    Command(("+s", "+saves", "+с", "+сохры"), partial(change_access, section=SAVED_PHOTOS, opening=True),
            "открыть сохры (ответом)", Access.TRUSTED, "📸"),
    Command(("-s", "-saves", "-с", "-сохры"), partial(change_access, section=SAVED_PHOTOS, opening=False),
            "закрыть сохры (ответом)", Access.TRUSTED, "🫣"),
    Command(("+a", "+audios", "+м", "+музыка"), partial(change_access, section=AUDIOS, opening=True),
            "открыть музыку (ответом)", Access.TRUSTED, "🎧"),
    Command(("-a", "-audios", "-м", "-музыка"), partial(change_access, section=AUDIOS, opening=False),
            "закрыть музыку (ответом)", Access.TRUSTED, "🔇"),
]
