import pytest

from hoshi.points import (
    HERMETIC_LOT_NAMES,
    LunarElements,
    _parse_horizons_elements,
    hermetic_lots,
)


class TestLunarElementsProperties:
    def test_north_node(self):
        el = LunarElements(om=100.0, w=50.0)
        assert el.north_node == pytest.approx(100.0)

    def test_south_node(self):
        el = LunarElements(om=100.0, w=50.0)
        assert el.south_node == pytest.approx(280.0)

    def test_lilith(self):
        el = LunarElements(om=100.0, w=50.0)
        # (100 + 50 + 180) % 360 = 330
        assert el.lilith == pytest.approx(330.0)

    def test_north_node_wrap(self):
        el = LunarElements(om=370.0, w=0.0)
        assert el.north_node == pytest.approx(10.0)

    def test_lilith_wrap(self):
        el = LunarElements(om=300.0, w=200.0)
        # (300 + 200 + 180) % 360 = 680 % 360 = 320
        assert el.lilith == pytest.approx(320.0)

    def test_south_node_opposite(self):
        el = LunarElements(om=10.0, w=0.0)
        assert el.south_node == pytest.approx(190.0)


class TestParseHorizonsElements:
    VALID_RESPONSE = """\
some header
$$SOE
 2451545.0, 2000-Jan-01, 0.05, 362000, 5.14, 125.678, 45.321, 2451500, 0.005, 15.0, 30.0, 384400, 405500, 27.32,
$$EOE
footer"""

    def test_valid(self):
        om, w = _parse_horizons_elements(self.VALID_RESPONSE)
        assert om == pytest.approx(125.678)
        assert w == pytest.approx(45.321)

    def test_missing_markers(self):
        with pytest.raises(RuntimeError, match="missing"):
            _parse_horizons_elements("no markers")

    def test_no_data(self):
        with pytest.raises(RuntimeError, match="no data"):
            _parse_horizons_elements("$$SOE\n$$EOE")


class TestHermeticLots:
    def test_all_seven_keys(self):
        result = hermetic_lots(0, 100, 200, 50, 60, 70, 80, 90)
        assert set(result.keys()) == set(HERMETIC_LOT_NAMES)

    def test_day_chart(self):
        # Day: (sun - asc) % 360 >= 180
        # asc=0, sun=100 -> (100-0)%360=100, NOT >= 180 -> night
        # asc=0, sun=200 -> (200-0)%360=200, >= 180 -> day
        asc, sun, moon = 0.0, 200.0, 50.0
        result = hermetic_lots(asc, sun, moon, 0, 0, 0, 0, 0)
        # Day fortune = (asc + moon - sun) % 360 = (0 + 50 - 200) % 360 = 210
        assert result["Fortune"] == pytest.approx(210.0)

    def test_night_chart(self):
        # asc=0, sun=100 -> (100-0)%360=100, < 180 -> night
        asc, sun, moon = 0.0, 100.0, 50.0
        result = hermetic_lots(asc, sun, moon, 0, 0, 0, 0, 0)
        # Night fortune = (asc + sun - moon) % 360 = (0 + 100 - 50) % 360 = 50
        assert result["Fortune"] == pytest.approx(50.0)

    def test_fortune_spirit_complementary(self):
        asc, sun, moon = 0.0, 200.0, 50.0
        result = hermetic_lots(asc, sun, moon, 0, 0, 0, 0, 0)
        # Day: Fortune = asc+moon-sun, Spirit = asc+sun-moon (swapped)
        assert result["Fortune"] == pytest.approx((asc + moon - sun) % 360)
        assert result["Spirit"] == pytest.approx((asc + sun - moon) % 360)

    def test_day_night_boundary(self):
        # Exactly at boundary: (sun - asc) % 360 = 180 -> day (>= check)
        asc, sun = 0.0, 180.0
        result = hermetic_lots(asc, sun, 50.0, 0, 0, 0, 0, 0)
        # Day formula: Fortune = (asc + moon - sun) % 360
        assert result["Fortune"] == pytest.approx((0 + 50 - 180) % 360)

    def test_wrap(self):
        result = hermetic_lots(350.0, 200.0, 300.0, 0, 0, 0, 0, 0)
        for v in result.values():
            assert 0.0 <= v < 360.0
