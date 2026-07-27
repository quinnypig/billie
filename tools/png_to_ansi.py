#!/usr/bin/env python3
"""Convert a transparent PNG into half-block, 256-color ANSI art.

Matches Billie's committed seasonal .txt art: ~60 columns wide, lower-half
(▄) / upper-half (▀) block glyphs, foreground = bottom pixel, background =
top pixel. Transparent pixels leave the terminal's default background so
there is no dark-mode halo on the edges.

Usage: uv run --with pillow python png_to_ansi.py in.png out.txt [cols]
"""

from __future__ import annotations

import sys

from PIL import Image

ALPHA_CUTOFF = 128


def _build_palette() -> list[tuple[int, int, int]]:
    """The 256 xterm colors as RGB, indices 16..255 (skip the 16 ANSI base)."""
    pal: dict[int, tuple[int, int, int]] = {}
    levels = [0, 95, 135, 175, 215, 255]
    for i in range(216):
        r, g, b = i // 36, (i // 6) % 6, i % 6
        pal[16 + i] = (levels[r], levels[g], levels[b])
    for i in range(24):
        v = 8 + 10 * i
        pal[232 + i] = (v, v, v)
    return [(idx, rgb) for idx, rgb in pal.items()]


_PALETTE = _build_palette()


def rgb_to_256(r: int, g: int, b: int) -> int:
    """Nearest xterm-256 color (full-palette Euclidean search, cube + grays)."""
    best_idx, best_d = 16, 1 << 30
    for idx, (pr, pg, pb) in _PALETTE:
        d = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2
        if d < best_d:
            best_d, best_idx = d, idx
    return best_idx


def convert(path_in: str, path_out: str, cols: int = 60) -> None:
    im = Image.open(path_in).convert("RGBA")
    bbox = im.split()[3].getbbox()
    if bbox:
        im = im.crop(bbox)
    w, h = im.size
    rows2 = round(cols * h / w)
    rows2 += rows2 % 2  # even so it splits into whole character rows
    im = im.resize((cols, rows2), Image.LANCZOS)
    px = im.load()

    out = []
    for cy in range(0, rows2, 2):
        line = []
        cur = None  # (fg, bg) currently set, None means reset
        for x in range(cols):
            tr, tg, tb, ta = px[x, cy]
            br, bg_, bb, ba = px[x, cy + 1]
            top = ta >= ALPHA_CUTOFF
            bot = ba >= ALPHA_CUTOFF
            if not top and not bot:
                if cur is not None:
                    line.append("\x1b[0m")
                    cur = None
                line.append(" ")
            elif top and bot:
                fg, bg = rgb_to_256(br, bg_, bb), rgb_to_256(tr, tg, tb)
                if cur != (fg, bg):
                    line.append(f"\x1b[38;5;{fg}m\x1b[48;5;{bg}m")
                    cur = (fg, bg)
                line.append("▄")  # ▄ fg=bottom over bg=top
            elif bot:  # bottom only -> lower half on default bg
                fg = rgb_to_256(br, bg_, bb)
                if cur != (fg, None):
                    line.append(f"\x1b[0m\x1b[38;5;{fg}m")
                    cur = (fg, None)
                line.append("▄")  # ▄
            else:  # top only -> upper half on default bg
                fg = rgb_to_256(tr, tg, tb)
                if cur != (fg, None):
                    line.append(f"\x1b[0m\x1b[38;5;{fg}m")
                    cur = (fg, None)
                line.append("▀")  # ▀
        line.append("\x1b[0m")
        out.append("".join(line))
    with open(path_out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"wrote {path_out}: {cols} cols x {rows2 // 2} rows")


if __name__ == "__main__":
    args = sys.argv[1:]
    cols = int(args[2]) if len(args) > 2 else 60
    convert(args[0], args[1], cols)
