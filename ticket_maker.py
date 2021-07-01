from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

TEMPLATE_PATH = 'files/ticket_template.jpg'
FONT_PATH = 'files/roboto_regular.ttf'
AVATAR_PATH = 'files/avatar.jpg'
BLACK = (0, 0, 0, 255)
DEP_OFFSET = (340, 160)
ARVL_OFFSET = (295, 220)
DATE_OFFSET = (338, 278)
SITS_OFFSET = (305, 335)
COMM_OFFSET = (260, 392)
PHONE_OFFSET = (175, 447)
AVATAR_OFFSET = (790, 10)


def make_ticket(departure, arrival, date, sits, comment, phone):
    template = Image.open(TEMPLATE_PATH)
    font = ImageFont.truetype(FONT_PATH, size=32)
    draw = ImageDraw.Draw(template)
    draw.text(DEP_OFFSET, departure, font=font, fill=BLACK)
    draw.text(ARVL_OFFSET, arrival, font=font, fill=BLACK)
    draw.text(DATE_OFFSET, date, font=font, fill=BLACK)
    draw.text(SITS_OFFSET, sits, font=font, fill=BLACK)
    draw.text(COMM_OFFSET, comment, font=font, fill=BLACK)
    draw.text(PHONE_OFFSET, phone, font=font, fill=BLACK)
    avatar = Image.open(AVATAR_PATH)
    template.paste(avatar, AVATAR_OFFSET)
    temp_file = BytesIO()
    template.save(temp_file, 'jpeg')
    temp_file.seek(0)
    return temp_file
