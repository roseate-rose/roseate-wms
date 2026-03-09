def test_protected_inventory_endpoint_requires_token(client):
    response = client.get("/api/v1/inventory/test")

    assert response.status_code == 401
    assert response.get_json() == {
        "code": 401,
        "data": {},
        "msg": "Missing Authorization Header",
    }


def test_login_returns_jwt_token_and_allows_access(client):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "password123"},
    )

    assert login_response.status_code == 200

    login_payload = login_response.get_json()
    assert login_payload["code"] == 200
    assert login_payload["msg"] == "success"
    assert login_payload["data"]["user"]["username"] == "admin"
    assert login_payload["data"]["token"]

    token = login_payload["data"]["token"]

    protected_response = client.get(
        "/api/v1/inventory/test",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert protected_response.status_code == 200
    assert protected_response.get_json()["data"]["current_user"]["role"] == "admin"


def test_app_bootstraps_default_admin(app):
    with app.app_context():
        from backend.models import User

        user = User.query.filter_by(username="admin").first()

        assert user is not None
        assert user.role == "admin"
        assert user.check_password("password123")


def test_flask_serves_built_frontend_assets(client):
    index_response = client.get("/")
    spa_response = client.get("/products/HB1001")
    asset_response = client.get("/assets/app.js")

    assert index_response.status_code == 200
    assert b"Roseate WMS Test" in index_response.data
    assert spa_response.status_code == 200
    assert b"Roseate WMS Test" in spa_response.data
    assert asset_response.status_code == 200
    assert b"roseate-wms-test" in asset_response.data


def test_unknown_api_and_missing_asset_return_404(client):
    missing_api_response = client.get("/api/v1/unknown")
    missing_asset_response = client.get("/assets/missing.js")

    assert missing_api_response.status_code == 404
    assert missing_api_response.get_json()["msg"] == "resource not found"
    assert missing_asset_response.status_code == 404
    assert missing_asset_response.get_json()["msg"] == "static asset not found"
