from tests.fakes import CHAT, OWNER, STRANGER, message, in_peer
from userbot.attachments import reattach_ids

CIRCLE = {"type": "video", "video": {"type": "video_message", "owner_id": 9, "id": 7, "access_key": "k"}}
VIDEO = {"type": "video", "video": {"owner_id": 9, "id": 8, "access_key": "k"}}
CIRCLE_ID = "video_message9_7_k"


def replying(text, attachment, **extra):
    return message(text, reply_message={"id": 5, "from_id": STRANGER, "attachments": [attachment]}, **extra)


def test_circles_are_reattached_as_video_message():
    assert reattach_ids({"attachments": [CIRCLE, VIDEO]}) == f"{CIRCLE_ID},video9_8_k"


def test_saved_circle_is_sent_by_the_voice_command(router, vk, store):
    router.handle(replying("/сгс", CIRCLE))
    assert store.get("saved_audio") == {"1": CIRCLE_ID} and vk.uploads == []
    assert "Кружочек сохранён как «1»" in in_peer(vk, OWNER)[0]["text"]
    router.handle(message("/гс 1"))
    assert in_peer(vk, CHAT)[-1]["attachment"] == CIRCLE_ID


def test_plain_video_is_not_saved(router, store):
    router.handle(replying("/сгс", VIDEO))
    assert store.get("saved_audio") is None


def test_circle_that_stopped_working_is_reported(router, vk, store):
    store.put_new("saved_audio", "привет", CIRCLE_ID)
    sent = vk.send

    def refuse_circles(peer_id, text=None, **params):
        if params.get("attachment") == CIRCLE_ID:
            raise RuntimeError("message is empty or invalid")
        return sent(peer_id, text, **params)

    vk.send = refuse_circles
    router.handle(message("/гс привет"))
    assert in_peer(vk, CHAT) == []
    assert "не отправился" in in_peer(vk, OWNER)[0]["text"]


def test_copy_reposts_foreign_circle(router, vk):
    router.handle(replying("/кгс", CIRCLE))
    assert in_peer(vk, CHAT) == [{"peer_id": CHAT, "text": None, "attachment": CIRCLE_ID}] and vk.uploads == []


def test_saved_list_marks_circles(router, vk, store):
    store.put_new("saved_audio", "голос", "audio_message1_2")
    store.put_new("saved_audio", "круг", CIRCLE_ID)
    router.handle(message("/гсы"))
    text = in_peer(vk, OWNER)[0]["text"]
    assert "🎀 голос" in text and "📹 круг" in text
