from backend.models import Batch, Product


def test_create_product(client, auth_headers):
    response = client.post(
        "/api/v1/products",
        json={
            "hb_code": "HB1001",
            "barcode": "6901234567890",
            "name": "玫瑰精华液",
            "spec": "50ml",
            "unit": "瓶",
            "extra_data": {"brand": "Roseate Lab"},
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["code"] == 201
    assert payload["data"]["product"]["hb_code"] == "HB1001"
    assert payload["data"]["product"]["extra_data"]["brand"] == "Roseate Lab"


def test_inbound_logic(client, auth_headers, app):
    client.post(
        "/api/v1/products",
        json={
            "hb_code": "HB2001",
            "barcode": "6900000000001",
            "name": "草本面霜",
            "spec": "50g",
            "unit": "盒",
        },
        headers=auth_headers,
    )

    response = client.post(
        "/api/v1/inventory/inbound",
        json={
            "barcode": "6900000000001",
            "batch_no": "LOT-001",
            "production_date": "2026-03-01",
            "expiry_date": "2027-03-01",
            "quantity": 24,
            "cost": 39.9,
            "extra_data": {"supplier": "A-Factory"},
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["batch"]["current_quantity"] == 24
    assert payload["data"]["product"]["hb_code"] == "HB2001"
    assert payload["data"]["product"]["total_stock"] == 24

    with app.app_context():
        product = Product.query.filter_by(hb_code="HB2001").first()
        batch = Batch.query.filter_by(hb_code="HB2001").first()

        assert product is not None
        assert batch is not None
        assert batch.batch_no == "LOT-001"
        assert batch.current_quantity == 24
        assert batch.product.hb_code == product.hb_code


def test_batch_merge(client, auth_headers, app):
    client.post(
        "/api/v1/products",
        json={
            "hb_code": "HB3001",
            "barcode": "6900000000002",
            "name": "舒缓喷雾",
            "spec": "120ml",
            "unit": "瓶",
        },
        headers=auth_headers,
    )

    first_inbound = {
        "hb_code": "HB3001",
        "batch_no": "LOT-100",
        "expiry_date": "2027-06-30",
        "quantity": 10,
        "cost": 18.5,
    }
    second_inbound = {
        "hb_code": "HB3001",
        "batch_no": "LOT-101",
        "expiry_date": "2027-06-30",
        "quantity": 6,
        "cost": 18.5,
    }

    first_response = client.post(
        "/api/v1/inventory/inbound",
        json=first_inbound,
        headers=auth_headers,
    )
    second_response = client.post(
        "/api/v1/inventory/inbound",
        json=second_inbound,
        headers=auth_headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.get_json()["data"]["batch"]["current_quantity"] == 16
    assert second_response.get_json()["data"]["product"]["total_stock"] == 16

    with app.app_context():
        batches = Batch.query.filter_by(hb_code="HB3001").all()

        assert len(batches) == 1
        assert batches[0].initial_quantity == 16
        assert batches[0].current_quantity == 16
