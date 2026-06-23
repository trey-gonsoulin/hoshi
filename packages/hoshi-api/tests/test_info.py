class TestInfoList:
    def test_list_planets(self, client):
        resp = client.get("/info/planets")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) > 0
        assert data["title"] == "Planets"

    def test_list_signs(self, client):
        resp = client.get("/info/signs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 13

    def test_list_angles(self, client):
        resp = client.get("/info/angles")
        assert resp.status_code == 200

    def test_list_aspects(self, client):
        resp = client.get("/info/aspects")
        assert resp.status_code == 200

    def test_list_houses(self, client):
        resp = client.get("/info/houses")
        assert resp.status_code == 200

    def test_list_points(self, client):
        resp = client.get("/info/points")
        assert resp.status_code == 200

    def test_invalid_category(self, client):
        resp = client.get("/info/invalid")
        assert resp.status_code == 422


class TestInfoDetail:
    def test_planet_detail(self, client):
        resp = client.get("/info/planets/sun")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Sun"
        assert len(data["keywords"]) > 0
        assert data["meaning"] != ""

    def test_sign_detail(self, client):
        resp = client.get("/info/signs/aries")
        assert resp.status_code == 200
        data = resp.json()
        assert data["element"] is not None

    def test_house_detail(self, client):
        resp = client.get("/info/houses/1")
        assert resp.status_code == 200

    def test_planet_not_found(self, client):
        resp = client.get("/info/planets/notaplanet")
        assert resp.status_code == 404

    def test_house_not_found(self, client):
        resp = client.get("/info/houses/99")
        assert resp.status_code == 404

    def test_fuzzy_match(self, client):
        resp = client.get("/info/planets/ven")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Venus"
