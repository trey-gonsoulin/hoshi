from hoshi.dignities import (
    chart_ruler,
    dignity_for,
    element_modality_tally,
    natal_sensitivity,
)
from tests.conftest import make_angle, make_chart, make_planet, make_point


class TestDignityFor:
    def test_domicile(self):
        assert dignity_for("mars", "Aries") == "domicile"

    def test_exaltation(self):
        assert dignity_for("sun", "Aries") == "exaltation"

    def test_detriment(self):
        assert dignity_for("venus", "Aries") == "detriment"

    def test_fall(self):
        assert dignity_for("saturn", "Aries") == "fall"

    def test_no_dignity(self):
        assert dignity_for("neptune", "Aries") is None

    def test_case_insensitive(self):
        assert dignity_for("Mars", "Aries") == "domicile"
        assert dignity_for("MARS", "Aries") == "domicile"

    def test_ophiuchus_chiron(self):
        assert dignity_for("chiron", "Ophiuchus") == "domicile"

    def test_unknown_sign(self):
        assert dignity_for("mars", "FakeSign") is None

    def test_priority_domicile_over_exaltation(self):
        # Mercury has both domicile and exaltation in Virgo; domicile wins
        assert dignity_for("mercury", "Virgo") == "domicile"

    def test_multiple_domicile_rulers(self):
        assert dignity_for("pluto", "Scorpio") == "domicile"
        assert dignity_for("mars", "Scorpio") == "domicile"


class TestElementModalityTally:
    def test_counts_elements(self):
        # Aries (lon=15) = Fire, Taurus (lon=45) = Earth, Cancer (lon=105) = Water
        chart = make_chart(
            planets=[
                make_planet("sun", 15.0),
                make_planet("moon", 45.0),
                make_planet("mars", 105.0),
            ]
        )
        tally = element_modality_tally(chart, "tropical")
        assert tally["primary"]["elements"]["Fire"] == 1
        assert tally["primary"]["elements"]["Earth"] == 1
        assert tally["primary"]["elements"]["Water"] == 1

    def test_counts_modalities(self):
        # Aries = Cardinal, Taurus = Fixed, Gemini = Mutable
        chart = make_chart(
            planets=[
                make_planet("sun", 15.0),  # Aries - Cardinal
                make_planet("moon", 45.0),  # Taurus - Fixed
                make_planet("mars", 75.0),  # Gemini - Mutable
            ]
        )
        tally = element_modality_tally(chart, "tropical")
        assert tally["primary"]["modalities"]["Cardinal"] == 1
        assert tally["primary"]["modalities"]["Fixed"] == 1
        assert tally["primary"]["modalities"]["Mutable"] == 1

    def test_primary_vs_total(self):
        chart = make_chart(
            planets=[make_planet("sun", 15.0)],
            angles=[make_angle("asc", 45.0)],
            points=[make_point("N.Node", 75.0)],
        )
        tally = element_modality_tally(chart, "tropical")
        assert tally["primary"]["elements"].get("Fire", 0) == 1
        total_count = sum(tally["total"]["elements"].values())
        primary_count = sum(tally["primary"]["elements"].values())
        assert total_count > primary_count

    def test_ophiuchus_realsky(self):
        # Ophiuchus spans 247.74-266.55; lon=250 is in Ophiuchus
        chart = make_chart(planets=[make_planet("sun", 250.0)])
        tally = element_modality_tally(chart, "realsky")
        assert tally["primary"]["elements"]["Water"] == 1
        assert tally["primary"]["modalities"]["Fixed"] == 1


class TestChartRuler:
    def test_aries_mars(self):
        assert chart_ruler("Aries") == "mars"

    def test_cancer_moon(self):
        assert chart_ruler("Cancer") == "moon"

    def test_leo_sun(self):
        assert chart_ruler("Leo") == "sun"

    def test_ophiuchus_chiron(self):
        assert chart_ruler("Ophiuchus") == "chiron"

    def test_scorpio_returns_first_ruler(self):
        # Scorpio has pluto + mars; domicile list is ["pluto", "mars"]
        assert chart_ruler("Scorpio") == "pluto"

    def test_unknown_sign_returns_none(self):
        assert chart_ruler("FakeSign") is None


class TestNatalSensitivity:
    def test_sun_primary_always(self):
        assert natal_sensitivity("Sun") == "primary"

    def test_moon_primary_always(self):
        assert natal_sensitivity("Moon") == "primary"

    def test_asc_primary_with_location(self):
        assert natal_sensitivity("Ascendant", location_known=True) == "primary"

    def test_asc_tertiary_without_location(self):
        assert natal_sensitivity("Ascendant", location_known=False) == "tertiary"

    def test_mc_primary_with_location(self):
        assert natal_sensitivity("Midheaven", location_known=True) == "primary"

    def test_mc_tertiary_without_location(self):
        assert natal_sensitivity("Midheaven", location_known=False) == "tertiary"

    def test_chart_ruler_primary_with_location(self):
        # Mars rules Aries; if chart_ruler_pid="mars", Mars → primary
        assert (
            natal_sensitivity("Mars", chart_ruler_pid="mars", location_known=True)
            == "primary"
        )

    def test_chart_ruler_not_primary_without_location(self):
        assert (
            natal_sensitivity("Mars", chart_ruler_pid="mars", location_known=False)
            == "secondary"
        )

    def test_mercury_secondary(self):
        assert natal_sensitivity("Mercury") == "secondary"

    def test_venus_secondary(self):
        assert natal_sensitivity("Venus") == "secondary"

    def test_mars_secondary_by_default(self):
        assert natal_sensitivity("Mars") == "secondary"

    def test_jupiter_tertiary(self):
        assert natal_sensitivity("Jupiter") == "tertiary"

    def test_saturn_tertiary(self):
        assert natal_sensitivity("Saturn") == "tertiary"

    def test_node_tertiary(self):
        assert natal_sensitivity("N.Node") == "tertiary"

    def test_case_insensitive_sun(self):
        assert natal_sensitivity("sun") == "primary"
