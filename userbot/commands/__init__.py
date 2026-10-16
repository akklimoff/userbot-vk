from userbot.commands import access, info, messages, voice
from userbot.context import Command

COMMANDS: list[Command] = [
    *voice.COMMANDS,
    *info.COMMANDS,
    *access.COMMANDS,
    *messages.COMMANDS,
]
