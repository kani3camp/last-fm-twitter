# 使用するTwitter App：last_fm twitter (アイマス垢でログイン)
# App ID : 16411000
#
import datetime
import json
import os
import urllib.request

import requests

# .env ファイルをロードして環境変数へ反映
from dotenv import load_dotenv

from ranking_image import random_background, render_ranking

load_dotenv()

LOCAL_IMG_PATH = "ranking.jpg"
LAMBDA_IMG_PATH = "/tmp/ranking.jpg"

LASTFM_API_KEY = os.environ["LASTFM_API_KEY"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

MAX_RANKED_TRACKS = 10
period = None
is_lambda = False

JST = datetime.timezone(datetime.timedelta(hours=+9), "JST")
today = datetime.datetime.now(JST).date()


class Period:
    SEVEN_DAYS = "7day"
    ONE_MONTH = "1month"
    TWELVE_MONTH = "12month"


def main():
    data = get_last_fm_tracks()
    message = initial_message_str()

    if not select_ranked_tracks(data):
        send_message_to_discord(
            f"{message}\n再生履歴が0件のため、ランキング画像は作成しませんでした。",
            DISCORD_WEBHOOK_URL,
        )
        return

    img_path = resolve_img_path()
    draw_ranking_img(data, img_path=img_path)
    send_image_to_discord(message, DISCORD_WEBHOOK_URL, img_path)


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


def select_ranked_tracks(data):
    """再生回数が1回以上の曲を、最大10曲までランキング対象にする。"""
    tracks = data["toptracks"].get("track") or []
    if isinstance(tracks, dict):
        tracks = [tracks]
    return [track for track in tracks if int(track["playcount"]) >= 1][:MAX_RANKED_TRACKS]


def draw_ranking_img(data, img_path: str):
    render_ranking(select_ranked_tracks(data), img_path, period, today, background=random_background())


def send_message_to_discord(message, webhook_url):
    response = requests.post(webhook_url, json={"content": message}, timeout=30)
    response.raise_for_status()
    print(f"Response: {response}")


def send_image_to_discord(message, webhook_url, file_path):
    data = {"content": message}
    file_data = {"file": (open(file_path, "rb"))}
    response = requests.post(webhook_url, data=data, files=file_data)
    print(f"Response: {response}")


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
