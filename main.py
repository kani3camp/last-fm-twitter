# 使用するTwitter App：last_fm twitter (アイマス垢でログイン)
# App ID : 16411000
#
import os

import tweepy
import urllib.request
import json
import unicodedata
import datetime
from PIL import Image, ImageFont, ImageDraw
import random
import dropbox
import sys


from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
)

YOUR_CHANNEL_ACCESS_TOKEN = os.environ['LineMessageAPIChannelAccessToken']
YOUR_CHANNEL_SECRET = os.environ['LineMessageAPIChannelSecret']
line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

TWITTER_CONSUMER_KEY = os.environ['TWITTER_CONSUMER_KEY']
TWITTER_CONSUMER_SECRET = os.environ['TWITTER_CONSUMER_SECRET']
TWITTER_ACCESS_TOKEN = os.environ['TWITTER_ACCESS_TOKEN']
TWITTER_ACCESS_TOKEN_SECRET = os.environ['TWITTER_ACCESS_TOKEN_SECRET']

DROPBOX_TOKEN = os.environ['DROPBOX_TOKEN']

LASTFM_API_KEY = os.environ['LASTFM_API_KEY']

LINE_USER_ID = os.environ['LINE_USER_ID']

global period
global theme_color


class Period:
    SEVEN_DAYS = '7day'
    ONE_MONTH = '1month'
    TWELVE_MONTH = '12month'


FONT1 = 'fonts/azuki.ttf'             # http://azukifont.com/font/azuki.html
FONT2 = 'fonts/Ronde-B_square.otf'    # https://moji-waku.com/ronde/
FONT3 = 'fonts/851letrogo_007.ttf'    # http://pm85122.onamae.jp/851letrogopage.html
FONT4 = 'fonts/logotypejp_mp_b_1.1.ttf'   # https://logotype.jp/corporate-logo-font-dl.html#i-11
FONT5 = 'fonts/logotypejp_mp_m_1.1.ttf'   # https://logotype.jp/corporate-logo-font-dl.html#i-11


def main():
    data = get_last_fm_tracks()
    # ツイートする文字列
    tweet_str = initial_tweet_str()
    draw_ranking_img(data)

    twitter_api = initialize_twitter_api()
    twitter_api.update_with_media(filename='ranking.jpg', status=tweet_str)
    img_url1, img_url2 = upload_img_to_dropbox()
    line_send_message(tweet_str, img_url1, img_url2)


def initialize_twitter_api():
    auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
    auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
    return tweepy.API(auth)


def get_last_fm_tracks():
    global period
    url = 'http://ws.audioscrobbler.com/2.0/'
    params = {
        'format': 'json',
        'api_key': LASTFM_API_KEY,
        'method': 'user.getTopTracks',
        'user': 'SoraraP',
        'period': period,
    }
    req = urllib.request.Request('{}?{}'.format(url, urllib.parse.urlencode(params)))
    with urllib.request.urlopen(req) as res:
        body = res.read()
        body = json.loads(body)
        return body


def initial_tweet_str():
    tweet = 'そららPが'
    if period == Period.SEVEN_DAYS:
        tweet += '今週'
    elif period == Period.ONE_MONTH:
        tweet += '先月'
    elif period == Period.TWELVE_MONTH:
        tweet += '今年'
    tweet += '聞いた曲ランキング\n'
    return tweet[:-1]


def draw_ranking_img(data):
    global period
    global theme_color
    theme_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    img_size = (1080, 2160)
    img = Image.new('RGB', img_size, color=theme_color)
    draw = ImageDraw.Draw(img)
    
    # 画像見出し
    font_size = 70
    font = ImageFont.truetype(font=FONT4, size=font_size)
    position = (int(img_size[0] / 2 - draw.textsize(initial_tweet_str(), font)[0] / 2), 10)
    draw.text(xy=position, text=initial_tweet_str(), fill='white', font=font)
    
    draw_table(draw, img_size, data)
    
    # 日付
    font_size = 40
    font = ImageFont.truetype(font=FONT4, size=font_size)
    position = (img_size[0] - draw.textsize(str(today), font)[0] - 10, img_size[1] - draw.textsize(str(today), font)[1] -10)
    draw.text(xy=position, text=str(today), fill='white', font=font)
    
    img.save('ranking.jpg')
    img2 = img.resize((120, 240))
    img2.save('ranking_preview.jpg')


def draw_table(draw, size, data):
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
    draw.rectangle((left_top, right_bottom), fill='white', width=0)
    draw.line((left_top, left_bottom), fill=theme_color, width=5)
    draw.line((right_top, right_bottom), fill=theme_color, width=5)
    draw.line((left_top, right_top), fill=theme_color, width=5)
    draw.line((left_bottom, right_bottom), fill=theme_color, width=5)
    
    table_height = height - margin_top - margin_bottom
    
    # 横線
    xy = (left_top, right_top)
    for n in range(num_songs):
        xy = [list(xy[0]), list(xy[1])]
        xy[0][1] = xy[0][1] + int(table_height/11)
        xy[1][1] = xy[0][1]
        xy = (tuple(xy[0]), tuple(xy[1]))
        draw.line(xy, fill=theme_color, width=5)
    
    # 縦線
    rank_width = 100
    xy = (left_top[0] + rank_width, left_top[1], left_bottom[0] + rank_width, left_bottom[1])
    draw.line(xy, fill=theme_color, width=5)
    
    titles, artists, playcount = ['タイトル'], ['アーティスト'], ['再生回数']
    track_num = 0
    for track in data['toptracks']['track']:
        if track_num < num_songs:
            if int(track['playcount']) >= 1:
                titles.append(track['name'])
                artists.append(track['artist']['name'])
                playcount.append(track['playcount'])
                track_num += 1
    if track_num != num_songs:
        print('再生履歴が少なすぎます')
        sys.exit()
                
    # 順位
    rank_size = 80
    rank_xy = (left_top[0] + 10, left_top[1] + 10)
    for n in range(num_songs + 1):
        if n == 0:
            font = ImageFont.truetype(font=FONT1, size=rank_size)
            text = '順\n位'
            draw.text(xy=rank_xy, text=text, fill=0, font=font)
        else:
            text = str(n)
            if n < 10:
                rank_size = 100
                rank_xy = (left_top[0] + 25, left_top[1] + 10 + n*int(table_height/(num_songs+1)))
            else:
                rank_size = 85
                rank_xy = (left_top[0] + 5, left_top[1] + 10 + n*int(table_height/(num_songs+1)))
            font = ImageFont.truetype(font=FONT3, size=rank_size)
            draw.text(xy=rank_xy, text=text, fill='purple', font=font)

    # タイトル
    title_size = 75
    font = ImageFont.truetype(font=FONT4, size=title_size)
    title_xy = (left_top[0] + rank_width + 20, left_top[1] + 10)
    for n in range(num_songs + 1):
        draw.text(xy=title_xy, text=titles[n], fill=(255, 130, 39), font=font)
        title_xy = list(title_xy)
        title_xy[1] = title_xy[1] + int(table_height/(num_songs+1))
        title_xy = tuple(title_xy)
    
    # 再生回数
    playcount_xy = (left_top[0] + rank_width + 20, left_top[1] + 110)
    playcount_size = 60
    font = ImageFont.truetype(font=FONT5, size=playcount_size)
    for n in range(num_songs + 1):
        text = playcount[n]
        if n != 0:  # 凡例には「回」を付けない
            text += '回'
        draw.text(xy=playcount_xy, text=text, fill=0, font=font)
        playcount_xy = list(playcount_xy)
        playcount_xy[1] = playcount_xy[1] + int(table_height/(num_songs+1))
        playcount_xy = tuple(playcount_xy)
    
    # アーティスト
    for n in range(num_songs + 1):
        artist = '' + artists[n]
        artist_xy = (width - side_margin - draw.textsize(artist, font)[0] - 20,
                     left_top[1] + 110 + n * int(table_height/(num_songs+1)))
        artist_size = 65
        font = ImageFont.truetype(font=FONT5, size=artist_size)
        while draw.textsize(artist, font)[0] > width - 2*side_margin - rank_width - 200:
            artist = artist[:-2] + '…'
            artist_xy = (width - side_margin - draw.textsize(artist, font)[0] - 20,
                         left_top[1] + 110 + n * int(table_height / (num_songs + 1)))
        font = ImageFont.truetype(font=FONT5, size=artist_size)
        draw.text(xy=artist_xy, text=artist, fill='black', font=font)
        artist_xy = list(artist_xy)
        artist_xy[1] = artist_xy[1] + int(table_height/(num_songs+1))
        artist_xy = tuple(artist_xy)
    

def len_tweet(text):
    count = 0
    for c in text:
        if unicodedata.east_asian_width(c) in 'Na':
            count += 1
        else:
            count += 2
    return count


def upload_img_to_dropbox():
    dbx = dropbox.Dropbox(DROPBOX_TOKEN)
    # dbx.users_get_current_account()
    with open('ranking.jpg', "rb") as f:
        dbx.files_upload(f.read(), '/ranking.jpg', mode=dropbox.files.WriteMode.overwrite)
    with open('ranking_preview.jpg', "rb") as f:
        dbx.files_upload(f.read(), '/ranking_preview.jpg', mode=dropbox.files.WriteMode.overwrite)
    
    # ファイルのリンクを取得
    # setting = dropbox.sharing.SharedLinkSettings(requested_visibility=dropbox.sharing.RequestedVisibility.public)
    # link = dbx.sharing_create_shared_link_with_settings(path='/ranking.jpg', settings=setting)
    # links = dbx.sharing_list_shared_links(path='/ranking.jpg', direct_only=True).links
    # if links is not None:
    #     for link in links:
    #         img_url = link.url
    #         img_url = img_url.replace('www.dropbox', 'dl.dropboxusercontent').replace('?dl=0', '')
    #         print(img_url)
    #         return img_url

    # 上の方法だとlink取得時にshared_link_already_existsエラーが出る
    # ただしurlは毎回以下のようになる。
    return 'https://dl.dropboxusercontent.com/s/thcrs9h1x1031ti/ranking.jpg', \
           'https://dl.dropboxusercontent.com/s/thcrs9h1x1031ti/ranking_preview.jpg'


def line_send_message(text, img_url1, img_url2):
    user_id = LINE_USER_ID
    messages = [
        ImageSendMessage(
            original_content_url=img_url1,
            preview_image_url=img_url2
        ),
        TextSendMessage(text=text)
    ]
    line_bot_api.push_message(user_id, messages=messages)


if __name__ == "__main__":
    global period
    today = datetime.date.today()
    weekday = today.weekday()
    day = today.day
    month = today.month

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
    print('process end.')


