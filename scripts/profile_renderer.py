"""Offline Lambda-handler smoke test and peak RSS measurement inside a Linux container."""

import argparse
import json
import os
import platform
import resource
import sys
import time
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["LASTFM_API_KEY"] = "offline-profile"
os.environ["DISCORD_WEBHOOK_URL"] = "https://example.invalid/offline-profile"

import main as bot  # noqa: E402
import ranking_image  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale", type=int, choices=(2, 3), default=ranking_image.SCALE)
    args = parser.parse_args()
    ranking_image.SCALE = args.scale
    data = json.loads((ROOT / "tests/fixtures/chart.json").read_text(encoding="utf-8"))
    started = time.monotonic()
    cases = []
    for period in ("7day", "1month", "12month"):
        for count in (1, 6, 10):
            fixture = {"toptracks": {"track": data["toptracks"]["track"][:count]}}
            with (
                patch.object(bot, "get_last_fm_tracks", return_value=fixture),
                patch.object(bot, "send_image_to_discord") as posted,
                patch.object(bot, "send_message_to_discord") as empty,
                patch("urllib.request.urlopen", side_effect=AssertionError("Network forbidden")),
                patch("requests.post", side_effect=AssertionError("Network forbidden")),
            ):
                bot.lambda_handler({"period": period}, None)
            posted.assert_called_once()
            empty.assert_not_called()
            with Image.open(bot.LAMBDA_IMG_PATH) as image:
                assert image.size == ranking_image.SIZE
                image.load()
            cases.append(
                {"period": period, "count": count, "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
            )
    result = {
        "architecture": platform.machine(),
        "scale": ranking_image.SCALE,
        "cases": cases,
        "seconds": time.monotonic() - started,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    for name in ("memory.max", "memory.peak", "memory.events"):
        path = Path("/sys/fs/cgroup") / name
        if path.exists():
            result[name] = path.read_text().strip()
    for name in ("memory.limit_in_bytes", "memory.max_usage_in_bytes", "memory.failcnt"):
        path = Path("/sys/fs/cgroup/memory") / name
        if path.exists():
            result[name] = path.read_text().strip()
    print(json.dumps(result))


if __name__ == "__main__":
    main()
