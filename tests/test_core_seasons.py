"""Tests for season integration in core."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from billie.core import Billie, TTYHandler, setup_arguments


class TestSeasonArgument:
    def test_season_flag_accepts_valid_season(self):
        parser = setup_arguments()
        ns = parser.parse_args(["--season", "halloween"])
        assert ns.season == "halloween"

    def test_season_flag_accepts_none(self):
        parser = setup_arguments()
        ns = parser.parse_args(["--season", "none"])
        assert ns.season == "none"

    def test_season_default_is_auto(self):
        parser = setup_arguments()
        ns = parser.parse_args([])
        assert ns.season == "auto"

    def test_season_flag_rejects_invalid(self):
        parser = setup_arguments()
        with pytest.raises(SystemExit):
            parser.parse_args(["--season", "summer"])

    def test_season_short_flag(self):
        parser = setup_arguments()
        ns = parser.parse_args(["-s", "billing"])
        assert ns.season == "billing"


def _make_billie(season="auto"):
    """Create a Billie instance with minimal TTY for testing."""
    tty = TTYHandler()
    ns = SimpleNamespace(
        no_billie=True,
        max_height=None,
        max_width=None,
        density=30,
        season=season,
    )
    return Billie(tty, ns)


class TestSetupSeasonal:
    def test_season_none_leaves_defaults(self):
        b = _make_billie(season="none")
        original_path = b.billie_path
        original_words = list(b.words)
        b.setup_seasonal()
        assert b.billie_path == original_path
        assert list(b.words) == original_words

    def test_explicit_season_extends_words(self):
        b = _make_billie(season="halloween")
        original_len = len(b.words)
        b.setup_seasonal()
        assert len(b.words) > original_len
        assert any("haunted" in w for w in b.words)

    def test_explicit_season_sets_art_path(self):
        b = _make_billie(season="halloween")
        b.setup_seasonal()
        assert "billie-halloween.txt" in str(b.billie_path)

    @patch("billie.seasons.get_current_season", return_value="valentine")
    def test_auto_uses_detected_season(self, mock_season):  # noqa: ARG002
        b = _make_billie(season="auto")
        b.setup_seasonal()
        assert "billie-valentine.txt" in str(b.billie_path)
        assert any("commitment" in w for w in b.words)

    @patch("billie.seasons.get_current_season", return_value=None)
    def test_auto_no_season_leaves_defaults(self, mock_season):  # noqa: ARG002
        b = _make_billie(season="auto")
        original_path = b.billie_path
        original_words = list(b.words)
        b.setup_seasonal()
        assert b.billie_path == original_path
        assert list(b.words) == original_words
