"""Every Billie ships an animation, and every manifest points at real patches."""

import json
import struct
from importlib.resources import files

import pytest

STATIC = files("billie").joinpath("static")
# Terminals keep each frame as a full decoded image, so keep animations short.
MAX_FRAMES = 8
ARTS = sorted(
    p.name.removesuffix(".png")
    for p in STATIC.iterdir()
    if p.name.endswith(".png") and "-anim" not in p.name
)


def _png_size(data):
    return struct.unpack(">II", data[16:24])


@pytest.mark.parametrize("stem", ARTS)
def test_every_billie_is_animated(stem):
    assert STATIC.joinpath(f"{stem}.anim.json").is_file()


@pytest.mark.parametrize("stem", ARTS)
def test_manifest_patches_fit_their_art(stem):
    manifest = json.loads(STATIC.joinpath(f"{stem}.anim.json").read_text())
    width, height = _png_size(STATIC.joinpath(f"{stem}.png").read_bytes())
    assert manifest["root_gap"] > 0
    assert 0 < len(manifest["frames"]) <= MAX_FRAMES
    for frame in manifest["frames"]:
        data = STATIC.joinpath(frame["file"]).read_bytes()
        assert data.startswith(b"\x89PNG")
        w, h = _png_size(data)
        assert frame["x"] + w <= width
        assert frame["y"] + h <= height
        assert frame["gap"] > 0
