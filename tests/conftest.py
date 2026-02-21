"""
テスト実行前に main を import しても KeyError にならないよう、
conftest はテストより先に読み込まれるためここで環境変数を設定する。
"""
import os
from pathlib import Path

import pytest

os.environ.setdefault("LASTFM_API_KEY", "dummy_for_test")
os.environ.setdefault("DISCORD_WEBHOOK_URL", "https://example.com/dummy")

# プロジェクトルート基準のフォントパス（main.py の FONT1〜FONT5 と同期）
_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_FONTS = [
    _ROOT / "fonts" / "azuki.ttf",
    _ROOT / "fonts" / "Ronde-B_square.otf",
    _ROOT / "fonts" / "851letrogo_007.ttf",
    _ROOT / "fonts" / "logotypejp_mp_b_1.1.ttf",
    _ROOT / "fonts" / "logotypejp_mp_m_1.1.ttf",
]


def _fonts_available() -> bool:
    """画像テストに必要な fonts/ がすべて存在するか。"""
    return all(p.is_file() for p in REQUIRED_FONTS)


@pytest.fixture
def fonts_available():
    """Expose font check as a fixture so tests don't import conftest directly."""
    return _fonts_available()
