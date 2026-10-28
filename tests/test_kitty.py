"""Tests for Kitty graphics protocol support."""

import base64
import struct
from importlib.resources import files
from io import StringIO
from unittest.mock import patch

import pytest

from billie import kitty
from billie.kitty import (
    CELL_ASPECT_RATIO,
    CHUNK_SIZE,
    SUPPORTED_TERMINALS,
    calculate_cell_size,
    cell_aspect_ratio,
    encode_animation_start,
    encode_frame_chunks,
    encode_image_chunks,
    is_kitty_capable,
    parse_png_dimensions,
    send_animation,
    send_image,
    supports_animation,
    terminal_program,
)


class TestIsKittyCapable:
    """Verify terminal capability detection."""

    @patch.dict("os.environ", {"TERM_PROGRAM": "ghostty"}, clear=True)
    def test_ghostty_supported(self):
        assert is_kitty_capable() is True

    @patch.dict("os.environ", {"TERM_PROGRAM": "kitty"}, clear=True)
    def test_kitty_supported(self):
        assert is_kitty_capable() is True

    @patch.dict("os.environ", {"TERM_PROGRAM": "WezTerm"}, clear=True)
    def test_wezterm_supported(self):
        assert is_kitty_capable() is True

    @patch.dict("os.environ", {"TERM_PROGRAM": "xterm"}, clear=True)
    def test_xterm_not_supported(self):
        assert is_kitty_capable() is False

    @patch.dict("os.environ", {}, clear=True)
    def test_unset_not_supported(self):
        assert is_kitty_capable() is False

    @patch.dict("os.environ", {"TERM": "xterm-kitty"}, clear=True)
    def test_kitty_detected_by_term(self):
        # kitty never sets TERM_PROGRAM, only its terminfo name.
        assert terminal_program() == "kitty"

    @patch.dict(
        "os.environ", {"TERM_PROGRAM": "tmux", "TERM": "tmux-256color"}, clear=True
    )
    def test_tmux_not_supported(self):
        assert is_kitty_capable() is False

    def test_supported_terminals_set(self):
        assert {"ghostty", "kitty", "WezTerm"} == SUPPORTED_TERMINALS


class TestParsePngDimensions:
    """Verify PNG header parsing."""

    def test_real_billie_png(self):
        data = files("billie").joinpath("static/billie.png").read_bytes()
        w, h = parse_png_dimensions(data)
        assert w == 1000  # noqa: PLR2004
        assert h == 898  # noqa: PLR2004

    def test_synthetic_png_header(self):
        signature = b"\x89PNG\r\n\x1a\n"
        ihdr_data = struct.pack(">II", 640, 480)
        chunk_length = struct.pack(">I", 13)
        header = signature + chunk_length + b"IHDR" + ihdr_data
        header += b"\x00" * (24 - len(header))
        w, h = parse_png_dimensions(header)
        assert w == 640  # noqa: PLR2004
        assert h == 480  # noqa: PLR2004


class TestCalculateCellSize:
    """Verify terminal cell size computation."""

    def test_basic_calculation(self):
        cols, rows = calculate_cell_size(1472, 1320, 50)
        expected_rows = int(50 * 0.55)
        aspect = 1472 / 1320
        expected_cols = int(expected_rows * aspect * CELL_ASPECT_RATIO)
        assert rows == expected_rows
        assert cols == expected_cols

    def test_square_image(self):
        cols, rows = calculate_cell_size(100, 100, 40)
        expected_rows = int(40 * 0.55)
        expected_cols = int(expected_rows * 1.0 * CELL_ASPECT_RATIO)
        assert rows == expected_rows
        assert cols == expected_cols

    def test_wide_image(self):
        cols, rows = calculate_cell_size(200, 100, 30)
        expected_rows = int(30 * 0.55)
        expected_cols = int(expected_rows * 2.0 * CELL_ASPECT_RATIO)
        assert rows == expected_rows
        assert cols == expected_cols

    def test_measured_cell_aspect(self):
        cols, rows = calculate_cell_size(100, 100, 40, cell_aspect=2.5)
        assert rows == int(40 * 0.55)
        assert cols == int(rows * 2.5)


class TestSupportsAnimation:
    """Only terminals that play Kitty animations themselves get frames."""

    @pytest.mark.parametrize(
        ("version", "expected"),
        [
            ("1.4.0", True),
            ("1.4.1", True),
            ("1.10.0", True),
            ("2.0.0", True),
            ("1.4.0-main+abc123", True),
            ("1.3.1", False),
            ("", False),
        ],
    )
    def test_ghostty_versions(self, version, expected):
        env = {"TERM_PROGRAM": "ghostty", "TERM_PROGRAM_VERSION": version}
        with patch.dict("os.environ", env, clear=True):
            assert supports_animation() is expected

    @patch.dict("os.environ", {"TERM": "xterm-kitty"}, clear=True)
    def test_kitty_animates(self):
        assert supports_animation() is True

    @patch.dict(
        "os.environ",
        {"TERM_PROGRAM": "WezTerm", "TERM_PROGRAM_VERSION": "20240203"},
        clear=True,
    )
    def test_wezterm_does_not(self):
        assert supports_animation() is False

    @patch.dict("os.environ", {}, clear=True)
    def test_unknown_terminal_does_not(self):
        assert supports_animation() is False


class TestCellAspectRatio:
    """Cell shape comes from TIOCGWINSZ pixel sizes when the terminal sets them."""

    @staticmethod
    def _winsize(rows, cols, xpixel, ypixel):
        return struct.pack("HHHH", rows, cols, xpixel, ypixel)

    def test_measured(self):
        # 50 rows x 100 cols at 1000x1100 px: cells are 10x22, ratio 2.2.
        packed = self._winsize(50, 100, 1000, 1100)
        with patch("billie.kitty.fcntl.ioctl", return_value=packed):
            assert cell_aspect_ratio(fd=1) == pytest.approx(2.2)

    def test_zero_pixels_falls_back(self):
        packed = self._winsize(50, 100, 0, 0)
        with patch("billie.kitty.fcntl.ioctl", return_value=packed):
            assert cell_aspect_ratio(fd=1) == CELL_ASPECT_RATIO

    def test_absurd_ratio_falls_back(self):
        packed = self._winsize(50, 100, 1000, 100)
        with patch("billie.kitty.fcntl.ioctl", return_value=packed):
            assert cell_aspect_ratio(fd=1) == CELL_ASPECT_RATIO

    def test_not_a_tty_falls_back(self):
        with patch("billie.kitty.fcntl.ioctl", side_effect=OSError):
            assert cell_aspect_ratio(fd=1) == CELL_ASPECT_RATIO

    def test_no_fcntl_falls_back(self):
        with patch.object(kitty, "fcntl", None):
            assert cell_aspect_ratio(fd=1) == CELL_ASPECT_RATIO


class TestEncodeImageChunks:
    """Verify Kitty protocol escape sequence generation."""

    def test_small_image_single_chunk(self):
        data = b"\x00" * 100
        sequences = encode_image_chunks(data, cols=10, rows=5)
        assert len(sequences) == 1
        assert "m=0" in sequences[0]
        assert "f=100" in sequences[0]
        assert "a=T" in sequences[0]
        assert "c=10" in sequences[0]
        assert "r=5" in sequences[0]

    def test_quiet_transient_and_cursor_stays(self):
        first = encode_image_chunks(b"\x00" * 100, cols=10, rows=5)[0]
        keys = first.split(";", 1)[0].removeprefix("\033_G").split(",")
        assert "q=2" in keys
        assert "N=1" in keys
        assert "C=1" in keys

    def test_no_image_number_by_default(self):
        first = encode_image_chunks(b"\x00" * 100, cols=10, rows=5)[0]
        assert "I=" not in first

    def test_image_number(self):
        first = encode_image_chunks(b"\x00" * 100, cols=10, rows=5, image_number=42)[0]
        assert "I=42" in first

    def test_large_image_multiple_chunks(self):
        data = b"\x42" * 4096
        sequences = encode_image_chunks(data, cols=20, rows=10)
        assert len(sequences) > 1

    def test_non_final_chunks_have_m1(self):
        data = b"\x42" * 4096
        sequences = encode_image_chunks(data, cols=20, rows=10)
        for seq in sequences[:-1]:
            assert "m=1" in seq

    def test_final_chunk_has_m0(self):
        data = b"\x42" * 4096
        sequences = encode_image_chunks(data, cols=20, rows=10)
        assert "m=0" in sequences[-1]

    def test_first_chunk_has_control_params(self):
        data = b"\x42" * 4096
        sequences = encode_image_chunks(data, cols=20, rows=10)
        assert "f=100" in sequences[0]
        assert "a=T" in sequences[0]
        assert "t=d" in sequences[0]
        assert "c=20" in sequences[0]
        assert "r=10" in sequences[0]

    def test_subsequent_chunks_lack_control_params(self):
        data = b"\x42" * 4096
        sequences = encode_image_chunks(data, cols=20, rows=10)
        for seq in sequences[1:]:
            assert "f=100" not in seq
            assert "a=T" not in seq

    def test_escape_sequence_framing(self):
        data = b"\x00" * 10
        sequences = encode_image_chunks(data, cols=5, rows=3)
        for seq in sequences:
            assert seq.startswith("\033_G")
            assert seq.endswith("\033\\")

    def test_chunk_payload_is_valid_base64(self):
        data = b"\x42" * 100
        sequences = encode_image_chunks(data, cols=5, rows=3)
        for seq in sequences:
            payload = seq.split(";", 1)[1].rstrip("\033\\")
            base64.b64decode(payload)

    def test_chunk_size_limit(self):
        data = b"\x42" * 8192
        sequences = encode_image_chunks(data, cols=10, rows=5)
        for seq in sequences:
            payload = seq.split(";", 1)[1].rstrip("\033\\")
            assert len(payload) <= CHUNK_SIZE


class TestSendImage:
    """Verify send_image writes escape sequences to stdout."""

    def test_writes_all_chunks_to_stdout(self):
        data = b"\x42" * 4096
        expected = encode_image_chunks(data, cols=20, rows=10)
        with patch("billie.kitty.sys.stdout") as mock_stdout:
            send_image(data, cols=20, rows=10)
            written = [call.args[0] for call in mock_stdout.write.call_args_list]
        assert written == expected


class TestAnimationEncoding:
    """Frames are patches composed onto the root frame of a numbered image."""

    def test_frame_keys(self):
        first = encode_frame_chunks(b"\x00" * 100, 7, x=12, y=34, gap=90)[0]
        keys = first.split(";", 1)[0].removeprefix("\033_G").split(",")
        for key in ("a=f", "f=100", "q=2", "N=1", "I=7", "c=1", "X=1"):
            assert key in keys
        assert {"x=12", "y=34", "z=90"} <= set(keys)

    def test_frame_continuation_chunks_are_bare(self):
        sequences = encode_frame_chunks(b"\x42" * 8192, 7, x=0, y=0, gap=90)
        assert len(sequences) > 1
        for seq in sequences[1:]:
            assert seq.startswith(("\033_Gm=0;", "\033_Gm=1;"))

    def test_start_sets_root_gap_then_loops(self):
        gap, start = encode_animation_start(7, root_gap=160)
        assert "a=a" in gap
        assert "I=7" in gap
        assert "r=1" in gap
        assert "z=160" in gap
        assert "s=3" in start
        assert "v=1" in start
        assert "q=2" in gap
        assert "q=2" in start

    def test_send_animation_order(self):
        frames = [(b"\x01" * 10, 1, 2, 80), (b"\x02" * 10, 3, 4, 90)]
        out = StringIO()
        with patch("billie.kitty.sys.stdout", out):
            send_animation(7, frames, root_gap=160)
        result = out.getvalue()
        assert result.count("a=f,") == 2  # noqa: PLR2004
        assert result.index("z=80") < result.index("z=90") < result.index("s=3")
