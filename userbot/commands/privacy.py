from functools import partial

from userbot.context import ERROR, INVALID, SUCCESS, SUCCESS_NO, Access, Command, Context, mention

AUDIOS = ("audios", "аудиозаписям")
SAVED_PHOTOS = ("photos_saved", "сохрам")


def change_access(ctx: Context, section: tuple[str, str], opening: bool) -> None:
    key, label = section
    reply = ctx.reply_message
    if reply is None:
        ctx.fail(f"{ERROR} Необходимо ответить на сообщение пользователя.")
    user = ctx.vk.user(reply["from_id"], "is_friend")
    if user is None:
        ctx.fail(f"{ERROR} Не удалось найти пользователя.")
    if user["id"] == ctx.owner_id:
        ctx.fail(f"{INVALID} Данную команду нельзя использовать на самого себя!")
    if opening and not user.get("is_friend"):
        ctx.fail(f"{INVALID} {mention(user)} не находится у Вас в друзьях!")
    value = ctx.vk.privacy_value(key)
    owners = value.get("owners") or {}
    if value.get("category") not in (None, "only_me") or owners.get("excluded") or value.get("lists"):
        ctx.fail(f"{INVALID} Доступ к {label} настроен сложнее, чем «только выбранные люди», — "
                 f"измените его в настройках VK, чтобы не потерять.")
    allowed = list(owners.get("allowed") or [])
    if opening and user["id"] in allowed:
        ctx.fail(f"{INVALID} У пользователя {mention(user)} уже есть доступ к {label}!")
    if not opening and user["id"] not in allowed:
        ctx.fail(f"{INVALID} У пользователя {mention(user)} нет доступа к {label}!")
    if opening:
        ctx.vk.set_privacy_allowed(key, [*allowed, user["id"]])
        ctx.answer(f"{SUCCESS} Пользователю {mention(user)} открыт доступ к {label}!")
    else:
        ctx.vk.set_privacy_allowed(key, [i for i in allowed if i != user["id"]])
        ctx.answer(f"{SUCCESS_NO} Пользователю {mention(user)} закрыт доступ к {label}!")


COMMANDS = [
    Command(("+s", "+saves", "+с", "+сохры"), partial(change_access, section=SAVED_PHOTOS, opening=True),
            "открыть сохры пользователю (ответом)", access=Access.TRUSTED),
    Command(("-s", "-saves", "-с", "-сохры"), partial(change_access, section=SAVED_PHOTOS, opening=False),
            "закрыть сохры пользователю (ответом)", access=Access.TRUSTED),
    Command(("+a", "+audios", "+м", "+музыка"), partial(change_access, section=AUDIOS, opening=True),
            "открыть аудиозаписи пользователю (ответом)", access=Access.TRUSTED),
    Command(("-a", "-audios", "-м", "-музыка"), partial(change_access, section=AUDIOS, opening=False),
            "закрыть аудиозаписи пользователю (ответом)", access=Access.TRUSTED),
]
