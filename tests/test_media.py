import pytest

from userbot import media


@pytest.mark.parametrize("url, name", [
    ("https://sun9.userapi.com/c1/a.jpg?size=1", "input.jpg"),
    ("https://psv4.userapi.com/c1/u1/audiomsg/d1/abc.ogg", "input.ogg"),
    ("https://cs1.userapi.com/stickers/1/512b", "input.png"),
    ("https://x/evil;rm -rf.sh%20x", "input.png"),
])
def test_local_name_is_safe(url, name):
    assert media.local_name(url, ".png") == name


def test_tool_failure_becomes_media_error():
    with pytest.raises(media.MediaError):
        media.run_tool(["definitely-missing-binary-for-userbot"])
