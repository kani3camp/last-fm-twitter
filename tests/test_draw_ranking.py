"""
画像処理のローカルテスト。API はモック（fixture JSON）、画像は実生成し正解 PNG と厳密比較する。
実行には fonts/ に FONT1〜FONT5 を配置すること。
"""
import json
from pathlib import Path

import pytest
from PIL import Image, ImageChops

# conftest で env を設定した後に import
import main

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
EXPECTED_IMAGE = FIXTURES_DIR / "expected_ranking_7day.png"
# テスト用に固定（正解画像生成時と同じ値にすること）
FIXED_THEME_COLOR = (100, 150, 200)
FIXED_DATE_STR = "2025-01-12"


@pytest.fixture
def fixture_data():
    with open(FIXTURES_DIR / "lastfm_toptracks.json", encoding="utf-8") as f:
        return json.load(f)


def test_draw_ranking_img_matches_expected(fixture_data, tmp_path, monkeypatch, fonts_available):
    """固定データ・色・日付で画像を生成し、正解 PNG とピクセル一致するか検証する。"""
    if not fonts_available:
        pytest.skip("画像テストには fonts/ に FONT1〜FONT5 を配置してください")

    if not EXPECTED_IMAGE.exists():
        pytest.skip(
            f"正解画像がありません: {EXPECTED_IMAGE}。"
            "scripts/generate_expected_image.py で生成してから再実行してください。"
        )

    monkeypatch.setattr(main, "period", main.Period.SEVEN_DAYS)
    monkeypatch.setattr(main, "today", __parse_date(FIXED_DATE_STR))

    out_path = tmp_path / "out.png"
    main.draw_ranking_img(
        fixture_data,
        str(out_path),
        theme_color_override=FIXED_THEME_COLOR,
    )

    with Image.open(EXPECTED_IMAGE) as expected, Image.open(out_path) as actual:
        expected_rgb = expected.convert("RGB")
        actual_rgb = actual.convert("RGB")
        diff = ImageChops.difference(expected_rgb, actual_rgb)
        extrema = diff.getextrema()
        max_diff = max(max(p) for p in extrema)
    assert max_diff == 0, (
        f"生成画像が正解と一致しません（最大差分: {max_diff}）。"
        "レイアウトを変えた場合は scripts/generate_expected_image.py で正解画像を更新してください。"
    )


def __parse_date(s: str):
    import datetime

    return datetime.datetime.strptime(s, "%Y-%m-%d").date()
