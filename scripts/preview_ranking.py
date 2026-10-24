"""Render fixture data locally without importing the bot, reading .env, or posting."""

import argparse
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ranking_image import render_ranking  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "tests/fixtures/chart.json")
    parser.add_argument("--count", type=int, choices=range(1, 11), default=10)
    parser.add_argument("--period", choices=("7day", "1month", "12month"), default="7day")
    parser.add_argument("--date", type=datetime.date.fromisoformat, default=datetime.date(2026, 7, 26))
    parser.add_argument("--output", type=Path, default=ROOT / "preview.png")
    parser.add_argument("--username", default="SoraraP")
    args = parser.parse_args()
    with args.data.open(encoding="utf-8") as source:
        tracks = json.load(source)["toptracks"].get("track") or []
    if isinstance(tracks, dict):
        tracks = [tracks]
    tracks = [track for track in tracks if int(track["playcount"]) > 0][: args.count]
    render_ranking(tracks, args.output, args.period, args.date, args.username)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
