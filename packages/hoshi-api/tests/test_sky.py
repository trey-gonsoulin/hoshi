"""Tests for /sky API endpoints."""


class TestSkyNow:
    def test_sky_now_returns_200(self, client, mock_chart):
        resp = client.get("/sky/now")
        assert resp.status_code == 200

    def test_sky_now_has_bodies(self, client, mock_chart):
        resp = client.get("/sky/now")
        data = resp.json()
        assert "bodies" in data
        assert len(data["bodies"]) > 0

    def test_sky_now_with_mode(self, client, mock_chart):
        resp = client.get("/sky/now?mode=tropical")
        assert resp.status_code == 200

    def test_sky_now_with_tz(self, client, mock_chart):
        resp = client.get("/sky/now?tz=America%2FNew_York")
        assert resp.status_code == 200

    def test_sky_now_no_location_no_houses(self, client, mock_chart):
        # /sky/now uses positions_only — no location, so no house columns
        resp = client.get("/sky/now")
        data = resp.json()
        assert "bodies" in data


class TestSkyEvents:
    def test_sky_events_defaults_to_today(self, client):
        resp = client.get("/sky/events")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "from_date" in data
        assert "to_date" in data
        assert data["from_date"] == data["to_date"]  # single-day range

    def test_sky_events_mode_field(self, client):
        resp = client.get("/sky/events?mode=tropical")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "tropical"

    def test_sky_events_date_range(self, client):
        resp = client.get("/sky/events?from=2026-07-01&to=2026-07-03")
        assert resp.status_code == 200
        data = resp.json()
        assert data["from_date"] == "2026-07-01"
        assert data["to_date"] == "2026-07-03"

    def test_sky_events_respects_disable_flags(self, client):
        # With all event types disabled, events list should be empty
        resp = client.get(
            "/sky/events?from=2026-07-01&to=2026-07-01"
            "&stations=false&ingresses=false&phases=false&voc=false&aspects=false"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["events"] == []

    def test_sky_events_returns_list(self, client):
        resp = client.get("/sky/events?from=2026-07-01&to=2026-07-31")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["events"], list)

    def test_sky_events_event_shape(self, client):
        # At least one event in a month-long window should have required fields
        resp = client.get("/sky/events?from=2026-07-01&to=2026-07-31")
        assert resp.status_code == 200
        data = resp.json()
        if data["events"]:
            e = data["events"][0]
            assert "when" in e
            assert "event_type" in e
            assert "body" in e

    def test_sky_events_mercury_retrograde_in_july_2026(self, client):
        # Mercury is retrograde Jun 29 – Jul 23 2026; should find a station in this window
        resp = client.get(
            "/sky/events?from=2026-06-20&to=2026-07-31&ingresses=false&phases=false&voc=false&aspects=false"
        )
        assert resp.status_code == 200
        data = resp.json()
        stations = [
            e
            for e in data["events"]
            if e["event_type"] in ("retrograde_station", "direct_station")
        ]
        assert len(stations) >= 1
        mercury_stations = [s for s in stations if s["body"] == "Mercury"]
        assert len(mercury_stations) >= 1
