"""Create a function ZIP locally, including the renderer and licensed fonts. No AWS calls."""

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(output):
    files = [ROOT / "main.py", ROOT / "ranking_image.py"]
    files.extend(sorted((ROOT / "assets/fonts").glob("*")))
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    build(ROOT / "function.zip")
