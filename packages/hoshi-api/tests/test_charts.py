from unittest.mock import patch


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
