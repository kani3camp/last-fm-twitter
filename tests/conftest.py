"""
テスト実行前に main を import しても KeyError にならないよう、
conftest はテストより先に読み込まれるためここで環境変数を設定する。
"""
import os

os.environ.setdefault("LASTFM_API_KEY", "dummy_for_test")
os.environ.setdefault("DISCORD_WEBHOOK_URL", "https://example.com/dummy")

# 画像テストで使うフォント（main.py の FONT1〜FONT5 と同期）
REQUIRED_FONTS = [
    "fonts/azuki.ttf",
    "fonts/Ronde-B_square.otf",
    "fonts/851letrogo_007.ttf",
    "fonts/logotypejp_mp_b_1.1.ttf",
    "fonts/logotypejp_mp_m_1.1.ttf",
]


def fonts_available() -> bool:
    """画像テストに必要な fonts/ がすべて存在するか。"""
    return all(os.path.isfile(p) for p in REQUIRED_FONTS)
