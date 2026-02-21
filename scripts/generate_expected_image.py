"""
正解画像を 1 枚生成し、tests/fixtures/expected_ranking_7day.png に保存する。
レイアウトやフォントを変えたあと、このスクリプトを再実行して正解画像を更新し、コミットすること。

実行: プロジェクトルートで uv run python scripts/generate_expected_image.py
"""

import json
import os
import sys
from pathlib import Path

# プロジェクトルートを path に追加
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("LASTFM_API_KEY", "dummy")
os.environ.setdefault("DISCORD_WEBHOOK_URL", "https://example.com/dummy")

import main  # noqa: E402 -- env を設定したあとで import する必要がある

FIXTURES_DIR = ROOT / "tests" / "fixtures"
OUT_PATH = FIXTURES_DIR / "expected_ranking_7day.png"
FIXED_THEME_COLOR = (100, 150, 200)
FIXED_DATE_STR = "2025-01-12"


def main_run():
    with open(FIXTURES_DIR / "lastfm_toptracks.json", encoding="utf-8") as f:
        data = json.load(f)

    main.period = main.Period.SEVEN_DAYS
    main.today = __parse_date(FIXED_DATE_STR)

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    main.draw_ranking_img(data, str(OUT_PATH), theme_color_override=FIXED_THEME_COLOR)
    print(f"Saved: {OUT_PATH}")


def __parse_date(s: str):
    import datetime

    return datetime.datetime.strptime(s, "%Y-%m-%d").date()


if __name__ == "__main__":
    main_run()
