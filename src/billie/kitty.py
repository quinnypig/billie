"""Kitty graphics protocol support for high-res Billie rendering."""

import base64
import os
import re
import struct
import sys

try:
    import fcntl
    import termios
except ImportError:  # Windows: no ioctl, so no pixel sizes
    fcntl = termios = None

CHUNK_SIZE = 4096
SUPPORTED_TERMINALS = {"ghostty", "kitty", "WezTerm"}
CELL_ASPECT_RATIO = 2.0
# Sane bounds for a measured cell height/width ratio; outside them, guess.
MIN_CELL_ASPECT, MAX_CELL_ASPECT = 1.0, 4.0
# Terminals that play Kitty animations themselves, and the first version that
# does. Kitty has since 0.20 and doesn't advertise a version in the env.
ANIMATING_TERMINALS = {"kitty": (), "ghostty": (1, 4)}

# On every command: q=2 silences replies (billie exits without reading them,
# so they'd land in the user's shell prompt). On transmissions: N=1 marks the
# data transient so the terminal evicts it before anything the user cares about.
QUIET = "q=2"
TRANSIENT = "N=1"


def terminal_program():
    """Name the Kitty-graphics-capable terminal we're in, or None."""
    program = os.environ.get("TERM_PROGRAM", "")
    if program in SUPPORTED_TERMINALS:
        return program
    # kitty doesn't set TERM_PROGRAM; its terminfo name is the tell.
    if os.environ.get("TERM") == "xterm-kitty":
        return "kitty"
    return None


def is_kitty_capable():
    """Check if the terminal supports the Kitty graphics protocol."""
    return terminal_program() is not None


def supports_animation():
    """Check if the terminal will play Kitty animation frames on its own."""
    program = terminal_program()
    if program not in ANIMATING_TERMINALS:
        return False
    version = os.environ.get("TERM_PROGRAM_VERSION", "")
    parsed = tuple(int(n) for n in re.findall(r"\d+", version.split("-")[0]))
    return parsed >= ANIMATING_TERMINALS[program]


def cell_aspect_ratio(fd=None):
    """Measure the terminal's cell height/width ratio, or fall back to a guess.

    Reads the window's pixel size from TIOCGWINSZ, which needs no round trip
    to the terminal. Terminals that leave the pixel fields at zero get the
    default.
    """
    if fcntl is None:
        return CELL_ASPECT_RATIO
    try:
        fd = sys.stdout.fileno() if fd is None else fd
        packed = fcntl.ioctl(fd, termios.TIOCGWINSZ, b"\0" * 8)
    except (OSError, ValueError):
        return CELL_ASPECT_RATIO
    rows, cols, xpixel, ypixel = struct.unpack("HHHH", packed)
    if not (rows and cols and xpixel and ypixel):
        return CELL_ASPECT_RATIO
    ratio = (ypixel / rows) / (xpixel / cols)
    if not MIN_CELL_ASPECT <= ratio <= MAX_CELL_ASPECT:
        return CELL_ASPECT_RATIO
    return ratio


def parse_png_dimensions(data):
    """Extract (width, height) from a PNG file's IHDR chunk."""
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def calculate_cell_size(
    image_width, image_height, term_height, cell_aspect=CELL_ASPECT_RATIO
):
    """Calculate image display size in terminal cells.

    Targets ~55% of terminal height. Returns (cols, rows).
    """
    rows = int(term_height * 0.55)
    aspect = image_width / image_height
    cols = int(rows * aspect * cell_aspect)
    return cols, rows


def _chunked(ctrl, data):
    """Split a payload into escape sequences, control keys on the first."""
    b64 = base64.standard_b64encode(data).decode("ascii")
    chunks = [b64[i : i + CHUNK_SIZE] for i in range(0, len(b64), CHUNK_SIZE)]
    sequences = []
    for i, chunk in enumerate(chunks):
        more = "0" if i == len(chunks) - 1 else "1"
        keys = f"{ctrl},m={more}" if i == 0 else f"m={more}"
        sequences.append(f"\033_G{keys};{chunk}\033\\")
    return sequences


def encode_image_chunks(data, cols, rows, image_number=None):
    """Encode PNG data as Kitty graphics protocol escape sequences.

    C=1 leaves the cursor where it was; billie positions it itself. Pass an
    image_number to refer back to the image later (to animate it).
    """
    ctrl = f"f=100,a=T,t=d,{QUIET},{TRANSIENT},C=1,c={cols},r={rows}"
    if image_number is not None:
        ctrl += f",I={image_number}"
    return _chunked(ctrl, data)


def encode_frame_chunks(data, image_number, x, y, gap):
    """Encode a PNG patch as an animation frame of an existing image.

    The patch is composed onto the root frame (c=1) at pixel offset (x, y)
    by plain replacement (X=1), and shown for `gap` milliseconds.
    """
    ctrl = (
        f"a=f,f=100,t=d,{QUIET},{TRANSIENT},I={image_number},"
        f"c=1,X=1,x={x},y={y},z={gap}"
    )
    return _chunked(ctrl, data)


def encode_animation_start(image_number, root_gap):
    """Give the root frame a gap and loop the animation forever."""
    return [
        f"\033_Ga=a,{QUIET},I={image_number},r=1,z={root_gap}\033\\",
        f"\033_Ga=a,{QUIET},I={image_number},s=3,v=1\033\\",
    ]


def send_image(data, cols, rows, image_number=None):
    """Transmit and display a PNG image via the Kitty graphics protocol."""
    for seq in encode_image_chunks(data, cols, rows, image_number):
        sys.stdout.write(seq)


def send_animation(image_number, frames, root_gap):
    """Attach frames to a displayed image and start it looping.

    `frames` is a list of (png_bytes, x, y, gap_ms).
    """
    for data, x, y, gap in frames:
        for seq in encode_frame_chunks(data, image_number, x, y, gap):
            sys.stdout.write(seq)
    for seq in encode_animation_start(image_number, root_gap):
        sys.stdout.write(seq)
