"""再生履歴が10件未満の場合と0件の場合の処理テスト。"""

import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("LASTFM_API_KEY", "test-lastfm-api-key")
os.environ.setdefault("DISCORD_WEBHOOK_URL", "https://example.invalid/webhook")

import main  # noqa: E402


def make_data(count):
    return {
        "toptracks": {
            "track": [
                {
                    "name": f"Track {i}",
                    "artist": {"name": f"Artist {i}"},
                    "playcount": str(count - i + 1),
                }
                for i in range(1, count + 1)
            ]
        }
    }


class PartialRankingTests(unittest.TestCase):
    def setUp(self):
        period = patch.object(main, "period", main.Period.SEVEN_DAYS, create=True)
        period.start()
        self.addCleanup(period.stop)

    def test_no_tracks_sends_discord_message_without_image_or_font_download(self):
        with (
            patch.object(main, "is_lambda", True),
            patch.object(main, "get_last_fm_tracks", return_value=make_data(0)),
            patch.object(main, "send_message_to_discord") as send_text,
            patch.object(main, "send_image_to_discord") as send_image,
            patch.object(main, "draw_ranking_img") as draw_image,
            patch.object(main, "download_s3_ttf") as download_font,
        ):
            main.main()

        send_text.assert_called_once_with(
            "そららPが今週聞いた曲ランキング\n再生履歴が0件のため、ランキング画像は作成しませんでした。",
            main.DISCORD_WEBHOOK_URL,
        )
        send_image.assert_not_called()
        draw_image.assert_not_called()
        download_font.assert_not_called()

    def test_only_unplayed_tracks_are_treated_as_empty(self):
        data = make_data(2)
        for track in data["toptracks"]["track"]:
            track["playcount"] = "0"

        with (
            patch.object(main, "get_last_fm_tracks", return_value=data),
            patch.object(main, "send_message_to_discord") as send_text,
            patch.object(main, "draw_ranking_img") as draw_image,
            patch.object(main, "send_image_to_discord") as send_image,
        ):
            main.main()

        send_text.assert_called_once()
        draw_image.assert_not_called()
        send_image.assert_not_called()

    def test_one_to_ten_tracks_continue_to_image_posting(self):
        for count in (1, 3, 9, 10):
            with self.subTest(track_count=count):
                data = make_data(count)
                with (
                    patch.object(main, "is_lambda", False),
                    patch.object(main, "get_last_fm_tracks", return_value=data),
                    patch.object(main, "send_message_to_discord") as send_text,
                    patch.object(main, "draw_ranking_img") as draw_image,
                    patch.object(main, "send_image_to_discord") as send_image,
                ):
                    main.main()

                draw_image.assert_called_once_with(data, img_path=main.LOCAL_IMG_PATH)
                send_image.assert_called_once_with(
                    "そららPが今週聞いた曲ランキング", main.DISCORD_WEBHOOK_URL, main.LOCAL_IMG_PATH
                )
                send_text.assert_not_called()

    def test_filter_unplayed_tracks_and_limit_to_ten(self):
        data = make_data(14)
        data["toptracks"]["track"][0]["playcount"] = "0"
        data["toptracks"]["track"][1]["playcount"] = "0"

        tracks = main.select_ranked_tracks(data)

        self.assertEqual(len(tracks), 10)
        self.assertEqual(tracks[0]["name"], "Track 3")
        self.assertEqual(tracks[-1]["name"], "Track 12")

    def test_single_track_object_is_supported(self):
        track = make_data(1)["toptracks"]["track"][0]
        self.assertEqual(main.select_ranked_tracks({"toptracks": {"track": track}}), [track])

    def test_short_rankings_have_compact_images(self):
        for count, expected_height in ((1, 515), (3, 880), (9, 1977), (10, 2160)):
            with self.subTest(track_count=count):
                image = Mock()
                with (
                    patch.object(main, "is_lambda", False),
                    patch.object(main.Image, "new", return_value=image) as new_image,
                    patch.object(main.ImageDraw, "Draw", return_value=Mock()),
                    patch.object(main.ImageFont, "truetype", return_value=Mock()),
                    patch.object(main, "draw_width", return_value=10),
                    patch.object(main, "draw_height", return_value=10),
                    patch.object(main, "draw_table") as draw_table,
                ):
                    main.draw_ranking_img(make_data(count), "test-ranking.jpg")

                self.assertEqual(new_image.call_args.args[1], (1080, expected_height))
                self.assertEqual(len(draw_table.call_args.args[2]), count)
                image.save.assert_called_once_with("test-ranking.jpg")

    def test_partial_table_renders_only_existing_ranks(self):
        draw = Mock()
        main.theme_color = (100, 150, 200)
        with (
            patch.object(main.ImageFont, "truetype", return_value=Mock()),
            patch.object(main, "draw_width", return_value=10),
        ):
            main.draw_table(draw, (1080, 515), main.select_ranked_tracks(make_data(1)))

        drawn_texts = [call.kwargs["text"] for call in draw.text.call_args_list]
        self.assertIn("1", drawn_texts)
        self.assertIn("Track 1", drawn_texts)
        self.assertIn("Artist 1", drawn_texts)
        self.assertNotIn("2", drawn_texts)

    def test_zero_tracks_cannot_be_rendered_directly(self):
        with patch.object(main.Image, "new") as create_image:
            with self.assertRaises(ValueError):
                main.draw_ranking_img(make_data(0), "test-ranking.jpg")

        create_image.assert_not_called()

    def test_discord_text_message_contains_no_file(self):
        with patch.object(main.requests, "post") as post:
            main.send_message_to_discord("履歴なし", "https://example.invalid/webhook")

        post.assert_called_once_with(
            "https://example.invalid/webhook", json={"content": "履歴なし"}, timeout=30
        )
        post.return_value.raise_for_status.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
