from typer.testing import CliRunner

from hoshi.cli import app
from hoshi.info import ASPECTS, HOUSES, PLANETS, SIGNS

runner = CliRunner()


class TestInfoPlanets:
    def test_list(self):
        result = runner.invoke(app, ["info", "planets"])
        assert result.exit_code == 0
        for name in PLANETS:
            assert name in result.output

    def test_detail(self):
        result = runner.invoke(app, ["info", "planets", "sun"])
        assert result.exit_code == 0
        assert "identity" in result.output
        assert PLANETS["Sun"].meaning[:40] in result.output

    def test_case_insensitive(self):
        result = runner.invoke(app, ["info", "planets", "VENUS"])
        assert result.exit_code == 0
        assert "Venus" in result.output

    def test_prefix_match(self):
        result = runner.invoke(app, ["info", "planets", "jup"])
        assert result.exit_code == 0
        assert "Jupiter" in result.output

    def test_not_found(self):
        result = runner.invoke(app, ["info", "planets", "zzz"])
        assert result.exit_code != 0


class TestInfoSigns:
    def test_list(self):
        result = runner.invoke(app, ["info", "signs"])
        assert result.exit_code == 0
        for name in SIGNS:
            assert name in result.output

    def test_list_includes_extra_columns(self):
        result = runner.invoke(app, ["info", "signs"])
        assert "Element" in result.output
        assert "Modality" in result.output
        assert "Ruler" in result.output

    def test_detail(self):
        result = runner.invoke(app, ["info", "signs", "aries"])
        assert result.exit_code == 0
        assert "Fire" in result.output
        assert "Cardinal" in result.output
        assert "Mars" in result.output

    def test_ophiuchus(self):
        result = runner.invoke(app, ["info", "signs", "ophiuchus"])
        assert result.exit_code == 0
        assert "serpent-bearer" in result.output

    def test_not_found(self):
        result = runner.invoke(app, ["info", "signs", "zzz"])
        assert result.exit_code != 0


class TestInfoAngles:
    def test_list(self):
        result = runner.invoke(app, ["info", "angles"])
        assert result.exit_code == 0
        assert "Ascendant" in result.output
        assert "Midheaven" in result.output

    def test_mc_alias(self):
        result = runner.invoke(app, ["info", "angles", "mc"])
        assert result.exit_code == 0
        assert "Midheaven" in result.output

    def test_ic_alias(self):
        result = runner.invoke(app, ["info", "angles", "ic"])
        assert result.exit_code == 0
        assert "Imum Coeli" in result.output

    def test_dsc_alias(self):
        result = runner.invoke(app, ["info", "angles", "dsc"])
        assert result.exit_code == 0
        assert "Descendant" in result.output

    def test_asc_alias(self):
        result = runner.invoke(app, ["info", "angles", "asc"])
        assert result.exit_code == 0
        assert "Ascendant" in result.output

    def test_rising_alias(self):
        result = runner.invoke(app, ["info", "angles", "rising"])
        assert result.exit_code == 0
        assert "Ascendant" in result.output

    def test_nadir_alias(self):
        result = runner.invoke(app, ["info", "angles", "nadir"])
        assert result.exit_code == 0
        assert "Imum Coeli" in result.output

    def test_not_found(self):
        result = runner.invoke(app, ["info", "angles", "zzz"])
        assert result.exit_code != 0


class TestInfoAspects:
    def test_list(self):
        result = runner.invoke(app, ["info", "aspects"])
        assert result.exit_code == 0
        assert "Conjunction" in result.output
        assert "Trine" in result.output

    def test_detail(self):
        result = runner.invoke(app, ["info", "aspects", "conjunction"])
        assert result.exit_code == 0
        assert "fusion" in result.output

    def test_quincunx_alias(self):
        result = runner.invoke(app, ["info", "aspects", "quincunx"])
        assert result.exit_code == 0
        assert "Inconjunct" in result.output

    def test_sesquisquare_alias(self):
        result = runner.invoke(app, ["info", "aspects", "sesquisquare"])
        assert result.exit_code == 0
        assert "Sesquiquadrate" in result.output

    def test_not_found(self):
        result = runner.invoke(app, ["info", "aspects", "zzz"])
        assert result.exit_code != 0


class TestInfoHouses:
    def test_list(self):
        result = runner.invoke(app, ["info", "houses"])
        assert result.exit_code == 0
        for i in range(1, 13):
            assert f"{i}" in result.output

    def test_detail(self):
        result = runner.invoke(app, ["info", "houses", "1"])
        assert result.exit_code == 0
        assert "1st House" in result.output
        assert "identity" in result.output

    def test_all_houses_have_entries(self):
        for i in range(1, 13):
            result = runner.invoke(app, ["info", "houses", str(i)])
            assert result.exit_code == 0, f"House {i} failed"

    def test_invalid_number(self):
        result = runner.invoke(app, ["info", "houses", "13"])
        assert result.exit_code != 0


class TestInfoPoints:
    def test_list(self):
        result = runner.invoke(app, ["info", "points"])
        assert result.exit_code == 0
        assert "North Node" in result.output
        assert "Lilith" in result.output

    def test_detail(self):
        result = runner.invoke(app, ["info", "points", "fortune"])
        assert result.exit_code == 0
        assert "Lot of Fortune" in result.output

    def test_bml_alias(self):
        result = runner.invoke(app, ["info", "points", "bml"])
        assert result.exit_code == 0
        assert "Black Moon Lilith" in result.output

    def test_north_node_alias(self):
        result = runner.invoke(app, ["info", "points", "north node"])
        assert result.exit_code == 0
        assert "North Node" in result.output

    def test_rahu_alias(self):
        result = runner.invoke(app, ["info", "points", "rahu"])
        assert result.exit_code == 0
        assert "North Node" in result.output

    def test_discipline_alias_for_nemesis(self):
        result = runner.invoke(app, ["info", "points", "discipline"])
        assert result.exit_code == 0
        assert "Nemesis" in result.output

    def test_part_of_fortune_alias(self):
        result = runner.invoke(app, ["info", "points", "part of fortune"])
        assert result.exit_code == 0
        assert "Lot of Fortune" in result.output

    def test_not_found(self):
        result = runner.invoke(app, ["info", "points", "zzz"])
        assert result.exit_code != 0


class TestInfoDataCompleteness:
    def test_all_planets_have_keywords(self):
        for item in PLANETS.values():
            assert len(item.keywords) >= 3

    def test_all_signs_have_keywords(self):
        for item in SIGNS.values():
            assert len(item.keywords) >= 3

    def test_all_signs_have_element_modality_ruler(self):
        for item in SIGNS.values():
            assert item.element
            assert item.modality
            assert item.ruler

    def test_thirteen_signs(self):
        assert len(SIGNS) == 13
        assert "Ophiuchus" in SIGNS

    def test_all_aspects_have_entries(self):
        from hoshi.aspects import ASPECT_DEFS

        for adef in ASPECT_DEFS:
            assert adef.name in ASPECTS, f"Missing info for aspect {adef.name}"

    def test_twelve_houses(self):
        assert len(HOUSES) == 12
        for i in range(1, 13):
            assert i in HOUSES
