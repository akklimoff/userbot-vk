import os
import textwrap

import config
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
from vk_api import VkUpload

FONT_SIZE = 24
FONT_CANDIDATES = ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "Arial Unicode.ttf")


def caption_font():
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, FONT_SIZE)
        except OSError:
            continue
    return ImageFont.load_default(FONT_SIZE)


# текст рисуется Pillow, а не ImageMagick: в label: строка с @ читает файл с диска, а через shell — выполняет команды
def add_caption(path, text):
    picture = ImageOps.expand(ImageOps.expand(Image.open(path).convert("RGB"), 3, "black"), 2, "white")
    font = caption_font()
    draw = ImageDraw.Draw(picture)
    chars_per_line = max(10, picture.width // max(1, int(draw.textlength("о", font=font))))
    caption = "\n".join(textwrap.wrap(text, chars_per_line)) or " "
    left, top, right, bottom = draw.multiline_textbbox((0, 0), caption, font=font, align="center")
    width = max(picture.width, right - left) + 40
    canvas = Image.new("RGB", (width, picture.height + (bottom - top) + 70), "black")
    canvas.paste(picture, ((width - picture.width) // 2, 20))
    ImageDraw.Draw(canvas).multiline_text((width // 2, picture.height + 40), caption, fill="white", font=font,
                                          anchor="ma", align="center")
    canvas.save(path, format="PNG")


def cmd(api, message, args, uploader: VkUpload):
    attach = message.get('attachments')
    reply = message.get('reply_message')
    if (len(attach) == 0 and reply is None) or args[1] is None:
        api.messages.send(
            peer_id=message['peer_id'],
            random_id=0,
            message=f"{config.prefixes['error']} Необходимо прикрепить фотографию и написать текст: /text [text]",
            reply_to=message['id']
        )
        return

    try:
        if reply is not None:
            img = reply['attachments'][0]['photo']['sizes'].pop()['url']
        else:
            img = attach[0]['photo']['sizes'].pop()['url']
    except:
        api.messages.send(
            peer_id=message['peer_id'],
            random_id=0,
            message=f"{config.prefixes['error']} Необходимо прикрепить фотографию и написать текст: /text [text]",
            reply_to=message['id']
        )
        return

    filename = "files/" + os.path.basename(img).split('?')[0]
    if len(filename.split('.')) < 2: filename += ".png"

    r = requests.get(img)
    with open(filename, 'wb') as f:
        f.write(r.content)

    add_caption(filename, " ".join(args[1:]))

    uploaded = uploader.photo_messages(filename, peer_id=message['peer_id'])[0]
    attach = f"photo{uploaded['owner_id']}_{uploaded['id']}"

    os.remove(filename)
    api.messages.send(
        peer_id=message['peer_id'],
        random_id=0,
        attachment=attach,
        reply_to=message['id']
    )
    return
