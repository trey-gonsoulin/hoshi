import pytest

from hoshi.aspects import compute_aspects, compute_inter_aspects, fmt_orb
from tests.conftest import make_angle, make_chart, make_planet, make_point


class TestFmtOrb:
    def test_positive(self):
        assert fmt_orb(0.5) == "+0°30'"

    def test_negative(self):
        assert fmt_orb(-1.25) == "-1°15'"

    def test_zero(self):
        assert fmt_orb(0.0) == "+0°00'"

    def test_exact_degree(self):
        assert fmt_orb(2.0) == "+2°00'"


class TestComputeAspects:
    def test_conjunction(self):
        chart = make_chart(planets=[make_planet("sun", 100.0), make_planet("moon", 100.0)])
        aspects = compute_aspects(chart)
        assert len(aspects) == 1
        assert aspects[0].name == "Conjunction"
        assert aspects[0].orb == pytest.approx(0.0)

    def test_opposition(self):
        chart = make_chart(planets=[make_planet("sun", 0.0), make_planet("moon", 180.0)])
        aspects = compute_aspects(chart)
        assert len(aspects) == 1
        assert aspects[0].name == "Opposition"

    def test_trine(self):
        chart = make_chart(planets=[make_planet("sun", 0.0), make_planet("moon", 120.0)])
        aspects = compute_aspects(chart)
        assert len(aspects) == 1
        assert aspects[0].name == "Trine"

    def test_square(self):
        chart = make_chart(planets=[make_planet("sun", 0.0), make_planet("moon", 90.0)])
        aspects = compute_aspects(chart)
        assert len(aspects) == 1
        assert aspects[0].name == "Square"

    def test_sextile(self):
        chart = make_chart(planets=[make_planet("sun", 0.0), make_planet("moon", 60.0)])
        aspects = compute_aspects(chart)
        assert len(aspects) == 1
        assert aspects[0].name == "Sextile"

    def test_no_aspect(self):
        chart = make_chart(planets=[make_planet("sun", 0.0), make_planet("moon", 50.0)])
        aspects = compute_aspects(chart)
        assert len(aspects) == 0

    def test_orb_just_inside(self):
        # Trine = 120, major orb = 4.0; 123.9 is 3.9 away -> inside
        chart = make_chart(planets=[make_planet("sun", 0.0), make_planet("moon", 123.9)])
        aspects = compute_aspects(chart)
        assert len(aspects) == 1
        assert aspects[0].name == "Trine"

    def test_orb_just_outside(self):
        # 124.1 is 4.1 away from 120 -> outside the 4.0 orb
        chart = make_chart(planets=[make_planet("sun", 0.0), make_planet("moon", 124.1)])
        aspects = compute_aspects(chart)
        assert len(aspects) == 0

    def test_shortest_arc(self):
        # 1 and 359 should have a diff of 2 (not 358), giving Conjunction
        chart = make_chart(planets=[make_planet("sun", 1.0), make_planet("moon", 359.0)])
        aspects = compute_aspects(chart)
        assert len(aspects) == 1
        assert aspects[0].name == "Conjunction"

    def test_sorted_by_tightness(self):
        chart = make_chart(
            planets=[
                make_planet("sun", 0.0),
                make_planet("moon", 122.0),  # trine, orb=2
                make_planet("mars", 0.5),  # conjunction, orb=0.5
            ]
        )
        aspects = compute_aspects(chart)
        assert len(aspects) >= 2
        assert abs(aspects[0].orb) <= abs(aspects[1].orb)

    def test_one_aspect_per_pair(self):
        chart = make_chart(planets=[make_planet("sun", 0.0), make_planet("moon", 1.0)])
        aspects = compute_aspects(chart)
        pairs = [(a.body_a, a.body_b) for a in aspects]
        assert len(pairs) == len(set(pairs))

    def test_axis_pair_excluded(self):
        chart = make_chart(
            angles=[make_angle("asc", 0.0), make_angle("dsc", 180.0)]
        )
        aspects = compute_aspects(chart)
        asc_dsc = [a for a in aspects if {a.body_a, a.body_b} == {"Asc", "Dsc"}]
        assert len(asc_dsc) == 0

    def test_axis_pair_nodes_excluded(self):
        chart = make_chart(
            points=[make_point("N.Node", 0.0), make_point("S.Node", 180.0)]
        )
        aspects = compute_aspects(chart)
        node_pairs = [a for a in aspects if {a.body_a, a.body_b} == {"N.Node", "S.Node"}]
        assert len(node_pairs) == 0

    def test_minor_semi_sextile(self):
        chart = make_chart(planets=[make_planet("sun", 0.0), make_planet("moon", 30.0)])
        aspects = compute_aspects(chart)
        assert len(aspects) == 1
        assert aspects[0].name == "Semi-sextile"
        assert aspects[0].kind == "Minor"

    def test_micro_quintile(self):
        chart = make_chart(planets=[make_planet("sun", 0.0), make_planet("moon", 72.0)])
        aspects = compute_aspects(chart)
        assert len(aspects) == 1
        assert aspects[0].name == "Quintile"
        assert aspects[0].kind == "Micro"


class TestComputeInterAspects:
    def test_basic_cross_chart(self):
        chart_a = make_chart(planets=[make_planet("sun", 0.0)])
        chart_b = make_chart(planets=[make_planet("moon", 120.0)])
        aspects = compute_inter_aspects(chart_a, chart_b)
        assert len(aspects) >= 1
        assert aspects[0].name == "Trine"

    def test_no_axis_pair_filtering(self):
        # Inter-aspects should NOT filter axis pairs
        chart_a = make_chart(angles=[make_angle("asc", 0.0)])
        chart_b = make_chart(angles=[make_angle("dsc", 180.0)])
        aspects = compute_inter_aspects(chart_a, chart_b)
        opp = [a for a in aspects if a.name == "Opposition"]
        assert len(opp) >= 1
