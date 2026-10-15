# vk-bot, если когда-нибудь окажется на этом же аккаунте, считает всё, что аккаунт отправил, командой владельца.
# Разбор повторяет vk-mcp (common/commands.py) и vk-userbot (userbot/commands.py): меняется там — меняй здесь.
COMMAND_WORDS = frozenset({"кик", "kick", "бан", "чс", "ban", "пермобан", "добавить", "вернуть", "мут", "mute",
                           "стата", "статистика", "неактив"})
DELETE_WORD = "смс"
COMMAND_PREFIXES = "!/-"
TRAILING = ",.:!"
# «помощь» vk-bot исполняет только когда в сообщении больше ничего нет
BARE_WORDS = frozenset({"помощь"})


def deletes_message(word: str) -> bool:
    return word.startswith("-") and word.lstrip(COMMAND_PREFIXES).rstrip(TRAILING) == DELETE_WORD


def looks_like_command(text: str | None) -> bool:
    words = (text or "").split()
    if not words:
        return False
    word = words[0].lower()
    if word.startswith(("/", "!")) or word.rstrip(TRAILING) in COMMAND_WORDS or deletes_message(word):
        return True
    return len(words) == 1 and word.rstrip(",.:!?") in BARE_WORDS
