# 使用するTwitter App：last_fm twitter (アイマス垢でログイン)
# App ID : 16411000
#
import datetime
import json
import os
import random
import sys
import urllib.request

import boto3
import requests

# .env ファイルをロードして環境変数へ反映
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont

from utils import draw_height, draw_width

load_dotenv()

LOCAL_IMG_PATH = "ranking.jpg"
LAMBDA_IMG_PATH = "/tmp/ranking.jpg"

LASTFM_API_KEY = os.environ["LASTFM_API_KEY"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

S3_BUCKET_NAME = "last-fm-twitter"

global period
global theme_color
is_lambda = False

JST = datetime.timezone(datetime.timedelta(hours=+9), "JST")
today = datetime.datetime.now(JST).date()


class Period:
    SEVEN_DAYS = "7day"
    ONE_MONTH = "1month"
    TWELVE_MONTH = "12month"


FONT1 = "fonts/azuki.ttf"  # http://azukifont.com/font/azuki.html
FONT2 = "fonts/Ronde-B_square.otf"  # https://moji-waku.com/ronde/
FONT3 = "fonts/851letrogo_007.ttf"  # http://pm85122.onamae.jp/851letrogopage.html
FONT4 = "fonts/logotypejp_mp_b_1.1.ttf"  # https://logotype.jp/corporate-logo-font-dl.html#i-11
FONT5 = "fonts/logotypejp_mp_m_1.1.ttf"  # https://logotype.jp/corporate-logo-font-dl.html#i-11


def main():
    data = get_last_fm_tracks()
    # ツイートする文字列
    message = initial_message_str()
    draw_ranking_img(data, img_path=resolve_img_path())

    send_image_to_discord(message, DISCORD_WEBHOOK_URL, resolve_img_path())


def resolve_img_path() -> str:
    if is_lambda:
        return LAMBDA_IMG_PATH
    else:
        return LOCAL_IMG_PATH


def get_last_fm_tracks():
    global period
    url = "https://ws.audioscrobbler.com/2.0/"
    params = {
        "format": "json",
        "api_key": LASTFM_API_KEY,
        "method": "user.getTopTracks",
        "user": "SoraraP",
        "period": period,
    }
    req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}")
    with urllib.request.urlopen(req) as res:
        body = res.read()
        body = json.loads(body)
        return body


def initial_message_str():
    tweet = "そららPが"
    if period == Period.SEVEN_DAYS:
        tweet += "今週"
    elif period == Period.ONE_MONTH:
        tweet += "先月"
    elif period == Period.TWELVE_MONTH:
        tweet += "今年"
    tweet += "聞いた曲ランキング\n"
    return tweet[:-1]


def draw_ranking_img(data, img_path: str, theme_color_override: tuple[int, int, int] | None = None):
    global period
    global theme_color
    if theme_color_override is None:
        theme_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    else:
        theme_color = theme_color_override
    img_size = (1080, 2160)
    img = Image.new("RGB", img_size, color=theme_color)
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)

    # 画像見出し
    font_size = 70
    font: FreeTypeFont = ImageFont.truetype(font=f"/tmp/{FONT4}" if is_lambda else FONT4, size=font_size)
    position = (int(img_size[0] / 2 - draw_width(draw, initial_message_str(), font) / 2), 10)
    draw.text(xy=position, text=initial_message_str(), fill="white", font=font)

    draw_table(draw, img_size, data)

    # 日付
    font_size = 40
    font = ImageFont.truetype(font=f"/tmp/{FONT4}" if is_lambda else FONT4, size=font_size)
    position = (
        img_size[0] - draw_width(draw, str(today), font) - 10,
        img_size[1] - draw_height(draw, str(today), font) - 10,
    )
    draw.text(xy=position, text=str(today), fill="white", font=font)

    img.save(img_path)


def draw_table(draw: ImageDraw.ImageDraw, size, data):
    global theme_color
    width, height = size
    num_songs = 10

    margin_top = 100
    margin_bottom = 50
    side_margin = 20

    left_top = (side_margin, margin_top)
    right_top = (width - side_margin, margin_top)
    left_bottom = (side_margin, height - margin_bottom)
    right_bottom = (width - side_margin, height - margin_bottom)

    # 四角
    draw.rectangle((left_top, right_bottom), fill="white", width=0)
    draw.line((left_top, left_bottom), fill=theme_color, width=5)
    draw.line((right_top, right_bottom), fill=theme_color, width=5)
    draw.line((left_top, right_top), fill=theme_color, width=5)
    draw.line((left_bottom, right_bottom), fill=theme_color, width=5)

    table_height = height - margin_top - margin_bottom

    # 横線
    xy = (left_top, right_top)
    for _ in range(num_songs):
        xy = [list(xy[0]), list(xy[1])]
        xy[0][1] = xy[0][1] + int(table_height / 11)
        xy[1][1] = xy[0][1]
        xy = (tuple(xy[0]), tuple(xy[1]))
        draw.line(xy, fill=theme_color, width=5)

    # 縦線
    rank_width = 100
    xy = (left_top[0] + rank_width, left_top[1], left_bottom[0] + rank_width, left_bottom[1])
    draw.line(xy, fill=theme_color, width=5)

    titles, artists, playcount = ["タイトル"], ["アーティスト"], ["再生回数"]
    track_num = 0
    for track in data["toptracks"]["track"]:
        if track_num < num_songs:
            if int(track["playcount"]) >= 1:
                titles.append(track["name"])
                artists.append(track["artist"]["name"])
                playcount.append(track["playcount"])
                track_num += 1
    if track_num != num_songs:
        print("再生履歴が少なすぎます")
        sys.exit()

    # 順位
    rank_size = 80
    rank_xy = (left_top[0] + 10, left_top[1] + 10)
    for n in range(num_songs + 1):
        if n == 0:
            font = ImageFont.truetype(font=f"/tmp/{FONT1}" if is_lambda else FONT1, size=rank_size)
            text = "順\n位"
            draw.text(xy=rank_xy, text=text, fill=0, font=font)
        else:
            text = str(n)
            if n < 10:
                rank_size = 100
                rank_xy = (left_top[0] + 25, left_top[1] + 10 + n * int(table_height / (num_songs + 1)))
            else:
                rank_size = 85
                rank_xy = (left_top[0] + 5, left_top[1] + 10 + n * int(table_height / (num_songs + 1)))
            font = ImageFont.truetype(font=f"/tmp/{FONT3}" if is_lambda else FONT3, size=rank_size)
            draw.text(xy=rank_xy, text=text, fill="purple", font=font)

    # タイトル
    title_size = 75
    font = ImageFont.truetype(font=f"/tmp/{FONT4}" if is_lambda else FONT4, size=title_size)
    title_xy = (left_top[0] + rank_width + 20, left_top[1] + 10)
    for n in range(num_songs + 1):
        draw.text(xy=title_xy, text=titles[n], fill=(255, 130, 39), font=font)
        title_xy = list(title_xy)
        title_xy[1] = title_xy[1] + int(table_height / (num_songs + 1))
        title_xy = tuple(title_xy)

    # 再生回数
    playcount_xy = (left_top[0] + rank_width + 20, left_top[1] + 110)
    playcount_size = 60
    font = ImageFont.truetype(font=f"/tmp/{FONT5}" if is_lambda else FONT5, size=playcount_size)
    for n in range(num_songs + 1):
        text = playcount[n]
        if n != 0:  # 凡例には「回」を付けない
            text += "回"
        draw.text(xy=playcount_xy, text=text, fill=0, font=font)
        playcount_xy = list(playcount_xy)
        playcount_xy[1] = playcount_xy[1] + int(table_height / (num_songs + 1))
        playcount_xy = tuple(playcount_xy)

    # アーティスト
    for n in range(num_songs + 1):
        artist = "" + artists[n]
        artist_xy = (
            width - side_margin - draw_width(draw, artist, font) - 20,
            left_top[1] + 110 + n * int(table_height / (num_songs + 1)),
        )
        artist_size = 65
        font = ImageFont.truetype(font=f"/tmp/{FONT5}" if is_lambda else FONT5, size=artist_size)
        while draw_width(draw, artist, font) > width - 2 * side_margin - rank_width - 200:
            artist = artist[:-2] + "…"
            artist_xy = (
                width - side_margin - draw_width(draw, artist, font) - 20,
                left_top[1] + 110 + n * int(table_height / (num_songs + 1)),
            )
        font = ImageFont.truetype(font=f"/tmp/{FONT5}" if is_lambda else FONT5, size=artist_size)
        draw.text(xy=artist_xy, text=artist, fill="black", font=font)
        artist_xy = list(artist_xy)
        artist_xy[1] = artist_xy[1] + int(table_height / (num_songs + 1))
        artist_xy = tuple(artist_xy)


def send_image_to_discord(message, webhook_url, file_path):
    data = {"content": message}
    file_data = {"file": (open(file_path, "rb"))}
    response = requests.post(webhook_url, data=data, files=file_data)
    print(f"Response: {response}")


def download_s3_ttf(bucket_name: str, file_path: str):
    s3 = boto3.client("s3")

    bucket = bucket_name
    key = file_path
    download_path = f"/tmp/{file_path}"  # Lambda has write access to the /tmp directory

    s3.download_file(bucket, key, download_path)


def pre_main():
    global period
    weekday = today.weekday()
    day = today.day
    month = today.month

    # デバッグ用
    # period = Period.ONE_MONTH
    # main()

    if weekday == 6:  # Sunday
        period = Period.SEVEN_DAYS
        main()
    if day == 1:
        period = Period.ONE_MONTH
        main()
    if month == 12 and day == 30:
        period = Period.TWELVE_MONTH
        main()

    print(today)
    print("process end.")


if __name__ == "__main__":
    pre_main()


PERIOD_BY_KEY = {
    "7day": Period.SEVEN_DAYS,
    "1month": Period.ONE_MONTH,
    "12month": Period.TWELVE_MONTH,
}


def lambda_handler(event, context):
    global is_lambda, period
    is_lambda = True

    os.makedirs("/tmp/fonts/", exist_ok=True)
    for f in [FONT1, FONT2, FONT3, FONT4, FONT5]:
        download_s3_ttf(bucket_name=S3_BUCKET_NAME, file_path=f)

    # テスト用: イベントで period を指定されていればそれで実行
    if event and (key := event.get("period")):
        if key in PERIOD_BY_KEY:
            period = PERIOD_BY_KEY[key]
            main()
            print(today)
            print("process end.")
            return
        raise ValueError(f"period must be one of: {list(PERIOD_BY_KEY)}")

    pre_main()
