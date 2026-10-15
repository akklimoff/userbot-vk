def attachment_id(kind: str, obj: dict) -> str:
    key = f"_{obj['access_key']}" if obj.get("access_key") else ""
    owner = obj.get("owner_id") or obj.get("to_id") or obj.get("from_id")
    return f"{kind}{owner}_{obj['id']}{key}"


REATTACHABLE = frozenset({"photo", "video", "audio", "doc", "audio_message", "wall", "market", "poll"})


def reattach_ids(message: dict) -> str:
    return ",".join(attachment_id(a["type"], a[a["type"]]) for a in message.get("attachments") or []
                    if a["type"] in REATTACHABLE and a[a["type"]].get("id") is not None)


def first_attachment(message: dict) -> dict | None:
    attachments = message.get("attachments") or []
    return attachments[0] if attachments else None


def source_attachment(message: dict) -> dict | None:
    reply = message.get("reply_message")
    return (first_attachment(reply) if reply else None) or first_attachment(message)


def largest_photo_url(photo: dict) -> str:
    return max(photo["sizes"], key=lambda s: s.get("width", 0) * s.get("height", 0))["url"]


def sticker_url(sticker: dict) -> str:
    images = sticker.get("images") or sticker["images_with_background"]
    return max(images, key=lambda i: i.get("width", 0))["url"]


def image_source(message: dict) -> tuple[str, str] | None:
    """URL картинки из ответа или вложения и её вид: «photo» или «sticker» (стикер уходит обратно граффити)."""
    attachment = source_attachment(message)
    if attachment is None:
        return None
    if attachment.get("photo"):
        return largest_photo_url(attachment["photo"]), "photo"
    if attachment.get("sticker") and message.get("reply_message"):
        return sticker_url(attachment["sticker"]), "sticker"
    return None


def voice_url(message: dict | None) -> str | None:
    attachment = first_attachment(message or {})
    voice = attachment.get("audio_message") if attachment else None
    return voice["link_ogg"] if voice else None
