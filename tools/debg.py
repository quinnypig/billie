#!/usr/bin/env python3
"""Knock out gpt-image's baked light background to true alpha.

gpt-image-2 renders "transparent" as an opaque light-gray checkerboard (or a
flat light matte). We reclaim real transparency by flood-filling the light,
low-saturation background inward from the image border. Because the fill only
spreads across background-colored pixels, detached colorful elements (confetti)
and interior light details (a candle flame) are left untouched.

The result is cropped to its content and, if a max-pixel cap is given, scaled
so its longest side fits — keeping seasonal PNGs in family with their siblings
(~1500px) so the Kitty graphics transmission stays lean.

Usage: uv run --with pillow python debg.py in.png out.png [max_px]
"""

from __future__ import annotations

import sys
from collections import deque

from PIL import Image

SPREAD_MAX = 26  # max channel spread to count as near-gray background
LIGHT_MIN = 165  # min channel value; darker pixels are art (outlines), not bg


def is_bg(px: tuple[int, int, int]) -> bool:
    r, g, b = px[0], px[1], px[2]
    return (max(r, g, b) - min(r, g, b)) <= SPREAD_MAX and min(r, g, b) >= LIGHT_MIN


def debg(path_in: str, path_out: str, max_px: int | None = None) -> None:
    im = Image.open(path_in).convert("RGBA")
    w, h = im.size
    px = im.load()
    bg = bytearray(w * h)  # 1 == background
    q: deque[tuple[int, int]] = deque()

    def seed(x: int, y: int) -> None:
        i = y * w + x
        if not bg[i] and is_bg(px[x, y]):
            bg[i] = 1
            q.append((x, y))

    for x in range(w):
        seed(x, 0)
        seed(x, h - 1)
    for y in range(h):
        seed(0, y)
        seed(w - 1, y)

    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                seed(nx, ny)

    cleared = 0
    for y in range(h):
        row = y * w
        for x in range(w):
            if bg[row + x]:
                r, g, b, _ = px[x, y]
                px[x, y] = (r, g, b, 0)
                cleared += 1

    bbox = im.split()[3].getbbox()
    if bbox:
        im = im.crop(bbox)
    if max_px and max(im.size) > max_px:
        cw, ch = im.size
        scale = max_px / max(cw, ch)
        im = im.resize((round(cw * scale), round(ch * scale)), Image.LANCZOS)

    im.save(path_out, optimize=True)
    pct = 100 * cleared // (w * h)
    print(f"wrote {path_out}: cleared {cleared} bg px ({pct}%), sized {im.size}")


if __name__ == "__main__":
    cap = int(sys.argv[3]) if len(sys.argv) > 3 else None
    debg(sys.argv[1], sys.argv[2], cap)
