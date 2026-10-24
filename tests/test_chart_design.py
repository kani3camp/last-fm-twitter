"""Semantic layout contracts and actual offline image regression tests."""

import datetime
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageChops, ImageStat

from ranking_image import (
    SCALE,
    Canvas,
    ellipsize,
    font,
    period_labels,
    render_ranking,
    wrap_title,
)
from scripts.build_function import build

FIXTURES = Path(__file__).parent / "fixtures"
DAY = datetime.date(2026, 7, 26)


def tracks():
    return json.loads((FIXTURES / "chart.json").read_text(encoding="utf-8"))["toptracks"]["track"]


class ChartDesignTests(unittest.TestCase):
    def test_reference_artboards_match_with_a_small_rasterization_tolerance(self):
        for count in (10, 6):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / "ranking.png"
                render_ranking(tracks()[:count], output, "7day", DAY, username="[USERNAME]")
                with Image.open(output) as actual, Image.open(FIXTURES / f"reference_chart_{count}.png") as reference:
                    difference = ImageChops.difference(actual, reference.convert("RGB"))
                    # Chromium and FreeType rasterize glyph edges differently. Keep the
                    # mean error below 0.87% per channel, alongside semantic geometry tests.
                    self.assertLess(max(ImageStat.Stat(difference).mean), 2.2)

    def test_date_badge_uses_the_reference_kerning(self):
        self.assertAlmostEqual(font(22, 600, True).getlength("2026.07.20 — 07.26") / SCALE, 272.9625, delta=0.1)

    def test_one_percent_bar_does_not_overstate_its_share(self):
        canvas = Canvas()
        canvas.bar(10, 10, 110, 8, 0.01)
        pixels = [canvas.image.getpixel((x, 14 * SCALE)) for x in range(10 * SCALE, 120 * SCALE)]
        filled = sum(pixel == (109, 53, 214) for pixel in pixels)
        self.assertLessEqual(filled, 4)  # 1.1 logical pixels at 3×, with subpixel rounding.
        self.assertGreater(filled, 0)

    def test_six_track_empty_slots_match_reference_flex_positions(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(Canvas, "placeholder", autospec=True) as empty:
            render_ranking(tracks()[:6], Path(temp) / "ranking.png", "7day", DAY)
        # Measured from the supplied ChartShort.dc.html's rendered artboard.
        expected = [(7, 1503.6875, 91.5875), (8, 1605.275, 91.575), (9, 1706.85, 91.575), (10, 1808.425, 91.575)]
        for call, (rank, y, height) in zip(empty.call_args_list, expected, strict=True):
            self.assertEqual(call.args[1], rank)
            self.assertAlmostEqual(call.args[2], y, delta=0.04)
            self.assertAlmostEqual(call.args[3], height, delta=0.04)

    def test_ten_and_six_track_designs_match_reviewed_images(self):
        for count in (10, 6):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / "ranking.png"
                render_ranking(tracks()[:count], output, "7day", DAY)
                with Image.open(output) as actual, Image.open(FIXTURES / f"chart_{count}.png") as expected:
                    self.assertEqual(actual.size, (1000, 2000))
                    self.assertIsNone(ImageChops.difference(actual, expected).getbbox())

    def test_empty_slots_do_not_claim_a_song_artist_or_play_count(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(Canvas, "placeholder", autospec=True) as empty:
            render_ranking(tracks()[:6], Path(temp) / "ranking.png", "7day", DAY)
        self.assertEqual([call.args[1] for call in empty.call_args_list], [7, 8, 9, 10])

    def test_single_track_keeps_all_remaining_rank_slots(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(Canvas, "placeholder", autospec=True) as empty:
            render_ranking(tracks()[:1], Path(temp) / "ranking.png", "7day", DAY)
        self.assertEqual([call.args[1] for call in empty.call_args_list], list(range(2, 11)))

    def test_stats_are_for_the_displayed_top_ten_only(self):
        data = tracks()
        data.append({"name": "Not shown", "artist": {"name": "Not counted"}, "playcount": "100"})
        with tempfile.TemporaryDirectory() as temp, patch.object(Canvas, "text", autospec=True) as text:
            render_ranking(data, Path(temp) / "ranking.png", "7day", DAY)
        stats = [call.args[1] for call in text.call_args_list if call.args[3] == 327.2]
        self.assertEqual(stats, ["63", "10", "7"])
        self.assertNotIn("Not shown", [call.args[1] for call in text.call_args_list])

    def test_feature_credits_stay_in_the_title(self):
        title = tracks()[0]["name"]
        lines = wrap_title(title, font(56), 622)
        self.assertEqual(lines, ["ミッドナイト・サイダー", "(feat. 春野ことり)"])

    def test_long_titles_are_clamped_and_fit_their_column(self):
        for size, width, max_lines in ((56, 622, 2), (34, 480, 2), (32, 622, 1)):
            for value in ("長い曲名" * 60, "Supercalifragilisticexpialidocious" * 8, "長い曲名\nfeat. Artist " * 30):
                with self.subTest(size=size, value=value):
                    face = font(size)
                    lines = wrap_title(value, face, width, max_lines)
                    self.assertLessEqual(len(lines), max_lines)
                    self.assertTrue(lines[-1].endswith("…"))
                    for line in lines:
                        self.assertLessEqual(face.getlength(line), width * SCALE)

    def test_long_artist_is_ellipsized_without_a_newline(self):
        value = ellipsize("長いアーティスト名\n" * 50, font(30, 700), 622)
        self.assertNotIn("\n", value)
        self.assertTrue(value.endswith("…"))
        self.assertLessEqual(font(30, 700).getlength(value), 622 * SCALE)

    def test_period_headers_and_dates_match_api_window(self):
        cases = [
            ("7day", DAY, ("WEEKLY TOP 10", "今週聴いた曲", "NO.1 THIS WEEK", "2026.07.20 — 07.26")),
            (
                "1month",
                datetime.date(2026, 8, 1),
                ("MONTHLY TOP 10", "先月聴いた曲", "NO.1 THIS MONTH", "AS OF 2026.08.01"),
            ),
            (
                "1month",
                datetime.date(2024, 3, 31),
                ("MONTHLY TOP 10", "先月聴いた曲", "NO.1 THIS MONTH", "AS OF 2024.03.31"),
            ),
            (
                "12month",
                datetime.date(2026, 12, 30),
                ("YEARLY TOP 10", "今年聴いた曲", "NO.1 THIS YEAR", "AS OF 2026.12.30"),
            ),
        ]
        for period, day, expected in cases:
            with self.subTest(period=period, day=day):
                self.assertEqual(period_labels(period, day), expected)

    def test_long_top_titles_and_large_counts_stay_inside_the_canvas(self):
        data = tracks()
        for track in data:
            track["name"] = "長いタイトル (feat. ゲスト) " * 20
            track["artist"]["name"] = "長いアーティスト" * 30
            track["playcount"] = "1234567"
        original = Canvas.text
        calls = []

        def record(canvas, value, x, y, size, *args, **kwargs):
            calls.append((value, x, y, size, kwargs.get("weight", args[1] if len(args) > 1 else 900)))
            return original(canvas, value, x, y, size, *args, **kwargs)

        with tempfile.TemporaryDirectory() as temp, patch.object(Canvas, "text", record):
            render_ranking(data, Path(temp) / "large.png", "12month", DAY)
        for value, x, y, size, weight in calls:
            if value.startswith("NO.1") or "TOP 10" in value or "—" in value or value.isdigit():
                continue  # Latin fonts and dynamically scaled count badges have their own geometry.
            with self.subTest(value=value):
                self.assertGreaterEqual(x, 0)
                self.assertLessEqual(x + font(size, weight).getlength(value) / SCALE, 945)
                self.assertGreaterEqual(y, 0)
                self.assertLess(y + size, 2000)

    def test_function_archive_contains_renderer_fonts_and_no_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "function.zip"
            build(output)
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
        self.assertEqual(
            names,
            {
                "main.py",
                "ranking_image.py",
                "assets/fonts/ZenMaruGothic-Black.ttf",
                "assets/fonts/ZenMaruGothic-Bold.ttf",
                "assets/fonts/Unbounded.ttf",
                "assets/fonts/OFL-ZenMaruGothic.txt",
                "assets/fonts/OFL-Unbounded.txt",
                "assets/fonts/README.md",
            },
        )


if __name__ == "__main__":
    unittest.main()
