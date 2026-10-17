import logging
import time
from collections.abc import Callable

from userbot.store import Store
from userbot.vk import Throttled

log = logging.getLogger("userbot-vk")

AUTO_ACCEPT = "auto_accept"
AUTO_UNFOLLOW = "auto_unfollow"
AUTO_CLEAN = "auto_clean"
ETERNAL_ONLINE = "eternal_online"

TICK_SECONDS = 5
# account.setOnline держит статус «онлайн» 5 минут
ONLINE_EVERY = 240
# User Long Poll не присылает событий о заявках в друзья — остаётся спрашивать VK
FRIENDS_EVERY = 60
THROTTLED_PAUSE = 3600
# десятки заявок подряд — прямой путь к капче и временной блокировке аккаунта; очередь разбирается пачками,
# чтобы между ними успевал обновляться вечный онлайн
ACTIONS_PER_RUN = 20
ACTION_PAUSE = 3.0


class Autopilot:
    def __init__(self, vk, store: Store, sleep: Callable[[float], None] = time.sleep,
                 now: Callable[[], float] = time.monotonic):
        self._vk = vk
        self._store = store
        self._sleep = sleep
        self._now = now
        self._due: dict[str, float] = {}
        self._paused_until = 0.0
        self._failed: set[tuple[str, int]] = set()
        self._jobs: dict[str, tuple[float, Callable[[str], bool | None]]] = {
            ETERNAL_ONLINE: (ONLINE_EVERY, lambda _: self._vk.set_online()),
            AUTO_ACCEPT: (FRIENDS_EVERY, lambda key: self._each(key, self._vk.friend_requests(False),
                                                                 self._vk.add_friend)),
            AUTO_UNFOLLOW: (FRIENDS_EVERY, lambda key: self._each(key, self._vk.friend_requests(True),
                                                                   self._vk.delete_friend)),
            AUTO_CLEAN: (FRIENDS_EVERY, lambda key: self._each(key, self._vk.dead_friends(),
                                                                self._vk.delete_friend)),
        }

    def run_forever(self) -> None:
        while True:
            self.tick()
            self._sleep(TICK_SECONDS)

    def tick(self) -> None:
        for key, (every, job) in self._jobs.items():
            if not self._store.get(key, False):
                self._due.pop(key, None)
                continue
            if self._now() < max(self._due.get(key, 0.0), self._paused_until):
                continue
            unfinished = False
            try:
                unfinished = bool(job(key))
            except Throttled as e:
                log.warning("VK просит притормозить (%s), автоматика на паузе %.0f мин", e, THROTTLED_PAUSE / 60)
                self._paused_until = self._now() + THROTTLED_PAUSE
            except Exception:
                log.exception("Автоматика %s упала, повтор через %.0f с", key, every)
            self._due[key] = self._now() + (0 if unfinished else every)

    # одна заявка от удалённого или заблокировавшего нас человека не должна навсегда занять очередь
    def _each(self, key: str, user_ids: list[int], action: Callable[[int], None]) -> bool:
        pending = [user_id for user_id in user_ids if (key, user_id) not in self._failed]
        for user_id in pending[:ACTIONS_PER_RUN]:
            if not self._store.get(key, False):
                return False
            try:
                action(user_id)
            except Throttled:
                raise
            except Exception as e:
                self._failed.add((key, user_id))
                log.warning("Автоматика %s пропускает id%s: %s", key, user_id, e)
            self._sleep(ACTION_PAUSE)
        return len(pending) > ACTIONS_PER_RUN
