"""Tests for Billie's seasonal awareness."""

from datetime import date

from billie.seasons import SEASONS, get_current_season


class TestSeasonData:
    """Verify season definitions are well-formed."""

    def test_all_seasons_have_required_keys(self):
        for name, season in SEASONS.items():
            assert "pic" in season, f"{name} missing 'pic'"
            assert "words" in season, f"{name} missing 'words'"
            if name != "billing":
                assert "dates" in season, f"{name} missing 'dates'"

    def test_all_seasons_have_nonempty_words(self):
        for name, season in SEASONS.items():
            assert len(season["words"]) > 0, f"{name} has no words"

    def test_billing_has_days_not_dates(self):
        assert "days" in SEASONS["billing"]

    def test_seven_seasons_defined(self):
        assert len(SEASONS) == 7  # noqa: PLR2004

    def test_season_names(self):
        expected = {
            "valentine",
            "easter",
            "earth",
            "halloween",
            "reinvent",
            "xmas",
            "billing",
        }
        assert set(SEASONS.keys()) == expected

    def test_all_pics_are_txt_files(self):
        for name, season in SEASONS.items():
            assert season["pic"].endswith(".txt"), f"{name} pic is not a .txt file"


class TestGetCurrentSeason:
    """Verify season detection across dates."""

    def test_valentine_detected(self):
        assert get_current_season(date(2026, 2, 14)) == "valentine"

    def test_valentine_start(self):
        assert get_current_season(date(2026, 2, 12)) == "valentine"

    def test_valentine_end(self):
        assert get_current_season(date(2026, 2, 15)) == "valentine"

    def test_valentine_before(self):
        assert get_current_season(date(2026, 2, 11)) != "valentine"

    def test_valentine_after(self):
        assert get_current_season(date(2026, 2, 16)) != "valentine"

    def test_no_season_mid_march(self):
        assert get_current_season(date(2026, 3, 15)) is None

    def test_halloween_detected(self):
        assert get_current_season(date(2026, 10, 31)) == "halloween"

    def test_xmas_detected(self):
        assert get_current_season(date(2026, 12, 25)) == "xmas"

    def test_reinvent_detected(self):
        assert get_current_season(date(2026, 12, 1)) == "reinvent"

    def test_earth_detected(self):
        assert get_current_season(date(2026, 4, 22)) == "earth"

    def test_easter_detected_2026(self):
        # Easter 2026 is April 5
        assert get_current_season(date(2026, 4, 5)) == "easter"

    def test_easter_not_detected_2027_on_2026_date(self):
        # Easter 2027 is March 28
        assert get_current_season(date(2027, 4, 5)) != "easter"

    def test_billing_first_of_month(self):
        assert get_current_season(date(2026, 6, 1)) == "billing"

    def test_billing_third_of_month(self):
        assert get_current_season(date(2026, 6, 3)) == "billing"

    def test_billing_fourth_not_billing(self):
        assert get_current_season(date(2026, 6, 4)) is None

    def test_calendar_season_beats_billing(self):
        # Dec 1 is both billing and reinvent — reinvent wins
        assert get_current_season(date(2026, 12, 1)) == "reinvent"

    def test_reinvent_nov_25(self):
        assert get_current_season(date(2026, 11, 25)) == "reinvent"

    def test_reinvent_dec_6(self):
        assert get_current_season(date(2026, 12, 6)) == "reinvent"

    def test_easter_week_before(self):
        # Easter 2026 is April 5; 7 days before is March 29
        assert get_current_season(date(2026, 3, 29)) == "easter"

    def test_easter_day_after(self):
        # Easter 2026 is April 5; day after is April 6
        assert get_current_season(date(2026, 4, 6)) == "easter"

    def test_easter_too_early(self):
        # Easter 2026 is April 5; 8 days before is March 28
        assert get_current_season(date(2026, 3, 28)) != "easter"

    def test_easter_too_late(self):
        # Easter 2026 is April 5; 2 days after is April 7
        assert get_current_season(date(2026, 4, 7)) != "easter"

    def test_no_season_regular_day(self):
        assert get_current_season(date(2026, 7, 15)) is None

    def test_defaults_to_today(self):
        result = get_current_season()
        assert result is None or isinstance(result, str)
