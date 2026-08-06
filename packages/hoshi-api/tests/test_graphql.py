"""Tests for the /graphql endpoint."""

GQL = "/graphql"


def _gql(client, query: str, variables: dict | None = None) -> dict:
    payload: dict = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = client.post(GQL, json=payload, headers={"Content-Type": "application/json"})
    assert resp.status_code == 200
    return resp.json()


class TestChart:
    def test_basic_chart(self, client, mock_chart):
        data = _gql(
            client,
            """
            query {
              chart(date: "2000-01-01", time: "12:00", lat: 30.0, lon: -90.0) {
                chart { name when mode houseSystem }
                warnings
                bodies { name sign degree lon rx house symbol signSymbol }
                cusps
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["chart"]
        assert result["chart"]["mode"] == "realsky"
        assert len(result["bodies"]) > 0
        sun = next(b for b in result["bodies"] if b["name"] == "Sun")
        assert sun["symbol"] == "☉"
        assert sun["signSymbol"]

    def test_chart_no_location_warns(self, client, mock_chart):
        data = _gql(
            client,
            """
            query {
              chart(date: "2000-01-01", time: "12:00") {
                warnings
                bodies { name sign }
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["chart"]
        assert any("location unknown" in w for w in result["warnings"])

    def test_chart_with_aspects_and_tallies(self, client, mock_chart):
        data = _gql(
            client,
            """
            query {
              chart(date: "2000-01-01", time: "12:00", lat: 30.0, lon: -90.0,
                    aspects: true, details: true) {
                bodies { name kind }
                aspects { bodyA bodyB name orb kind }
                tallies {
                  elements { fire { primary total } earth { primary total } }
                  modalities { cardinal { primary total } }
                }
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["chart"]
        assert result["tallies"] is not None
        assert result["tallies"]["elements"]["fire"]["primary"] >= 0

    def test_invalid_date_returns_graphql_error(self, client):
        data = _gql(
            client,
            """
            query {
              chart(date: "not-a-date") {
                chart { when }
              }
            }
            """,
        )
        assert "errors" in data

    def test_lat_without_lon_returns_error(self, client):
        data = _gql(
            client,
            """
            query {
              chart(date: "2000-01-01", lat: 30.0) {
                chart { when }
              }
            }
            """,
        )
        assert "errors" in data


class TestCusps:
    def test_cusps(self, client, mock_chart):
        data = _gql(
            client,
            """
            query {
              cusps(date: "2000-01-01", time: "12:00", lat: 30.0, lon: -90.0) {
                houseSystem
                cusps { house sign degree lon }
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["cusps"]
        assert result["houseSystem"] == "porphyry"
        assert len(result["cusps"]) == 12


class TestTransits:
    def test_transits(self, client, mock_chart):
        data = _gql(
            client,
            """
            query {
              transits(
                natal: { date: "2000-01-01", time: "12:00", lat: 30.0, lon: -90.0 }
                date: "2026-01-01"
              ) {
                header { name mode }
                warnings
                transitBodies { name sign degree rx }
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["transits"]
        assert len(result["transitBodies"]) > 0


class TestSkyNow:
    def test_sky_now(self, client, mock_chart):
        data = _gql(
            client,
            """
            query {
              skyNow {
                chart { when mode }
                bodies { name sign degree rx }
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["skyNow"]
        assert result["chart"]["mode"] == "realsky"
        assert len(result["bodies"]) > 0

    def test_sky_now_with_mode(self, client, mock_chart):
        data = _gql(
            client,
            """
            query {
              skyNow(mode: tropical) {
                chart { mode }
              }
            }
            """,
        )
        assert "errors" not in data
        assert data["data"]["skyNow"]["chart"]["mode"] == "tropical"


class TestBatched:
    def test_chart_and_sky_now_in_one_request(self, client, mock_chart):
        """Single HTTP request returns both chart and current sky."""
        data = _gql(
            client,
            """
            query {
              chart(date: "2000-01-01", time: "12:00") {
                chart { when mode }
                bodies { name sign }
              }
              skyNow {
                chart { when mode }
                bodies { name sign }
              }
            }
            """,
        )
        assert "errors" not in data
        assert data["data"]["chart"] is not None
        assert data["data"]["skyNow"] is not None
        assert len(data["data"]["chart"]["bodies"]) > 0
        assert len(data["data"]["skyNow"]["bodies"]) > 0


class TestSkyEvents:
    def test_sky_events_defaults(self, client):
        data = _gql(
            client,
            """
            query {
              skyEvents {
                fromDate
                toDate
                mode
                events { when eventType body detail }
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["skyEvents"]
        assert result["fromDate"] == result["toDate"]
        assert result["mode"] == "realsky"

    def test_sky_events_date_range(self, client):
        data = _gql(
            client,
            """
            query {
              skyEvents(fromDate: "2026-07-01", toDate: "2026-07-03") {
                fromDate
                toDate
                events { when eventType body }
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["skyEvents"]
        assert result["fromDate"] == "2026-07-01"
        assert result["toDate"] == "2026-07-03"

    def test_sky_events_all_disabled_returns_empty(self, client):
        data = _gql(
            client,
            """
            query {
              skyEvents(
                fromDate: "2026-07-01", toDate: "2026-07-01",
                stations: false, ingresses: false, phases: false,
                voc: false, aspects: false
              ) {
                events { when }
              }
            }
            """,
        )
        assert "errors" not in data


class TestComposite:
    def test_basic_composite(self, client, mock_chart):
        data = _gql(
            client,
            """
            query {
              composite(
                chartA: {date: "2000-01-01", time: "12:00", lat: 30.0, lon: -90.0},
                chartB: {date: "1990-06-15", time: "08:30", lat: 40.7, lon: -74.0}
              ) {
                header { nameA nameB dateA dateB mode houseSystem }
                warnings
                bodies { name sign degree lon rx house symbol }
                cusps
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["composite"]
        assert result["header"]["mode"] == "realsky"
        assert result["header"]["dateA"] == "2000-01-01"
        assert result["header"]["dateB"] == "1990-06-15"
        assert result["header"]["houseSystem"] is not None
        assert len(result["bodies"]) > 0
        sun = next(b for b in result["bodies"] if b["name"] == "Sun")
        assert sun["symbol"] == "☉"
        assert 0.0 <= sun["lon"] < 360.0
        assert sun["rx"] is False  # composite bodies are never retrograde
        assert len(result["cusps"]) > 0

    def test_composite_with_aspects(self, client, mock_chart):
        data = _gql(
            client,
            """
            query {
              composite(
                chartA: {date: "2000-01-01", time: "12:00", lat: 30.0, lon: -90.0},
                chartB: {date: "1990-06-15", time: "08:30", lat: 40.7, lon: -74.0},
                aspects: true, details: true
              ) {
                bodies { name sign }
                aspects { bodyA bodyB name orb kind }
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["composite"]
        assert result["aspects"] is not None

    def test_composite_no_location_omits_angles(self, client, mock_chart):
        data = _gql(
            client,
            """
            query {
              composite(
                chartA: {date: "2000-01-01"},
                chartB: {date: "1990-06-15"}
              ) {
                warnings
                bodies { name house }
                cusps
                header { houseSystem }
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["composite"]
        assert len(result["cusps"]) == 0
        assert result["header"]["houseSystem"] is None
        assert all(
            b["house"] is None
            for b in result["bodies"]
            if b["name"] in ("Ascendant", "Midheaven")
        )
        assert any("location unknown" in w for w in result["warnings"])


class TestCompositeTransits:
    def test_basic_composite_transits(self, client, mock_chart):
        data = _gql(
            client,
            """
            query {
              compositeTransits(
                chartA: {date: "2000-01-01", time: "12:00", lat: 30.0, lon: -90.0},
                chartB: {date: "1990-06-15", time: "08:30", lat: 40.7, lon: -74.0},
                date: "2024-06-01", time: "12:00"
              ) {
                header { name transitWhen mode }
                warnings
                transitBodies { name sign degree lon }
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["compositeTransits"]
        assert result["header"]["transitWhen"] != ""
        assert len(result["transitBodies"]) > 0

    def test_composite_transits_no_location_suppresses_houses(self, client, mock_chart):
        data = _gql(
            client,
            """
            query {
              compositeTransits(
                chartA: {date: "2000-01-01"},
                chartB: {date: "1990-06-15"},
                date: "2024-06-01", time: "12:00"
              ) {
                warnings
                transitBodies { name house }
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["compositeTransits"]
        assert any("location unknown" in w for w in result["warnings"])
        assert all(b["house"] is None for b in result["transitBodies"])


class TestCompositeForecast:
    def test_basic_composite_forecast(self, client, mock_chart):
        data = _gql(
            client,
            """
            query {
              compositeForecast(
                chartA: {date: "2000-01-01", time: "12:00", lat: 30.0, lon: -90.0},
                chartB: {date: "1990-06-15", time: "08:30", lat: 40.7, lon: -74.0},
                fromDate: "2024-06-01", toDate: "2024-07-01",
                tier: "all"
              ) {
                header { name fromDate toDate mode tier }
                warnings
                aspects { bodyA signA bodyB signB name }
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["compositeForecast"]
        assert result["header"]["fromDate"] == "2024-06-01"
        assert result["header"]["toDate"] == "2024-07-01"
        assert isinstance(result["aspects"], list)


class TestBirthRange:
    def test_basic_search(self, client):
        data = _gql(
            client,
            """
            query {
              birthRange(
                constraints: [{planet: "sun", sign: "Aries"}],
                fromDate: "2000-03-20", toDate: "2000-04-20"
              ) {
                constraints mode searchStart searchEnd stepHours
                windows { start end durationDays }
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["birthRange"]
        assert result["mode"] == "realsky"
        assert len(result["constraints"]) == 1
        assert len(result["windows"]) > 0
        assert result["windows"][0]["durationDays"] > 0

    def test_no_windows_in_range(self, client):
        data = _gql(
            client,
            """
            query {
              birthRange(
                constraints: [{planet: "sun", sign: "Aries"}],
                fromDate: "2000-06-01", toDate: "2000-06-30"
              ) {
                windows { start end durationDays }
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["birthRange"]
        assert result["windows"] == []

    def test_invalid_planet_returns_error(self, client):
        data = _gql(
            client,
            """
            query {
              birthRange(
                constraints: [{planet: "chiron", sign: "Aries"}],
                fromDate: "2000-01-01", toDate: "2000-12-31"
              ) {
                windows { start end durationDays }
              }
            }
            """,
        )
        assert "errors" in data

    def test_chart_with_birth_windows(self, client, mock_chart):
        data = _gql(
            client,
            """
            query {
              chart(
                date: "2000-03-25",
                birthWindows: [
                  {start: "2000-03-20T00:00:00", end: "2000-04-20T00:00:00"}
                ]
              ) {
                warnings
                bodies { name sign }
                placementDist { pid fracs { sign fraction } }
              }
            }
            """,
        )
        assert "errors" not in data
        result = data["data"]["chart"]
        assert any("window" in w.lower() for w in result["warnings"])
        assert result["placementDist"] is not None
        assert len(result["placementDist"]) > 0
