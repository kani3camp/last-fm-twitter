from PIL.ImageDraw import ImageDraw


def draw_width(draw: ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox(xy=(0, 0), text=text, font=font)
    return bbox[2] - bbox[0]


def draw_height(draw: ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox(xy=(0, 0), text=text, font=font)
    return bbox[3] - bbox[1]
