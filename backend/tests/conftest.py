import pytest

from backend.app import create_app
from backend.extensions import db


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "JWT_SECRET_KEY": "test-secret-key-with-32-chars-minimum",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "DEFAULT_ADMIN_USERNAME": "admin",
            "DEFAULT_ADMIN_PASSWORD": "password123",
            "DEFAULT_ADMIN_ROLE": "admin",
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
