def attachment_id(kind: str, obj: dict) -> str:
    key = f"_{obj['access_key']}" if obj.get("access_key") else ""
    owner = obj.get("owner_id") or obj.get("to_id") or obj.get("from_id")
    return f"{kind}{owner}_{obj['id']}{key}"


CIRCLE = "video_message"
REATTACHABLE = frozenset({"photo", "video", "audio", "doc", "audio_message", "wall", "market", "poll"})


# кружочек приходит вложением video с type=video_message, а отправить его VK даёт только как video_message…:
# с префиксом video вложение молча отбрасывается
def reattach_id(attachment: dict) -> str:
    obj = attachment[attachment["type"]]
    return attachment_id(CIRCLE if is_circle(obj) else attachment["type"], obj)


def reattach_ids(message: dict) -> str:
    return ",".join(reattach_id(a) for a in message.get("attachments") or []
                    if a["type"] in REATTACHABLE and a[a["type"]].get("id") is not None)


def is_circle(obj: dict) -> bool:
    return obj.get("type") == CIRCLE


def is_circle_id(attachment: str) -> bool:
    return attachment.startswith(CIRCLE)


def first_attachment(message: dict) -> dict | None:
    attachments = message.get("attachments") or []
    return attachments[0] if attachments else None


# голосовое или кружочек часто пересылают, и команда отвечает на пересылку, а не на оригинал
def media_of(message: dict | None) -> dict | None:
    if not message:
        return None
    attachment = first_attachment(message)
    if attachment is not None:
        return attachment
    return next(filter(None, map(media_of, message.get("fwd_messages") or [])), None)


def circle_id(message: dict | None) -> str | None:
    attachment = media_of(message)
    video = attachment.get("video") if attachment else None
    return reattach_id(attachment) if video and is_circle(video) else None


def voice_url(message: dict | None) -> str | None:
    attachment = media_of(message)
    voice = attachment.get("audio_message") if attachment else None
    return voice["link_ogg"] if voice else None
