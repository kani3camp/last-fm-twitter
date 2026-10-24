"""Comparison regions for the original artboards, whose old period labels were corrected."""

from PIL import ImageChops, ImageDraw

# These regions contain intentionally replaced period/date labels and the title marker.
# All ranking content, stats, card geometry, and the first title line remain compared.
CHANGED_PERIOD_REGIONS = ((56, 56, 944, 100), (56, 197, 944, 313), (282, 443, 904, 483))


def reference_difference(actual, reference):
    difference = ImageChops.difference(actual.convert("RGB"), reference.convert("RGB"))
    draw = ImageDraw.Draw(difference)
    for left, top, right, bottom in CHANGED_PERIOD_REGIONS:
        draw.rectangle((left, top, right - 1, bottom - 1), fill=0)
    return difference
