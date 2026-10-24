"""Compare an offline render with the original supplied artboard, without posting."""

import argparse
import datetime
import json
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ranking_image import FONTS, render_ranking  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, choices=(6, 10), default=10)
    parser.add_argument("--output", type=Path, default=ROOT / "preview-comparison.png")
    args = parser.parse_args()
    fixtures = ROOT / "tests/fixtures"
    data = json.loads((fixtures / "chart.json").read_text(encoding="utf-8"))["toptracks"]["track"]
    with tempfile.TemporaryDirectory(dir=args.output.resolve().parent) as temp:
        output = Path(temp) / "ranking.png"
        render_ranking(data[: args.count], output, "7day", datetime.date(2026, 7, 26), "[USERNAME]")
        with Image.open(output) as rendered, Image.open(fixtures / f"reference_chart_{args.count}.png") as source:
            actual, reference = rendered.convert("RGB"), source.convert("RGB")
    difference = ImageChops.difference(reference, actual)
    means = ImageStat.Stat(difference).mean
    grid = Image.new("RGB", (1200, 840), "#EEF1F6")
    draw = ImageDraw.Draw(grid)
    face = ImageFont.truetype(str(FONTS / "ZenMaruGothic-Bold.ttf"), 16)
    for column, (label, image) in enumerate(
        [
            ("参照デザイン", reference),
            ("ローカル生成", actual),
            ("差分（3倍強調）", difference.point(lambda x: min(255, x * 3))),
        ]
    ):
        draw.text((column * 400 + 10, 10), label, fill="#14213D", font=face)
        grid.paste(image.resize((400, 800), Image.Resampling.LANCZOS), (column * 400, 40))
    grid.save(args.output)
    print(json.dumps({"count": args.count, "mean_rgb_error": means, "limit": 2.2, "pass": max(means) < 2.2}))
    print(args.output.resolve())
    return 0 if max(means) < 2.2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
