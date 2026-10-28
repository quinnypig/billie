#!/usr/bin/env python3
"""Build Kitty-graphics animation frames for the seasonal Billies.

Terminals that speak the Kitty animation protocol (Kitty, Ghostty 1.4+) play
the frames themselves after billie exits, so an animation is just extra data
sent alongside the still PNG. To keep that data small, each frame ships as a
*patch*: the rectangle that differs from the root image, plus its offset. The
terminal composes it onto the root frame (c=1) with plain replacement (X=1).

Terminals keep every frame as a full decoded image (about 3.6 MB at 1000px),
so each animation sticks to one effect and a handful of frames.

Each animated PNG is listed in animations.toml (next to this script) with an
effect and the pixel boxes it works on. Output, next to the PNG:

- billie-<season>-anim<N>.png  one patch per extra frame
- billie-<season>.anim.json    offsets and frame gaps, read by billie at runtime

Subcommands:

  build [STEM ...] [--preview DIR]
      Regenerate every animation in animations.toml, or just the named stems
      (e.g. billie-birthday). --preview writes an animated GIF of each.

  pack IN.png FRAME.png [FRAME.png ...] [--gap MS] [--preview out.gif]
      Package hand-made full-size frames (same size as IN.png).

Usage: uv run --with pillow python animate.py <subcommand> ...
"""

from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import subprocess
from collections import deque
from pathlib import Path
from statistics import median

import tomllib
from PIL import Image, ImageChops

CONFIG = Path(__file__).with_name("animations.toml")
STATIC = Path(__file__).resolve().parents[1] / "src" / "billie" / "static"

DARK_MAX = 110  # max channel at or below this counts as outline-dark
LIGHT_MIN = 175  # min channel at or above this counts as white-ish
OUTLINE = (50, 46, 46, 255)  # fallback lid-line color


# --- pixel-set helpers ------------------------------------------------------


def _all(crop: Image.Image) -> list[tuple[int, int]]:
    w, h = crop.size
    return [(x, y) for y in range(h) for x in range(w)]


def _neighbors(p, w, h):
    x, y = p
    for nb in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if 0 <= nb[0] < w and 0 <= nb[1] < h:
            yield nb


def _components(pixels: set, w: int, h: int) -> list[set]:
    seen, comps = set(), []
    for start in pixels:
        if start in seen:
            continue
        comp, queue = {start}, deque([start])
        seen.add(start)
        while queue:
            for nb in _neighbors(queue.popleft(), w, h):
                if nb in pixels and nb not in seen:
                    seen.add(nb)
                    comp.add(nb)
                    queue.append(nb)
        comps.append(comp)
    return comps


def _interior(pixels: set, w: int, h: int) -> set:
    """Components that don't touch the crop border (the crop's own object)."""
    keep = set()
    for comp in _components(pixels, w, h):
        if not any(x in (0, w - 1) or y in (0, h - 1) for x, y in comp):
            keep |= comp
    return keep


def _span_fill(pixels: set) -> set:
    """Fill each row and column between its extremes: closes holes and gaps."""
    rows, cols = {}, {}
    for x, y in pixels:
        lo, hi = rows.get(y, (x, x))
        rows[y] = (min(lo, x), max(hi, x))
        lo, hi = cols.get(x, (y, y))
        cols[x] = (min(lo, y), max(hi, y))
    out = {(x, y) for y, (a, b) in rows.items() for x in range(a, b + 1)}
    out |= {(x, y) for x, (a, b) in cols.items() for y in range(a, b + 1)}
    return out


def _grow(pixels: set, steps: int, w: int, h: int) -> set:
    out = set(pixels)
    for _ in range(steps):
        out |= {nb for p in out for nb in _neighbors(p, w, h)}
    return out


def _shrink(pixels: set, steps: int, w: int, h: int) -> set:
    out = set(pixels)
    for _ in range(steps):
        out = {p for p in out if all(nb in out for nb in _neighbors(p, w, h))}
    return out


def _median_color(colors: list) -> tuple:
    if not colors:
        return OUTLINE
    return tuple(round(median(c[i] for c in colors)) for i in range(4))


def _inpaint(crop: Image.Image, holes: set) -> Image.Image:
    """Fill holes row by row, blending the nearest kept pixels on each side."""
    out = crop.copy()
    src, dst = crop.load(), out.load()
    w, _ = crop.size
    for x, y in holes:
        left = next((xx for xx in range(x, -1, -1) if (xx, y) not in holes), None)
        right = next((xx for xx in range(x, w) if (xx, y) not in holes), None)
        sides = [s for s in (left, right) if s is not None]
        if not sides:
            continue
        if len(sides) == 1:
            dst[x, y] = src[sides[0], y]
            continue
        t = (x - left) / (right - left)
        a, b = src[left, y], src[right, y]
        dst[x, y] = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(4))
    return out


def _layer(crop: Image.Image, pixels: set) -> Image.Image:
    """The crop, transparent everywhere except `pixels`."""
    alpha = Image.new("L", crop.size, 0)
    src = crop.getchannel("A").load()
    for p in pixels:
        alpha.putpixel(p, src[p])
    out = crop.copy()
    out.putalpha(alpha)
    return out


def _affine(
    sprite: Image.Image,
    scale_x: float,
    scale_y: float,
    sway: float,
    anchor: tuple[float, float],
) -> Image.Image:
    """Scale about `anchor` and shear by `sway` px per px above it.

    Done premultiplied so transparent edges don't drag in stray colors.
    """
    ax, ay = anchor
    a, b = 1 / scale_x, -sway / (scale_x * scale_y)
    e = 1 / scale_y
    out = sprite.convert("RGBa").transform(
        sprite.size,
        Image.Transform.AFFINE,
        (a, b, ax - a * ax - b * ay, 0, e, ay - e * ay),
        resample=Image.Resampling.BILINEAR,
    )
    return out.convert("RGBA")


def _box(spec_box: list[int]) -> tuple[int, int, int, int]:
    x, y, w, h = spec_box
    return x, y, x + w, y + h


def _with(base: Image.Image, pieces: list) -> Image.Image:
    """A copy of base with (image, (x, y)) pieces pasted over it."""
    frame = base.copy()
    for piece, at in pieces:
        frame.paste(piece, at)
    return frame


# --- effects ------------------------------------------------------------------
# Each takes (base, spec) and returns (root_gap, [(frame, gap), ...]). Frame 1
# (the root) is always the untouched art, so every effect starts from rest.

# (x scale, y scale, sway) per flicker frame, and the gap after each.
FLICKER = [
    (0.96, 1.08, 0.07),
    (1.03, 0.90, -0.03),
    (0.95, 1.12, -0.08),
    (1.01, 0.94, 0.04),
    (0.97, 1.05, 0.09),
]
FLICKER_GAPS = [110, 90, 130, 80, 120]


def flicker(base, spec):
    """A candle flame: an orange outline around a lighter core, over a wick."""
    box = _box(spec["box"])
    crop = base.crop(box)
    w, h = crop.size
    px = crop.load()
    orange = {
        p for p in _all(crop) if px[p][0] >= 190 and px[p][1] <= 170 and px[p][2] <= 110
    }
    # Whatever the orange outline encloses is flame; flood the rest from the edge.
    outside = set()
    queue = deque(p for p in _all(crop) if p[0] in (0, w - 1) or p[1] in (0, h - 1))
    queue = deque(p for p in queue if p not in orange)
    outside.update(queue)
    while queue:
        for nb in _neighbors(queue.popleft(), w, h):
            if nb not in outside and nb not in orange:
                outside.add(nb)
                queue.append(nb)
    inside = set(_all(crop)) - outside
    wick = _grow({p for p in inside if max(px[p][:3]) <= DARK_MAX}, 1, w, h)
    flame = _grow(inside, 2, w, h) - wick  # take the anti-aliased fringe too

    background = _inpaint(crop, flame | wick)
    sprite, wick_layer = _layer(crop, flame), _layer(crop, wick)
    xs = [x for x, _ in flame]
    anchor = ((min(xs) + max(xs)) / 2, max(y for _, y in flame))
    frames = []
    for (sx, sy, sway), gap in zip(FLICKER, FLICKER_GAPS):
        piece = Image.alpha_composite(background, _affine(sprite, sx, sy, sway, anchor))
        piece = Image.alpha_composite(piece, wick_layer)
        frames.append((_with(base, [(piece, box[:2])]), gap))
    return 160, frames


def _eyelid(base, eye_box, closed, open_eye):
    """One eye with its lid `closed` (0..1) of the way down."""
    box = _box(eye_box)
    crop = base.crop(box)
    w, h = crop.size
    px = crop.load()
    if open_eye:
        # A white eyeball (pupil and all): span-fill the light pixels.
        opening = _span_fill({p for p in _all(crop) if min(px[p][:3]) >= LIGHT_MIN})
    else:
        # A dark dot: the dark blob that doesn't run off the box.
        dark = {p for p in _all(crop) if max(px[p][:3]) <= DARK_MAX and px[p][3] > 200}
        opening = _span_fill(_interior(dark, w, h))
    if not opening:
        msg = f"no eye found in box {eye_box}"
        raise SystemExit(msg)
    # Take in the soft rim too, or a ghost of the open eye shows through.
    opening = _grow(opening, 1 if open_eye else 2, w, h)

    border = [p for p in _all(crop) if p[0] in (0, w - 1) or p[1] in (0, h - 1)]
    skin = _median_color([px[p] for p in border if max(px[p][:3]) > DARK_MAX])
    line = _median_color([px[p] for p in _all(crop) if max(px[p][:3]) <= DARK_MAX])
    tall = max(y for _, y in opening) - min(y for _, y in opening) + 1
    thick = max(2, min(4, round(tall * 0.2)))

    cols = {}
    for x, y in opening:
        top, bottom = cols.get(x, (y, y))
        cols[x] = (min(top, y), max(bottom, y))
    out = crop.copy()
    dst = out.load()
    for x, (top, bottom) in cols.items():
        span = bottom - top + 1
        if closed >= 1 and open_eye:
            # A shut eyeball: all lid, with a lash line low across it.
            edge, fill_to = top + round(0.72 * span), bottom + 1
        else:
            # Partway down, or along the bottom when a dot eye is shut.
            edge = top + round(min(closed, 1) * span)
            fill_to = edge
        for y in range(top, min(fill_to, bottom + 1)):
            if (x, y) in opening:
                dst[x, y] = line if edge - thick <= y < edge else skin
    return out, box[:2]


def blink(base, spec):
    """Eyes close and open; `eyes_later` blink in turn after another stare."""
    stare = spec.get("stare", 3600)
    open_eye = spec.get("open", False)
    groups = [spec["eyes"]] + ([spec["eyes_later"]] if "eyes_later" in spec else [])
    frames = []
    for i, eyes in enumerate(groups):
        if i:
            frames.append((base.copy(), stare // 2))
        for closed, gap in ((0.5, 60), (1.0, 130), (0.5, 60)):
            pieces = [_eyelid(base, e, closed, open_eye) for e in eyes]
            frames.append((_with(base, pieces), gap))
    return (stare // 2 if len(groups) > 1 else stare), frames


def steam(base, spec):
    """Light wisps sway side to side, more at the top than at the source."""
    box = _box(spec["box"])
    crop = base.crop(box)
    w, h = crop.size
    px = crop.load()
    border = [p for p in _all(crop) if p[0] in (0, w - 1) or p[1] in (0, h - 1)]
    body_blue = median(px[p][2] for p in border)
    light = {
        p
        for p in _all(crop)
        if px[p][2] >= body_blue + spec.get("lift", 30) and min(px[p][:2]) >= LIGHT_MIN
    }
    wisps = set().union(*(c for c in _components(light, w, h) if len(c) >= 15))
    wisps = _grow(wisps, 2, w, h)
    background = _inpaint(crop, wisps)
    sprite = _layer(crop, wisps).convert("RGBa")
    top = min(y for _, y in wisps)
    bottom = max(y for _, y in wisps)
    amp, wave, zoom = spec.get("amplitude", 4), spec.get("wavelength", 70), 4

    big = sprite.resize((w * zoom, h * zoom), Image.Resampling.BILINEAR)
    frames = []
    steps = 6
    for k in range(1, steps):
        phase = 2 * math.pi * k / steps
        swayed = Image.new("RGBa", big.size)
        for yy in range(h * zoom):
            y = yy / zoom
            # Full sway at the top, none where the steam leaves its source.
            reach = 1 - max(0.0, min(1.0, (y - top) / max(1, bottom - top)))
            angle = 2 * math.pi * y / wave
            dx = amp * reach * (math.sin(angle + phase) - math.sin(angle))
            row = big.crop((0, yy, w * zoom, yy + 1))
            swayed.paste(row, (round(dx * zoom), yy))
        small = swayed.resize((w, h), Image.Resampling.BOX).convert("RGBA")
        piece = Image.alpha_composite(background, small)
        frames.append((_with(base, [(piece, box[:2])]), 150))
    return 150, frames


GLOW_STEPS = {
    # Lightsaber hum: brighten and widen the halo, then dip.
    "saber": ([0.45, -0.4, 0.65], [80, 90, 70], 100),
    # Candle inside a jack-o'-lantern: the root frame is the unlit pumpkin.
    "candle": ([0.95, 0.85, 1.0, 0.82, 0.92], [120, 90, 140, 80, 110], 50),
}
CANDLE = (255, 214, 90)
CANDLE_CORE = (255, 236, 140)


def glow(base, spec):
    """Brighten part of the art in a flickering rhythm."""
    box = _box(spec["box"])
    crop = base.crop(box)
    w, h = crop.size
    px = crop.load()
    kind = spec["kind"]
    steps, gaps, root_gap = GLOW_STEPS[kind]
    if kind == "saber":
        lit = {
            p
            for p in _all(crop)
            if px[p][3] > 0 and px[p][2] >= 150 and px[p][2] - px[p][0] >= 20
        }
    else:
        dark = {p for p in _all(crop) if max(px[p][:3]) <= DARK_MAX}
        lit = set().union(
            *(c for c in _components(_interior(dark, w, h), w, h) if len(c) >= 30)
        )
    core = _shrink(lit, 2, w, h)
    hot = _shrink(lit, 5, w, h)

    frames = []
    for k, gap in zip(steps, gaps):
        out = crop.copy()
        dst = out.load()
        for p in lit:
            r, g, b, a = px[p]
            if kind == "saber":
                # Brighten the blade; dimming only thins the halo, so the
                # blade never goes grey.
                lift = max(k, 0) * 0.8
                rgb = [c + (255 - c) * lift for c in (r, g, b)]
                if a < 255:
                    a = min(255, a * (1 + k))
                dst[p] = (*(round(c) for c in rgb), round(a))
            else:
                color = CANDLE_CORE if p in hot else CANDLE
                t = k if p in core else k * 0.6
                rgb = [c + (glow_c - c) * t for c, glow_c in zip((r, g, b), color)]
                dst[p] = (*(round(c) for c in rgb), a)
        frames.append((_with(base, [(out, box[:2])]), gap))
    return root_gap, frames


def _star(dst, at, arm, size):
    """A four-point glint with a soft glow, blended toward white."""
    (cx, cy), (w, h) = at, size
    for dy in range(-arm, arm + 1):
        for dx in range(-arm, arm + 1):
            x, y = cx + dx, cy + dy
            if not (0 <= x < w and 0 <= y < h):
                continue
            dist = math.hypot(dx, dy)
            glow_amt = max(0.0, 1 - dist / 4.5) ** 2
            if dx == 0 or dy == 0:
                spike = (1 - max(abs(dx), abs(dy)) / (arm + 1)) ** 1.5
            elif abs(dx) == abs(dy):
                spike = 0.5 * (1 - abs(dx) / (arm * 0.5 + 1)) ** 2
            else:
                spike = 0.0
            amt = min(1.0, max(glow_amt, spike))
            if amt <= 0:
                continue
            r, g, b, a = dst[x, y]
            dst[x, y] = (
                round(r + (255 - r) * amt),
                round(g + (255 - g) * amt),
                round(b + (255 - b) * amt),
                a,
            )


def twinkle(base, spec):
    """Big glints pop in and out across a dark, glittery area.

    Each frame's stars sit close together so its patch stays small.
    """
    box = _box(spec["box"])
    crop = base.crop(box)
    w, h = crop.size
    px = crop.load()
    spots = [p for p in _all(crop) if px[p][3] > 200 and max(px[p][:3]) < 90]
    rng = random.Random(spec.get("seed", 7))
    frames = []
    for _ in range(5):
        out = crop.copy()
        dst = out.load()
        cx, cy = rng.choice(spots)
        near = [p for p in spots if abs(p[0] - cx) < 40 and abs(p[1] - cy) < 30]
        for sx, sy in rng.sample(near, min(len(near), spec.get("count", 3))):
            _star(dst, (sx, sy), rng.randint(10, 16), (w, h))
        frames.append((_with(base, [(out, box[:2])]), 150))
    return 150, frames


def pulse(base, spec):
    """Shapes on a transparent background beat like a heart: lub, dub, rest.

    Each box scales its largest shape about its centre; anything else that
    strays into the box stays put.
    """
    beats = [(1.12, 110), (1.0, 110), (1.07, 110)]
    shapes = []
    for b in spec["boxes"]:
        box = _box(b)
        crop = base.crop(box)
        w, h = crop.size
        solid = {p for p in _all(crop) if crop.getpixel(p)[3] > 0}
        shape = max(_components(solid, w, h), key=len)
        xs, ys = [x for x, _ in shape], [y for _, y in shape]
        anchor = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        rest = _layer(crop, set(_all(crop)) - shape)
        shapes.append((box, _layer(crop, shape), rest, anchor))
    frames = []
    for scale, gap in beats:
        if scale == 1:
            frames.append((base.copy(), gap))
            continue
        pieces = [
            (
                Image.alpha_composite(rest, _affine(sprite, scale, scale, 0, anchor)),
                box[:2],
            )
            for box, sprite, rest, anchor in shapes
        ]
        frames.append((_with(base, pieces), gap))
    return 650, frames


EFFECTS = {
    "flicker": flicker,
    "blink": blink,
    "steam": steam,
    "glow": glow,
    "twinkle": twinkle,
    "pulse": pulse,
}


# --- packaging ------------------------------------------------------------------


def pack(png: Path, base: Image.Image, frames: list, root_gap: int) -> Path:
    """Write per-frame patches and the manifest next to the base PNG."""
    stem = png.stem
    for old in png.parent.glob(f"{stem}-anim*.png"):
        old.unlink()
    entries = []
    for i, (frame, gap) in enumerate(frames, start=1):
        diff = ImageChops.difference(base, frame).getbbox(alpha_only=False)
        box = diff or (0, 0, 1, 1)
        name = f"{stem}-anim{i}.png"
        frame.crop(box).save(png.with_name(name), optimize=True)
        entries.append({"file": name, "x": box[0], "y": box[1], "gap": gap})
    # Squeeze the patches losslessly. (pngquant would shift colours and leave
    # visible seams where a patch meets the root image.)
    if oxipng := shutil.which("oxipng"):
        patches = [str(png.with_name(e["file"])) for e in entries]
        cmd = [oxipng, "-o", "4", "--strip", "safe", "-q", *patches]
        subprocess.run(cmd, check=True)  # noqa: S603
    manifest = png.with_name(f"{stem}.anim.json")
    manifest.write_text(
        json.dumps({"root_gap": root_gap, "frames": entries}, indent=2) + "\n"
    )
    return manifest


def preview(base: Image.Image, frames: list, root_gap: int, out: Path) -> None:
    """Write an animated GIF of the whole loop for eyeballing."""
    dark = Image.new("RGBA", base.size, (30, 30, 30, 255))
    flat = [Image.alpha_composite(dark, f) for f in [base, *(f for f, _ in frames)]]
    flat[0].save(
        out,
        save_all=True,
        append_images=flat[1:],
        duration=[root_gap, *(g for _, g in frames)],
        loop=0,
    )


def _build(stems: list[str], preview_dir: Path | None) -> None:
    config = tomllib.loads(CONFIG.read_text())
    for stem in stems or list(config):
        spec = config[stem]
        png = STATIC / f"{stem}.png"
        base = Image.open(png).convert("RGBA")
        root_gap, frames = EFFECTS[spec["effect"]](base, spec)
        manifest = pack(png, base, frames, root_gap)
        if preview_dir:
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview(base, frames, root_gap, preview_dir / f"{stem}.gif")
        print(f"{manifest.name}: {spec['effect']}, {len(frames)} frames")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    bd = sub.add_parser("build")
    bd.add_argument("stems", nargs="*")
    bd.add_argument("--preview", type=Path)
    pk = sub.add_parser("pack")
    pk.add_argument("png", type=Path)
    pk.add_argument("frames", nargs="+", type=Path)
    pk.add_argument("--gap", type=int, default=120)
    pk.add_argument("--preview", type=Path)
    ns = parser.parse_args()

    if ns.cmd == "build":
        _build(ns.stems, ns.preview)
        return
    base = Image.open(ns.png).convert("RGBA")
    frames = [(Image.open(f).convert("RGBA"), ns.gap) for f in ns.frames]
    manifest = pack(ns.png, base, frames, ns.gap)
    if ns.preview:
        preview(base, frames, ns.gap, ns.preview)
    print(f"wrote {manifest} with {len(frames)} frames")


if __name__ == "__main__":
    main()
