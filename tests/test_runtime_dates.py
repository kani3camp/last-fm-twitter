"""JST dates and period wording must be correct across warm Lambda invocations."""

import datetime
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("LASTFM_API_KEY", "offline-test")
os.environ.setdefault("DISCORD_WEBHOOK_URL", "https://example.invalid/offline-test")

import main  # noqa: E402


class RuntimeDateTests(unittest.TestCase):
    def test_current_date_uses_jst_across_the_utc_day_boundary(self):
        after_midnight = datetime.datetime(2026, 7, 26, 0, 1, tzinfo=main.JST)
        with patch.object(main.datetime, "datetime") as clock:
            clock.now.return_value = after_midnight
            self.assertEqual(main.current_date(), datetime.date(2026, 7, 26))
            clock.now.assert_called_once_with(main.JST)

    def test_forced_warm_invocations_render_each_invocations_date(self):
        days = [datetime.date(2026, 7, 26), datetime.date(2026, 7, 27)]
        fixture = {"toptracks": {"track": [{"name": "Track", "artist": {"name": "Artist"}, "playcount": "1"}]}}
        with (
            patch.object(main, "today", None),
            patch.object(main, "is_lambda", False),
            patch.object(main, "period", None),
            patch.object(main, "current_date", side_effect=days),
            patch.object(main, "get_last_fm_tracks", return_value=fixture),
            patch.object(main, "render_ranking") as rendered,
            patch.object(main, "send_image_to_discord"),
        ):
            for _ in days:
                main.lambda_handler({"period": "7day"}, None)
        self.assertEqual([call.args[3] for call in rendered.call_args_list], days)

    def test_scheduled_warm_invocations_recompute_the_month_boundary(self):
        days = [datetime.date(2026, 7, 31), datetime.date(2026, 8, 1)]
        observed = []
        with (
            patch.object(main, "today", None),
            patch.object(main, "is_lambda", False),
            patch.object(main, "period", None),
            patch.object(main, "current_date", side_effect=days) as clock,
            patch.object(main, "main", side_effect=lambda: observed.append((main.period, main.today))),
        ):
            main.lambda_handler({}, None)
            main.lambda_handler({}, None)
        self.assertEqual(clock.call_count, 2)
        self.assertEqual(observed, [(main.Period.ONE_MONTH, days[1])])

    def test_cli_scheduler_refreshes_the_date_on_each_run(self):
        days = [datetime.date(2026, 7, 25), datetime.date(2026, 7, 26)]
        observed = []
        with (
            patch.object(main, "today", None),
            patch.object(main, "period", None),
            patch.object(main, "current_date", side_effect=days),
            patch.object(main, "main", side_effect=lambda: observed.append((main.period, main.today))),
        ):
            main.pre_main()
            main.pre_main()
        self.assertEqual(observed, [(main.Period.SEVEN_DAYS, days[1])])

    def test_post_text_and_image_share_the_same_period_wording(self):
        for period, title in (
            ("7day", "過去7日間に聴いた曲"),
            ("1month", "過去1か月に聴いた曲"),
            ("12month", "過去12か月に聴いた曲"),
        ):
            with self.subTest(period=period), patch.object(main, "period", period):
                self.assertEqual(main.initial_message_str(), f"そららPが{title}ランキング")


if __name__ == "__main__":
    unittest.main()
