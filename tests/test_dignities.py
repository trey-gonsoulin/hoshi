from hoshi.dignities import dignity_for, element_modality_tally
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
