def test_device_types_list(client):
    response = client.get("/api/device-types")
    assert response.status_code == 200
    families = {item["family"] for item in response.json()}
    assert {"leak", "light", "counter"} <= families


def test_device_type_has_groups(client):
    response = client.get("/api/device-types/light")
    assert response.status_code == 200
    groups = {signal["group"] for signal in response.json()["signals"]}
    assert groups == {"property", "capability", "setting"}


def test_unknown_device_type(client):
    assert client.get("/api/device-types/toaster").status_code == 404


def test_device_crud(client):
    created = client.post("/api/devices", json={"name": " Кухня ", "family": "leak"})
    assert created.status_code == 201
    device = created.json()
    assert device["name"] == "Кухня"

    device_id = device["id"]
    assert client.get(f"/api/devices/{device_id}").status_code == 200

    renamed = client.patch(f"/api/devices/{device_id}", json={"name": "Ванная"})
    assert renamed.json()["name"] == "Ванная"

    assert client.delete(f"/api/devices/{device_id}").status_code == 204
    assert client.get(f"/api/devices/{device_id}").status_code == 404


def test_device_validation(client):
    assert client.post("/api/devices", json={"name": "X", "family": "toaster"}).status_code == 422
    assert client.post("/api/devices", json={"name": "", "family": "leak"}).status_code == 422
