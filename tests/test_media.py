import subprocess

import pytest
from PIL import Image

from userbot import media
from userbot.attachments import image_source, largest_photo_url


def test_caption_never_runs_external_tools(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("caption must not start processes")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    source, target = tmp_path / "in.png", tmp_path / "out.png"
    Image.new("RGB", (200, 100), "red").save(source)
    media.add_caption(str(source), str(target), '"; touch /tmp/pwned; " label:@/proc/self/environ')
    result = Image.open(target)
    assert result.width > 200 and result.height > 100


def test_negate_keeps_transparency(tmp_path):
    source, target = tmp_path / "in.png", tmp_path / "out.png"
    Image.new("RGBA", (2, 2), (10, 20, 30, 40)).save(source)
    media.negate(str(source), str(target))
    assert Image.open(target).getpixel((0, 0)) == (245, 235, 225, 40)


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


def test_largest_photo_is_chosen():
    sizes = [{"url": "big", "width": 800, "height": 600}, {"url": "small", "width": 75, "height": 50}]
    assert largest_photo_url({"sizes": sizes}) == "big"


def test_sticker_only_from_reply():
    sticker = {"type": "sticker", "sticker": {"images": [{"url": "s", "width": 128}]}}
    assert image_source({"attachments": [sticker]}) is None
    assert image_source({"attachments": [], "reply_message": {"attachments": [sticker]}}) == ("s", "sticker")


def test_negate_keeps_palette_transparency(tmp_path):
    source, target = tmp_path / "in.png", tmp_path / "out.png"
    Image.new("RGBA", (2, 2), (0, 0, 0, 0)).convert("P").save(source, transparency=0)
    media.negate(str(source), str(target))
    assert Image.open(target).getpixel((0, 0))[3] == 0


def test_broken_image_becomes_media_error(tmp_path):
    source = tmp_path / "in.png"
    source.write_bytes(b"not an image")
    with pytest.raises(media.MediaError):
        media.negate(str(source), str(tmp_path / "out.png"))
