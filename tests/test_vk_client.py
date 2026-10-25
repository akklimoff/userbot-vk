import pytest
import requests

from userbot import vk
from userbot.vk import VkClient


class FlakyUpload:
    def __init__(self, failures):
        self.failures = failures
        self.calls = 0

    def audio_message(self, path, peer_id):
        self.calls += 1
        if self.calls <= self.failures:
            raise requests.exceptions.JSONDecodeError("Expecting value", "<html>504</html>", 0)
        return {"audio_message": {"id": 7, "owner_id": 5, "access_key": "k"}}


class Friends:
    def __init__(self, items):
        self.items = items
        self.params = None

    def getRequests(self, **params):
        self.params = params
        return {"count": len(self.items), "items": self.items}


class Api:
    def __init__(self, friends):
        self.friends = friends


def client(**attrs) -> VkClient:
    vk_client = VkClient.__new__(VkClient)
    vk_client.__dict__.update(attrs)
    return vk_client


def test_voice_upload_retries_when_vk_upload_server_fails():
    upload = FlakyUpload(failures=vk.UPLOAD_ATTEMPTS - 1)
    assert client(_upload=upload).upload_voice("voice.ogg", 1) == "audio_message5_7_k"
    assert upload.calls == vk.UPLOAD_ATTEMPTS


def test_voice_upload_gives_up_after_all_attempts():
    upload = FlakyUpload(failures=vk.UPLOAD_ATTEMPTS)
    with pytest.raises(requests.RequestException):
        client(_upload=upload).upload_voice("voice.ogg", 1)
    assert upload.calls == vk.UPLOAD_ATTEMPTS


def test_friend_requests_skip_deleted_and_banned_pages():
    friends = Friends([{"user_id": 1}, {"user_id": 2, "deactivated": "deleted"},
                       {"user_id": 3, "deactivated": "banned"}, {"user_id": 4}])
    assert client(_api=Api(friends)).friend_requests(False) == [1, 4]
    assert friends.params["extended"] == 1
