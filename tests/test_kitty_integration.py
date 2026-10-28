"""Tests for Kitty graphics protocol integration into core.py."""

import re
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from billie.core import ROOT, Billie, TTYHandler


def _make_billie(*, no_billie=False, width=120, height=50, season="none"):
    """Create a Billie instance with controllable TTY settings."""
    tty = TTYHandler()
    tty.width = width
    tty.height = height
    tty.out_is_tty = True
    tty.pretty = True
    ns = SimpleNamespace(
        no_billie=no_billie,
        max_height=None,
        max_width=None,
        density=30,
        season=season,
    )
    return Billie(tty, ns)


class TestBillieInitKittyAttributes:
    """Billie.__init__ should set kitty-related attributes."""

    def test_kitty_mode_defaults_false(self):
        b = _make_billie()
        assert b.kitty_mode is False

    def test_image_data_defaults_none(self):
        b = _make_billie()
        assert b.image_data is None

    def test_image_cols_defaults_zero(self):
        b = _make_billie()
        assert b.image_cols == 0

    def test_image_rows_defaults_zero(self):
        b = _make_billie()
        assert b.image_rows == 0

    def test_actual_width_defaults_zero(self):
        b = _make_billie()
        assert b.actual_width == 0


class TestSetupKittyCapableWithPNG:
    """When terminal supports Kitty AND a PNG exists, activate kitty_mode."""

    @patch("billie.kitty.is_kitty_capable", return_value=True)
    @patch("billie.core.Path.home")
    def test_kitty_mode_enabled(self, mock_home, mock_capable, tmp_path):  # noqa: ARG002
        mock_home.return_value = tmp_path
        (tmp_path / "somefile").touch()
        b = _make_billie()
        b.setup()
        assert b.kitty_mode is True

    @patch("billie.kitty.is_kitty_capable", return_value=True)
    @patch("billie.core.Path.home")
    def test_image_data_loaded(self, mock_home, mock_capable, tmp_path):  # noqa: ARG002
        mock_home.return_value = tmp_path
        (tmp_path / "somefile").touch()
        b = _make_billie()
        b.setup()
        assert b.image_data is not None
        assert len(b.image_data) > 0

    @patch("billie.kitty.is_kitty_capable", return_value=True)
    @patch("billie.core.Path.home")
    def test_image_cols_and_rows_set(self, mock_home, mock_capable, tmp_path):  # noqa: ARG002
        mock_home.return_value = tmp_path
        (tmp_path / "somefile").touch()
        b = _make_billie(height=50)
        b.setup()
        assert b.image_cols > 0
        assert b.image_rows > 0

    @patch("billie.kitty.is_kitty_capable", return_value=True)
    @patch("billie.core.Path.home")
    def test_tty_width_reduced(self, mock_home, mock_capable, tmp_path):  # noqa: ARG002
        mock_home.return_value = tmp_path
        (tmp_path / "somefile").touch()
        original_width = 120
        b = _make_billie(width=original_width, height=50)
        b.setup()
        assert b.actual_width == original_width
        assert b.tty.width < original_width
        assert b.tty.width == original_width - b.image_cols


class TestSetupKittyNarrowTerminal:
    """When image is too wide for terminal, fall back to ANSI."""

    @patch("billie.kitty.is_kitty_capable", return_value=True)
    @patch("billie.core.Path.home")
    def test_narrow_terminal_falls_back(self, mock_home, mock_capable, tmp_path):  # noqa: ARG002
        mock_home.return_value = tmp_path
        (tmp_path / "somefile").touch()
        b = _make_billie(width=30, height=50)
        b.setup()
        assert b.kitty_mode is False
        assert b.tty.width == 30  # noqa: PLR2004


class TestSetupNonKittyTerminal:
    """Non-Kitty terminals should behave exactly as before."""

    @patch("billie.kitty.is_kitty_capable", return_value=False)
    @patch("billie.core.Path.home")
    def test_kitty_mode_false(self, mock_home, mock_capable, tmp_path):  # noqa: ARG002
        mock_home.return_value = tmp_path
        (tmp_path / "somefile").touch()
        b = _make_billie()
        b.setup()
        assert b.kitty_mode is False

    @patch("billie.kitty.is_kitty_capable", return_value=False)
    @patch("billie.core.Path.home")
    def test_image_data_none(self, mock_home, mock_capable, tmp_path):  # noqa: ARG002
        mock_home.return_value = tmp_path
        (tmp_path / "somefile").touch()
        b = _make_billie()
        b.setup()
        assert b.image_data is None


class TestSetupNoBillieFlag:
    """--no-billie should prevent Kitty mode."""

    @patch("billie.kitty.is_kitty_capable", return_value=True)
    @patch("billie.core.Path.home")
    def test_no_billie_skips_kitty(self, mock_home, mock_capable, tmp_path):  # noqa: ARG002
        mock_home.return_value = tmp_path
        (tmp_path / "somefile").touch()
        b = _make_billie(no_billie=True)
        b.setup()
        assert b.kitty_mode is False


class TestPrintBillieKittyMode:
    """print_billie() in kitty_mode writes Kitty escape sequences."""

    @patch("billie.kitty.is_kitty_capable", return_value=True)
    @patch("billie.core.Path.home")
    def test_kitty_escape_in_output(self, mock_home, mock_capable, tmp_path):  # noqa: ARG002
        mock_home.return_value = tmp_path
        (tmp_path / "somefile").touch()
        b = _make_billie(width=120, height=50)
        b.setup()
        assert b.kitty_mode is True

        output = StringIO()
        with patch("sys.stdout", output):
            b.print_billie()
        result = output.getvalue()
        assert "\033_G" in result

    @patch("billie.kitty.is_kitty_capable", return_value=True)
    @patch("billie.core.Path.home")
    def test_cursor_positioning_in_output(self, mock_home, mock_capable, tmp_path):  # noqa: ARG002
        mock_home.return_value = tmp_path
        (tmp_path / "somefile").touch()
        b = _make_billie(width=120, height=50)
        b.setup()

        output = StringIO()
        with patch("sys.stdout", output):
            b.print_billie()
        result = output.getvalue()
        assert "\033[" in result


class TestPrintBillieNonKittyMode:
    """print_billie() without kitty_mode must NOT emit Kitty sequences."""

    @patch("billie.kitty.is_kitty_capable", return_value=False)
    @patch("billie.core.Path.home")
    def test_no_kitty_escape_in_output(self, mock_home, mock_capable, tmp_path):  # noqa: ARG002
        mock_home.return_value = tmp_path
        (tmp_path / "somefile").touch()
        b = _make_billie()
        b.setup()

        output = StringIO()
        with patch("sys.stdout", output):
            b.print_billie()
        result = output.getvalue()
        assert "\033_G" not in result


class TestAnimation:
    """Seasons with an .anim.json get animated where the terminal can play it."""

    @patch("billie.kitty.supports_animation", return_value=True)
    @patch("billie.kitty.is_kitty_capable", return_value=True)
    @patch("billie.core.Path.home")
    def test_frames_loaded(self, mock_home, mock_capable, mock_anim, tmp_path):  # noqa: ARG002
        mock_home.return_value = tmp_path
        (tmp_path / "somefile").touch()
        b = _make_billie(season="birthday")
        b.setup()
        assert b.anim_frames
        assert b.anim_root_gap > 0
        for data, _x, _y, gap in b.anim_frames:
            assert data.startswith(b"\x89PNG")
            assert gap > 0

    @patch("billie.kitty.supports_animation", return_value=False)
    @patch("billie.kitty.is_kitty_capable", return_value=True)
    @patch("billie.core.Path.home")
    def test_no_frames_without_support(
        self,
        mock_home,
        mock_capable,  # noqa: ARG002
        mock_anim,  # noqa: ARG002
        tmp_path,
    ):
        mock_home.return_value = tmp_path
        (tmp_path / "somefile").touch()
        b = _make_billie(season="birthday")
        b.setup()
        assert b.anim_frames == []

    def test_art_without_manifest_has_no_frames(self):
        b = _make_billie()
        b.load_animation(ROOT.joinpath("billie-does-not-exist.png"))
        assert b.anim_frames == []

    @patch("billie.kitty.supports_animation", return_value=True)
    @patch("billie.kitty.is_kitty_capable", return_value=True)
    @patch("billie.core.Path.home")
    def test_output_animates_the_displayed_image(
        self,
        mock_home,
        mock_capable,  # noqa: ARG002
        mock_anim,  # noqa: ARG002
        tmp_path,
    ):
        mock_home.return_value = tmp_path
        (tmp_path / "somefile").touch()
        b = _make_billie(season="birthday")
        b.setup()

        output = StringIO()
        with patch("sys.stdout", output):
            b.print_billie()
        result = output.getvalue()

        number = re.search(r"a=T[^;]*,I=(\d+)", result).group(1)
        assert result.count("a=f,") == len(b.anim_frames)
        assert f"I={number},s=3,v=1" in result
        # Frames come after the image they animate.
        assert result.index("a=T") < result.index("a=f")
