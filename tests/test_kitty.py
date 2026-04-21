"""Tests for Kitty graphics protocol support."""

import base64
import struct
from importlib.resources import files
from unittest.mock import patch

from billie.kitty import (
    CELL_ASPECT_RATIO,
    CHUNK_SIZE,
    SUPPORTED_TERMINALS,
    calculate_cell_size,
    encode_image_chunks,
    is_kitty_capable,
    parse_png_dimensions,
    send_image,
)


class TestIsKittyCapable:
    """Verify terminal capability detection."""

    @patch.dict("os.environ", {"TERM_PROGRAM": "ghostty"})
    def test_ghostty_supported(self):
        assert is_kitty_capable() is True

    @patch.dict("os.environ", {"TERM_PROGRAM": "kitty"})
    def test_kitty_supported(self):
        assert is_kitty_capable() is True

    @patch.dict("os.environ", {"TERM_PROGRAM": "WezTerm"})
    def test_wezterm_supported(self):
        assert is_kitty_capable() is True

    @patch.dict("os.environ", {"TERM_PROGRAM": "xterm"})
    def test_xterm_not_supported(self):
        assert is_kitty_capable() is False

    @patch.dict("os.environ", {}, clear=True)
    def test_unset_not_supported(self):
        assert is_kitty_capable() is False

    def test_supported_terminals_set(self):
        assert {"ghostty", "kitty", "WezTerm"} == SUPPORTED_TERMINALS


class TestParsePngDimensions:
    """Verify PNG header parsing."""

    def test_real_billie_png(self):
        data = files("billie").joinpath("static/billie.png").read_bytes()
        w, h = parse_png_dimensions(data)
        assert w == 1470  # noqa: PLR2004
        assert h == 1320  # noqa: PLR2004

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
