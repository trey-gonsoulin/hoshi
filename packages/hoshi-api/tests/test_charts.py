from unittest.mock import patch

from tests.conftest import SAMPLE_CI, SAMPLE_CI_MINIMAL


class TestListCharts:
    def test_empty(self, client):
        with patch("hoshi.store.list_all", return_value=[]):
            resp = client.get("/charts")
        assert resp.status_code == 200
        assert resp.json()["charts"] == []

    def test_with_charts(self, client):
        with patch("hoshi.store.list_all", return_value=[SAMPLE_CI]):
            resp = client.get("/charts")
        assert resp.status_code == 200
        charts = resp.json()["charts"]
        assert len(charts) == 1
        assert charts[0]["name"] == "test"


class TestCreateChart:
    def test_create(self, client, mock_chart):
        with patch("hoshi_api.routes.charts.store.save") as save:
            resp = client.post(
                "/charts",
                json={
                    "name": "test",
                    "date": "2000-01-01",
                    "time": "12:00",
                    "lat": 30.0,
                    "lon": -90.0,
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["chart"]["name"] == "test"
        assert len(data["bodies"]) > 0
        save.assert_called_once()

    def test_create_conflict(self, client, mock_chart):
        with patch(
            "hoshi_api.routes.charts.store.save", side_effect=FileExistsError("exists")
        ):
            resp = client.post(
                "/charts",
                json={
                    "name": "test",
                    "date": "2000-01-01",
                    "lat": 30.0,
                    "lon": -90.0,
                },
            )
        assert resp.status_code == 409

    def test_create_lat_without_lon(self, client, mock_chart):
        with patch("hoshi_api.routes.charts.store.save"):
            resp = client.post(
                "/charts",
                json={
                    "name": "test",
                    "date": "2000-01-01",
                    "lat": 30.0,
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


class TestShowChart:
    def test_show(self, client, mock_chart):
        with patch("hoshi_api.routes.charts.store.load", return_value=SAMPLE_CI):
            resp = client.get("/charts/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["chart"]["name"] == "test"

    def test_show_not_found(self, client):
        with patch(
            "hoshi_api.routes.charts.store.load", side_effect=FileNotFoundError("nope")
        ):
            resp = client.get("/charts/missing")
        assert resp.status_code == 404

    def test_show_with_details(self, client, mock_chart):
        with patch("hoshi_api.routes.charts.store.load", return_value=SAMPLE_CI):
            resp = client.get("/charts/test?details=true")
        assert resp.status_code == 200
        data = resp.json()
        kinds = {b["kind"] for b in data["bodies"]}
        assert "Node" in kinds or "Point" in kinds

    def test_show_with_aspects(self, client, mock_chart):
        with patch("hoshi_api.routes.charts.store.load", return_value=SAMPLE_CI):
            resp = client.get("/charts/test?aspects=true")
        assert resp.status_code == 200
        assert "aspects" in resp.json()


class TestDeleteChart:
    def test_delete(self, client):
        with patch(
            "hoshi_api.routes.charts.store.delete", return_value="charts/test.json"
        ):
            resp = client.delete("/charts/test")
        assert resp.status_code == 200

    def test_delete_not_found(self, client):
        with patch(
            "hoshi_api.routes.charts.store.delete",
            side_effect=FileNotFoundError("nope"),
        ):
            resp = client.delete("/charts/missing")
        assert resp.status_code == 404


class TestCusps:
    def test_cusps(self, client, mock_chart):
        with patch("hoshi_api.routes.charts.store.load", return_value=SAMPLE_CI):
            resp = client.get("/charts/test/cusps")
        assert resp.status_code == 200
        data = resp.json()
        assert data["house_system"] == "porphyry"
        assert len(data["cusps"]) == 12

    def test_cusps_no_time(self, client, mock_chart):
        with patch(
            "hoshi_api.routes.charts.store.load", return_value=SAMPLE_CI_MINIMAL
        ):
            resp = client.get("/charts/notime/cusps")
        assert resp.status_code == 422


class TestTransits:
    def test_transits(self, client, mock_chart):
        with patch("hoshi_api.routes.charts.store.load", return_value=SAMPLE_CI):
            with patch("hoshi.chart.Chart.positions_only", return_value=mock_chart):
                resp = client.get("/charts/test/transits?date=2025-06-01&time=12:00")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["transit_bodies"]) > 0

    def test_transits_not_found(self, client):
        with patch(
            "hoshi_api.routes.charts.store.load", side_effect=FileNotFoundError("nope")
        ):
            resp = client.get("/charts/missing/transits")
        assert resp.status_code == 404


class TestCompare:
    def test_compare(self, client, mock_chart):
        with patch("hoshi_api.routes.charts.store.load", return_value=SAMPLE_CI):
            resp = client.get("/charts/chart_a/compare/chart_b")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["bodies_a"]) > 0
        assert len(data["bodies_b"]) > 0
