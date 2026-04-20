"""Kitty graphics protocol support for high-res Billie rendering."""

import base64
import os
import struct
import sys

CHUNK_SIZE = 4096
SUPPORTED_TERMINALS = {"ghostty", "kitty", "WezTerm"}
CELL_ASPECT_RATIO = 2.0


def is_kitty_capable():
    """Check if the terminal supports the Kitty graphics protocol."""
    return os.environ.get("TERM_PROGRAM", "") in SUPPORTED_TERMINALS


def parse_png_dimensions(data):
    """Extract (width, height) from a PNG file's IHDR chunk."""
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def calculate_cell_size(image_width, image_height, term_height):
    """Calculate image display size in terminal cells.

    Targets ~55% of terminal height. Returns (cols, rows).
    """
    rows = int(term_height * 0.55)
    aspect = image_width / image_height
    cols = int(rows * aspect * CELL_ASPECT_RATIO)
    return cols, rows


def encode_image_chunks(data, cols, rows):
    """Encode PNG data as Kitty graphics protocol escape sequences."""
    b64 = base64.standard_b64encode(data).decode("ascii")
    chunks = [b64[i : i + CHUNK_SIZE] for i in range(0, len(b64), CHUNK_SIZE)]
    sequences = []
    for i, chunk in enumerate(chunks):
        is_last = i == len(chunks) - 1
        if i == 0:
            ctrl = f"f=100,a=T,t=d,c={cols},r={rows},m={'0' if is_last else '1'}"
        else:
            ctrl = f"m={'0' if is_last else '1'}"
        sequences.append(f"\033_G{ctrl};{chunk}\033\\")
    return sequences


def send_image(data, cols, rows):
    """Transmit and display a PNG image via the Kitty graphics protocol."""
    for seq in encode_image_chunks(data, cols, rows):
        sys.stdout.write(seq)
