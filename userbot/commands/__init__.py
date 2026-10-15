from userbot.commands import access, assoc, images, info, messages, privacy, voice
from userbot.context import Command

COMMANDS: list[Command] = [
    *voice.COMMANDS,
    *images.COMMANDS,
    *info.COMMANDS,
    *access.COMMANDS,
    *assoc.COMMANDS,
    *messages.COMMANDS,
    *privacy.COMMANDS,
]
