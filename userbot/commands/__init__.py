from userbot.commands import access, auto, info, messages, voice
from userbot.context import Command

COMMANDS: list[Command] = [
    *voice.COMMANDS,
    *info.COMMANDS,
    *access.COMMANDS,
    *auto.COMMANDS,
    *messages.COMMANDS,
]
