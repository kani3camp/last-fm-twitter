"""Offline renderer for the 1000 × 2000 Chart design (no API calls or credentials)."""

import datetime
import math
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import uharfbuzz as hb
from PIL import Image, ImageDraw, ImageFont

SIZE = (1000, 2000)
BACKGROUND = "#CDE9FF"
INK = "#14213D"
MUTED = "#4A5468"
PURPLE = "#6D35D6"
ORANGE = "#F0561A"
FONTS = Path(__file__).resolve().parent / "assets" / "fonts"
SCALE = 3


@lru_cache(maxsize=3)
def font_face(path):
    return hb.Face(path.read_bytes())


class TextFont:
    """Use the same shaping metrics on Windows and Linux, independent of Pillow's optional Raqm."""

    def __init__(self, path, size, weight):
        self.pillow = ImageFont.truetype(str(path), round(size * SCALE), layout_engine=ImageFont.Layout.BASIC)
        self.shaper = hb.Font(font_face(path))
        self.shaper.scale = (round(size * SCALE * 64), round(size * SCALE * 64))
        if path.name == "Unbounded.ttf":
            self.pillow.set_variation_by_axes([weight])
            self.shaper.set_variations({"wght": weight})
        self.shape = lru_cache(maxsize=256)(self._shape)

    def _shape(self, value):
        value = unicodedata.normalize("NFC", value)
        buffer = hb.Buffer()
        buffer.add_codepoints([ord(char) for char in value])
        buffer.guess_segment_properties()
        hb.shape(self.shaper, buffer, {"liga": False, "clig": False})
        clusters = sorted({info.cluster for info in buffer.glyph_infos}) + [len(value)]
        ends = dict(zip(clusters, clusters[1:], strict=False))
        glyphs, seen, cursor = [], set(), 0
        for info, position in zip(buffer.glyph_infos, buffer.glyph_positions, strict=True):
            if info.cluster not in seen:
                glyphs.append(
                    (
                        value[info.cluster : ends[info.cluster]],
                        (cursor + position.x_offset) / 64,
                        position.y_offset / 64,
                    )
                )
                seen.add(info.cluster)
            cursor += position.x_advance
        return glyphs, cursor / 64

    def getlength(self, value):
        return self.shape(value)[1]

    def getmetrics(self):
        return self.pillow.getmetrics()


@lru_cache(maxsize=64)
def font(size, weight=900, latin=False):
    path = FONTS / ("Unbounded.ttf" if latin else f"ZenMaruGothic-{'Black' if weight == 900 else 'Bold'}.ttf")
    return TextFont(path, size, weight)


def period_labels(period, day):
    """Week dates follow the design; longer periods show their retrieval date.

    getTopTracks does not return exact interval endpoints. Do not invent calendar
    month/year boundaries for its 1month/12month results.
    """
    if period == "7day":
        start = day - datetime.timedelta(days=6)
        label, title, winner = "WEEKLY", "今週聴いた曲", "NO.1 THIS WEEK"
    elif period in ("1month", "12month"):
        label, title, winner = (
            ("MONTHLY", "先月聴いた曲", "NO.1 THIS MONTH")
            if period == "1month"
            else ("YEARLY", "今年聴いた曲", "NO.1 THIS YEAR")
        )
        return f"{label} TOP 10", title, winner, f"AS OF {day:%Y.%m.%d}"
    else:
        raise ValueError(f"Unsupported period: {period}")
    end_format = "%m.%d" if start.year == day.year else "%Y.%m.%d"
    return f"{label} TOP 10", title, winner, f"{start:%Y.%m.%d} — {day.strftime(end_format)}"


def single_line(text):
    return re.sub(r"\s+", " ", text).strip()


def ellipsize(text, face, width):
    text = single_line(text)
    limit = width * SCALE
    if face.getlength(text) <= limit:
        return text
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if face.getlength(text[:middle].rstrip() + "…") <= limit:
            low = middle
        else:
            high = middle - 1
    return text[:low].rstrip() + "…"


def wrap_title(text, face, width, max_lines=2):
    """Wrap Japanese/Latin text, keeping words and Japanese closing marks together."""
    remaining = single_line(text)
    lines = []
    for _ in range(max_lines - 1):
        if face.getlength(remaining) <= width * SCALE:
            break
        cut = 1
        while cut < len(remaining) and face.getlength(remaining[: cut + 1]) <= width * SCALE:
            cut += 1
        if cut < len(remaining) and remaining[cut - 1].isascii() and remaining[cut].isascii():
            space = remaining.rfind(" ", 0, cut + 1)
            if space > 0:
                cut = space
        while cut > 1 and (remaining[cut - 1] in "（([「『" or remaining[cut] in "、。，．！？)]）」』"):
            cut -= 1
        lines.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    lines.append(ellipsize(remaining, face, width))
    return lines


class Canvas:
    def __init__(self):
        self.image = Image.new("RGB", tuple(value * SCALE for value in SIZE), BACKGROUND)
        self.draw = ImageDraw.Draw(self.image)

    def box(self, x, y, width, height, color, radius=0):
        if round((x + width) * SCALE) <= round(x * SCALE) or height <= 0:
            return
        self.draw.rounded_rectangle(
            (round(x * SCALE), round(y * SCALE), round((x + width) * SCALE) - 1, round((y + height) * SCALE) - 1),
            radius=round(radius * SCALE),
            fill=color,
        )

    def text(self, value, x, y, size, color=INK, weight=900, latin=False, line_height=None, spacing=0):
        face = font(size, weight, latin)
        # Use font metrics to match CSS line boxes rather than aligning ink bounding boxes.
        ascent, descent = face.getmetrics()
        height = line_height if line_height is not None else (1.24 if latin else 1.46) * size
        baseline = y * SCALE + (height * SCALE - ascent - descent) / 2 + ascent
        glyphs, _ = face.shape(value)
        for index, (text, dx, dy) in enumerate(glyphs):
            self.draw.text(
                (x * SCALE + dx + index * spacing * SCALE, baseline - dy),
                text,
                font=face.pillow,
                fill=color,
                anchor="ls",
            )

    def fitted(self, value, x, y, width, size, **kwargs):
        self.text(ellipsize(value, font(size, kwargs.get("weight", 900)), width), x, y, size, **kwargs)

    def centered(self, value, x, y, width, size, color, line_height):
        face = font(size, 800, True)
        self.text(value, x + (width - face.getlength(value) / SCALE) / 2, y, size, color, 800, True, line_height)

    def triangle(self, x, y, size):
        points = [(x + size / 3, y + size * 0.229), (x + size / 3, y + size * 0.771), (x + size * 0.771, y + size / 2)]
        self.draw.polygon([(round(px * SCALE), round(py * SCALE)) for px, py in points], fill=ORANGE)

    def bar(self, x, y, width, height, fraction, hero=False):
        self.box(x, y, width, height, "#FFE3D6" if hero else "#EADFFF", height / 2)
        if fraction > 0:
            filled_width = width * min(fraction, 1)
            self.box(x, y, filled_width, height, ORANGE if hero else PURPLE, min(height, filled_width) / 2)

    def badge(self, count, right, y, hero=False, large=False):
        size = 46 if hero else 34 if large else 28
        icon = 30 if hero else 22 if large else 20
        label = "回再生" if hero else "回"
        label_size = 24 if hero else 22
        gap = 10 if hero else 8
        left_pad, right_pad = (16, 24) if hero else (12, 18) if large else (10, 16)
        width = left_pad + icon + gap + font(size).getlength(str(count)) / SCALE + gap
        width += font(label_size, 700).getlength(label) / SCALE + right_pad
        height = 66 if hero else 50 if large else 42
        # Very large counts retain every digit within the available column.
        factor = min(1, (330 if hero else 260) / width)
        width *= factor
        x = right - width
        self.box(x, y, width, height, "#FFE3D6" if hero else "#F1F4F8", height / 2)
        cursor = x + left_pad * factor
        self.triangle(cursor, y + (height - icon * factor) / 2, icon * factor)
        cursor += (icon + gap) * factor
        self.text(str(count), cursor, y + (height - size * factor) / 2, size * factor, line_height=size * factor)
        cursor += (font(size).getlength(str(count)) / SCALE + gap) * factor
        self.text(label, cursor, y + (height - label_size * factor * 1.46) / 2, label_size * factor, weight=700)
        return width

    def placeholder(self, rank, y, height, large=False):
        # Dashed, rounded empty slots are intentional in the short-week reference.
        outline = "#9FB7CF"
        radius = 22 if large else 18
        points = []
        # Walk the rounded perimeter so dashes also appear on the vertical sides.
        for cx, cy, start in (
            (944 - radius, y + radius, -90),
            (944 - radius, y + height - radius, 0),
            (56 + radius, y + height - radius, 90),
            (56 + radius, y + radius, 180),
        ):
            for angle in range(start, start + 91):
                radians = math.radians(angle)
                points.append((cx + (radius - 1) * math.cos(radians), cy + (radius - 1) * math.sin(radians)))
        points.append(points[0])
        distance = 0
        for p1, p2 in zip(points, points[1:], strict=False):
            length = math.dist(p1, p2)
            position = 0
            while position < length:
                phase = (distance + position) % 8
                step = min(length - position, (4.8 if phase < 4.8 else 8) - phase)
                if step < 1e-6:
                    position += 1e-6
                    continue
                if phase < 4.8:
                    ends = [
                        (p1[0] + (p2[0] - p1[0]) * t / length, p1[1] + (p2[1] - p1[1]) * t / length)
                        for t in (position, position + step)
                    ]
                    self.draw.line(
                        [(round(px * SCALE), round(py * SCALE)) for px, py in ends],
                        fill=outline,
                        width=round(1.6 * SCALE),
                    )
                position += step
            distance += length

        self.centered(
            str(rank),
            74 if large else 68,
            y + (height - (72 if large else 44)) / 2,
            96 if large else 80,
            72 if large else 44,
            outline,
            72 if large else 44,
        )


def render_ranking(tracks, path, period, day, username="SoraraP"):
    if not tracks:
        raise ValueError("ランキング画像に表示できる再生履歴がありません")
    tracks = tracks[:10]
    heading, title, winner, dates = period_labels(period, day)
    canvas = Canvas()
    canvas.text(heading, 56, 62.72, 24, "#7B3FE4", 800, True, spacing=1.92)
    date_size = 22
    # Cross-year date ranges must also stay clear of the heading.
    while font(date_size, 600, True).getlength(dates) / SCALE + 36 > 450:
        date_size -= 1
    date_width = font(date_size, 600, True).getlength(dates) / SCALE + 36
    canvas.box(944 - date_width, 56, date_width, 43.2, "#7B3FE4", 22)
    canvas.text(dates, 962 - date_width, 64, date_size, "white", 600, True)
    canvas.text("そららPが", 56, 117.2, 80, line_height=92)
    highlight_width = font(80).getlength(title) / SCALE + 8
    canvas.box(56, 197.2 + 116 * 0.58, highlight_width, 116 * 0.34, "#FFC9AE")
    canvas.text(title, 60, 209.2, 80, line_height=92)
    x = 56
    stats = [
        (sum(int(t["playcount"]) for t in tracks), "回再生"),
        (len(tracks), "曲"),
        (len({t["artist"]["name"] for t in tracks}), "アーティスト"),
    ]
    for value, label in stats:
        number_width = font(30).getlength(str(value)) / SCALE
        width = number_width + font(22, 700).getlength(label) / SCALE + 44
        canvas.box(x, 319.2, width, 60, "white", 12)
        canvas.text(str(value), x + 18, 327.2, 30, "#6229C9")
        canvas.text(label, x + 26 + number_width, 336, 22, MUTED, 700)
        x += width + 12

    top = tracks[0]
    title_lines = wrap_title(top["name"], font(56), 622)
    title_height = len(title_lines) * 66.08
    content_height = 39.2 + 10 + title_height + 10 + 44
    hero_height = 36 + content_height + 28 + 66 + 36
    canvas.box(56, 407.2, 888, hero_height, "white", 32)
    canvas.centered("1", 84, 443.2 + (content_height - 170) / 2, 170, 200, ORANGE, 170)
    winner_width = font(22, 800, True).getlength(winner) / SCALE + 28 + (len(winner) - 1) * 1.32
    canvas.box(282, 443.2, winner_width, 39.2, ORANGE, 8)
    canvas.text(winner, 296, 449.2, 22, "white", 800, True, spacing=1.32)
    for i, line in enumerate(title_lines):
        canvas.text(line, 282, 492.4 + i * 66.08, 56, line_height=66.08)
    canvas.fitted(top["artist"]["name"], 282, 502.4 + title_height, 622, 30, weight=700)
    badge_y = 443.2 + content_height + 28
    # The hero badge is left aligned; other counts are right aligned.
    hero_width = 162 + font(46).getlength(str(top["playcount"])) / SCALE
    hero_width = min(330, hero_width)
    canvas.badge(int(top["playcount"]), 96 + hero_width, badge_y, hero=True)
    canvas.bar(116 + hero_width, badge_y + 26, 788 - hero_width, 14, 1, hero=True)

    y = 407.2 + hero_height + 28
    max_count = max(int(track["playcount"]) for track in tracks)
    for rank in (2, 3):
        if rank > len(tracks):
            canvas.placeholder(rank, y, 164, large=True)
        else:
            track = tracks[rank - 1]
            count = int(track["playcount"])
            canvas.box(56, y, 888, 164, "white", 22)
            canvas.centered(str(rank), 74, y + 46, 96, 72, PURPLE, 72)
            badge_width = canvas.badge(count, 916, y + 48, large=True)
            canvas.bar(806, y + 108, 110, 8, count / max_count)
            text_width = 916 - max(110, badge_width) - 24 - 194
            lines = wrap_title(track["name"], font(34), text_width)
            text_y = y + (164 - (len(lines) * 41.48 + 4 + 33.8)) / 2
            for i, line in enumerate(lines):
                canvas.text(line, 194, text_y + i * 41.48, 34, line_height=41.48)
            canvas.fitted(
                track["artist"]["name"],
                194,
                text_y + len(lines) * 41.48 + 4,
                text_width,
                26,
                weight=700,
                line_height=33.8,
            )
        y += 180
    y += 12  # 28px gap after the top-three group (rather than its internal 16px gap).
    # In the reference's flex layout, dashed borders add 3.2px to an empty slot's
    # outer height. Deduct that space before distributing the shared row content.
    empty_border_height = 3.2
    empty_slots = 10 - max(3, len(tracks))
    row_height = (1900 - y - 60 - empty_slots * empty_border_height) / 7
    for rank in range(4, 11):
        height = row_height + (empty_border_height if rank > len(tracks) else 0)
        if rank > len(tracks):
            canvas.placeholder(rank, y, height)
        else:
            track = tracks[rank - 1]
            count = int(track["playcount"])
            canvas.box(56, y, 888, row_height, "white", 18)
            canvas.centered(str(rank), 68, y + (row_height - 44) / 2, 80, 44, INK, 44)
            badge_width = canvas.badge(count, 924, y + (row_height - 58) / 2)
            canvas.bar(814, y + (row_height - 58) / 2 + 50, 110, 8, count / max_count)
            text_width = 924 - max(110, badge_width) - 22 - 170
            text_y = y + (row_height - 74) / 2
            canvas.fitted(track["name"], 170, text_y, text_width, 32, line_height=40)
            canvas.fitted(track["artist"]["name"], 170, text_y + 42, text_width, 22, color=MUTED, weight=700)
        y += height + 10
    canvas.text("Data: Last.fm", 56, 1928, 22, weight=700)
    profile = f"last.fm/user/{username}"
    canvas.text(profile, 944 - font(22, 700).getlength(profile) / SCALE, 1928, 22, weight=700)
    image = canvas.image.resize(SIZE, Image.Resampling.LANCZOS)
    image.save(path, **({"quality": 95, "subsampling": 0} if str(path).lower().endswith((".jpg", ".jpeg")) else {}))
