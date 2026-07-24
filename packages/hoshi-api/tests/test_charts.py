from unittest.mock import patch


class TestBirthRange:
    def test_basic_search(self, client):
        resp = client.post(
            "/charts/birthrange",
            json={
                "constraints": [{"planet": "sun", "sign": "Aries"}],
                "from_date": "2000-03-20",
                "to_date": "2000-04-20",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["windows"]) > 0
        assert data["mode"] == "realsky"
        assert data["windows"][0]["duration_days"] > 0

    def test_no_windows_in_range(self, client):
        resp = client.post(
            "/charts/birthrange",
            json={
                "constraints": [{"planet": "sun", "sign": "Aries"}],
                "from_date": "2000-06-01",
                "to_date": "2000-06-30",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["windows"] == []

    def test_invalid_planet_returns_422(self, client):
        resp = client.post(
            "/charts/birthrange",
            json={
                "constraints": [{"planet": "chiron", "sign": "Aries"}],
                "from_date": "2000-01-01",
                "to_date": "2000-12-31",
            },
        )
        assert resp.status_code == 422


class TestComputeChart:
    def test_compute(self, client, mock_chart):
        resp = client.post(
            "/charts/compute",
            json={
                "date": "2000-01-01",
                "time": "12:00",
                "lat": 30.0,
                "lon": -90.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["bodies"]) > 0
        # Every body entry should carry a symbol glyph and a sign_symbol glyph.
        sun = next(b for b in data["bodies"] if b["name"] == "Sun")
        assert sun["symbol"] == "☉"
        assert sun["sign_symbol"]  # non-empty for any valid sign

    def test_compute_no_location(self, client, mock_chart):
        resp = client.post(
            "/charts/compute",
            json={
                "date": "2000-01-01",
                "time": "12:00",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert any("location unknown" in w for w in data["warnings"])

    def test_compute_lat_without_lon(self, client, mock_chart):
        resp = client.post(
            "/charts/compute",
            json={
                "date": "2000-01-01",
                "lat": 30.0,
            },
        )
        assert resp.status_code == 422


class TestCusps:
    def test_cusps(self, client, mock_chart):
        resp = client.post(
            "/charts/cusps",
            json={
                "date": "2000-01-01",
                "time": "12:00",
                "lat": 30.0,
                "lon": -90.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["house_system"] == "porphyry"
        assert len(data["cusps"]) == 12


class TestTransits:
    def test_transits(self, client, mock_chart):
        with patch("hoshi.chart.Chart.positions_only", return_value=mock_chart):
            resp = client.post(
                "/charts/transits",
                json={
                    "natal": {
                        "date": "2000-01-01",
                        "time": "12:00",
                        "lat": 30.0,
                        "lon": -90.0,
                    },
                    "date": "2025-06-01",
                    "time": "12:00",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["transit_bodies"]) > 0


class TestCompare:
    def test_compare(self, client, mock_chart):
        resp = client.post(
            "/charts/compare",
            json={
                "chart_a": {
                    "date": "2000-01-01",
                    "time": "12:00",
                    "lat": 30.0,
                    "lon": -90.0,
                },
                "chart_b": {
                    "date": "1990-05-15",
                    "time": "08:30",
                    "lat": 40.7,
                    "lon": -74.0,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["bodies_a"]) > 0
        assert len(data["bodies_b"]) > 0
