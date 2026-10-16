from functools import partial

from userbot.automation import AUTO_ACCEPT, AUTO_CLEAN, AUTO_UNFOLLOW, ETERNAL_ONLINE
from userbot.context import SUCCESS, SUCCESS_NO, Access, Command, Context


def switch(ctx: Context, key: str, title: str) -> None:
    if ctx.store.toggle(key):
        ctx.answer(f"{SUCCESS} {title}: включено")
    else:
        ctx.answer(f"{SUCCESS_NO} {title}: выключено")


COMMANDS = [
    Command(("/автоприём", "/автоприем", "/autoaccept"), partial(switch, key=AUTO_ACCEPT, title="Автоприём заявок"),
            "вкл/выкл: принимать входящие заявки в друзья", Access.TRUSTED, "🤝"),
    Command(("/автоотписка", "/autounfollow"), partial(switch, key=AUTO_UNFOLLOW, title="Автоотписка"),
            "вкл/выкл: отменять исходящие заявки в друзья", Access.TRUSTED, "🚪"),
    Command(("/автоочистка", "/autoclean"), partial(switch, key=AUTO_CLEAN, title="Автоочистка друзей"),
            "вкл/выкл: удалять из друзей удалённых и заблокированных", Access.TRUSTED, "🧹"),
    Command(("/онлайн", "/вечныйонлайн", "/online"), partial(switch, key=ETERNAL_ONLINE, title="Вечный онлайн"),
            "вкл/выкл: держать онлайн круглые сутки", Access.TRUSTED, "🟢"),
]
