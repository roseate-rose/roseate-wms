import pytest

from backend.app import create_app
from backend.extensions import db


@pytest.fixture
def app(tmp_path):
    frontend_dist_dir = tmp_path / "frontend-dist"
    assets_dir = frontend_dist_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (frontend_dist_dir / "index.html").write_text(
        "<!doctype html><html><body><div id='app'>Roseate WMS Test</div></body></html>",
        encoding="utf-8",
    )
    (assets_dir / "app.js").write_text("console.log('roseate-wms-test');", encoding="utf-8")

    app = create_app(
        {
            "TESTING": True,
            "JWT_SECRET_KEY": "test-secret-key-with-32-chars-minimum",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "DEFAULT_ADMIN_USERNAME": "admin",
            "DEFAULT_ADMIN_PASSWORD": "password123",
            "DEFAULT_ADMIN_ROLE": "admin",
            "FRONTEND_DIST_DIR": str(frontend_dist_dir),
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        from backend.app import ensure_default_admin
        from backend.models import User

        ensure_default_admin(app)

        staff_user = User(username="staff", role="staff")
        staff_user.set_password("staff123")
        staff_user.set_extra_data({"seeded": True})
        db.session.add(staff_user)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "password123"},
    )

    token = response.get_json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def staff_auth_headers(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "staff", "password": "staff123"},
    )

    token = response.get_json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}
