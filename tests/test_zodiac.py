import pytest

from hoshi.zodiac import (
    SIGN_ATTRS,
    TROP_ABBR,
    TROP_NAMES,
    TROP_SIGNS,
    Placement,
    ZodiacMode,
    format_deg,
    n360,
)


class TestSignTable:
    def test_derived_lists_match_table(self):
        assert TROP_NAMES == [s.name for s in TROP_SIGNS]
        assert TROP_ABBR == [s.abbr for s in TROP_SIGNS]

    def test_twelve_tropical_signs(self):
        assert len(TROP_SIGNS) == 12

    def test_sign_attrs_covers_thirteen_realsky_signs(self):
        assert len(SIGN_ATTRS) == 13
        assert SIGN_ATTRS["Aries"] == ("Fire", "Cardinal")
        assert SIGN_ATTRS["Ophiuchus"] == ("Water", "Fixed")


class TestForMode:
    def test_realsky_dispatch_matches_realsky(self):
        assert Placement.for_mode(100.0, "realsky") == Placement.realsky(100.0)

    def test_realsky_threads_precession(self):
        assert Placement.for_mode(29.5, "realsky", precession=1.0).name == "Pisces"

    def test_tropical_dispatch(self):
        assert Placement.for_mode(100.0, "tropical") == Placement.tropical(100.0)

    def test_vedic_threads_ayanamsa(self):
        assert Placement.for_mode(100.0, "vedic", ayanamsa=24.0) == Placement.vedic(
            100.0, 24.0
        )

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown zodiac mode"):
            Placement.for_mode(100.0, "bogus")

    def test_accepts_zodiac_mode_enum(self):
        assert Placement.for_mode(100.0, ZodiacMode.tropical) == Placement.for_mode(
            100.0, "tropical"
        )

    def test_enum_value_equals_string(self):
        assert ZodiacMode.realsky == "realsky"
        assert list(ZodiacMode) == [
            ZodiacMode.realsky,
            ZodiacMode.tropical,
            ZodiacMode.vedic,
        ]


class TestN360:
    def test_positive_wrap(self):
        assert n360(370.0) == pytest.approx(10.0)

    def test_negative(self):
        assert n360(-10.0) == pytest.approx(350.0)

    def test_zero(self):
        assert n360(0.0) == pytest.approx(0.0)

    def test_exact_360(self):
        assert n360(360.0) == pytest.approx(0.0)

    def test_large(self):
        assert n360(720.5) == pytest.approx(0.5)


class TestFormatDeg:
    def test_zero(self):
        assert format_deg(0.0) == "00°00'"

    def test_integer(self):
        assert format_deg(15.0) == "15°00'"

    def test_fractional_half(self):
        assert format_deg(10.5) == "10°30'"

    def test_near_full(self):
        assert format_deg(29.99) == "29°59'"

    def test_negative_clamped(self):
        assert format_deg(-5.0) == "00°00'"


class TestTropical:
    @pytest.mark.parametrize(
        "lon, expected_name",
        [
            (0.0, "Aries"),
            (30.0, "Taurus"),
            (60.0, "Gemini"),
            (90.0, "Cancer"),
            (120.0, "Leo"),
            (150.0, "Virgo"),
            (180.0, "Libra"),
            (210.0, "Scorpio"),
            (240.0, "Sagittarius"),
            (270.0, "Capricorn"),
            (300.0, "Aquarius"),
            (330.0, "Pisces"),
        ],
    )
    def test_all_twelve_signs(self, lon, expected_name):
        p = Placement.tropical(lon)
        assert p.name == expected_name
        assert p.deg == pytest.approx(0.0)

    def test_mid_sign(self):
        p = Placement.tropical(15.0)
        assert p.name == "Aries"
        assert p.deg == pytest.approx(15.0)

    def test_end_of_pisces(self):
        p = Placement.tropical(359.99)
        assert p.name == "Pisces"
        assert p.deg == pytest.approx(29.99)

    def test_wraps_past_360(self):
        p = Placement.tropical(361.0)
        assert p.name == "Aries"
        assert p.deg == pytest.approx(1.0)


class TestVedic:
    def test_offset_shifts_sign(self):
        p = Placement.vedic(30.0, ayanamsa=24.0)
        assert p.name == "Aries"
        assert p.deg == pytest.approx(6.0)

    def test_wraps_negative(self):
        p = Placement.vedic(10.0, ayanamsa=24.0)
        # n360(10 - 24) = n360(-14) = 346 -> Pisces at 346 - 330 = 16
        assert p.name == "Pisces"
        assert p.deg == pytest.approx(16.0)

    def test_matches_tropical_when_zero(self):
        p_vedic = Placement.vedic(45.0, ayanamsa=0.0)
        p_trop = Placement.tropical(45.0)
        assert p_vedic.name == p_trop.name
        assert p_vedic.deg == pytest.approx(p_trop.deg)


class TestRealsky:
    def test_aries(self):
        p = Placement.realsky(40.0)
        assert p.name == "Aries"
        assert p.deg == pytest.approx(40.0 - 29.0)

    def test_ophiuchus(self):
        p = Placement.realsky(250.0)
        assert p.name == "Ophiuchus"
        assert p.deg == pytest.approx(250.0 - 247.74)

    def test_scorpio_narrow(self):
        p = Placement.realsky(244.0)
        assert p.name == "Scorpio"
        assert p.deg == pytest.approx(244.0 - 241.03)

    def test_pisces_before_wrap(self):
        p = Placement.realsky(355.0)
        assert p.name == "Pisces"
        assert p.deg == pytest.approx(355.0 - 351.65)

    def test_pisces_after_wrap(self):
        p = Placement.realsky(5.0)
        assert p.name == "Pisces"
        assert p.deg == pytest.approx((360.0 - 351.65) + 5.0)

    def test_with_precession(self):
        # With 1 degree of precession, boundaries shift by 1 degree
        # lon=30 without precession is Aries (29.00-53.41)
        # With precession=1, Aries boundary becomes 30.00-54.41
        # So lon=29.5 should now be in Pisces instead of Aries
        p_no_prec = Placement.realsky(29.5)
        assert p_no_prec.name == "Aries"

        p_with_prec = Placement.realsky(29.5, precession=1.0)
        assert p_with_prec.name == "Pisces"

    def test_boundary_exact(self):
        # Exactly at the Aries lo boundary
        p = Placement.realsky(29.0)
        assert p.name == "Aries"
        assert p.deg == pytest.approx(0.0)
