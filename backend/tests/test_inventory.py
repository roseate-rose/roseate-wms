import csv
from datetime import date, timedelta
from io import BytesIO
from io import StringIO

from backend.extensions import db
from backend.models import (
    Batch,
    ChannelMapping,
    InboundLine,
    InboundReceipt,
    InventoryTransaction,
    OrderAllocation,
    SalesOrder,
    Product,
)


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


def test_unit_conversion(client, auth_headers, app):
    client.post(
        "/api/v1/products",
        json={
            "hb_code": "HB4001",
            "barcode": "6900000000003",
            "name": "修护安瓶",
            "spec": "10ml*10",
            "unit": "支",
            "base_unit": "支",
            "purchase_unit": "盒",
            "conversion_rate": 10,
        },
        headers=auth_headers,
    )

    response = client.post(
        "/api/v1/inventory/inbound",
        json={
            "hb_code": "HB4001",
            "batch_no": "BOX-001",
            "expiry_date": "2027-08-01",
            "quantity": 1,
            "cost": 199.0,
            "unit_type": "purchase",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["batch"]["current_quantity"] == 10
    assert response.get_json()["data"]["product"]["total_stock"] == 10

    with app.app_context():
        batch = Batch.query.filter_by(hb_code="HB4001").first()
        assert batch is not None
        assert batch.initial_quantity == 10
        assert batch.current_quantity == 10


def test_reservation_logic(client, auth_headers, app):
    client.post(
        "/api/v1/products",
        json={
            "hb_code": "HB5001",
            "barcode": "6900000000004",
            "name": "玻尿酸精华",
            "spec": "30ml",
            "unit": "支",
            "base_unit": "支",
            "purchase_unit": "盒",
            "conversion_rate": 1,
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/inventory/inbound",
        json={
            "hb_code": "HB5001",
            "batch_no": "RES-001",
            "expiry_date": "2027-09-01",
            "quantity": 12,
            "cost": 30.0,
            "unit_type": "base",
        },
        headers=auth_headers,
    )

    reserve_response = client.post(
        "/api/v1/inventory/reserve",
        json={"hb_code": "HB5001", "quantity": 5},
        headers=auth_headers,
    )

    assert reserve_response.status_code == 200
    reserve_payload = reserve_response.get_json()
    assert reserve_payload["data"]["product"]["total_stock"] == 12
    assert reserve_payload["data"]["product"]["reserved_stock"] == 5
    assert reserve_payload["data"]["product"]["sellable_stock"] == 7

    product_response = client.get("/api/v1/products?q=HB5001", headers=auth_headers)
    item = product_response.get_json()["data"]["items"][0]
    assert item["total_stock"] == 12
    assert item["reserved_stock"] == 5
    assert item["sellable_stock"] == 7

    with app.app_context():
        batch = Batch.query.filter_by(hb_code="HB5001").first()
        assert batch.current_quantity == 12
        assert batch.reserved_quantity == 5


def test_channel_lookup(client, auth_headers, app):
    client.post(
        "/api/v1/products",
        json={
            "hb_code": "HB6001",
            "barcode": "6900000000005",
            "name": "积雪草面膜",
            "spec": "5片",
            "unit": "片",
            "base_unit": "片",
            "purchase_unit": "盒",
            "conversion_rate": 5,
        },
        headers=auth_headers,
    )

    mapping_response = client.post(
        "/api/v1/channel-mappings",
        json={
            "channel_name": "抖音",
            "external_sku_id": "DY-889900",
            "hb_code": "HB6001",
            "extra_data": {"shop_name": "官方旗舰店"},
        },
        headers=auth_headers,
    )
    lookup_response = client.get(
        "/api/v1/channel-mappings/lookup?channel_name=%E6%8A%96%E9%9F%B3&external_sku_id=DY-889900",
        headers=auth_headers,
    )

    assert mapping_response.status_code == 201
    assert lookup_response.status_code == 200
    assert lookup_response.get_json()["data"]["hb_code"] == "HB6001"

    with app.app_context():
        mapping = ChannelMapping.query.filter_by(external_sku_id="DY-889900").first()
        assert mapping is not None
        assert mapping.channel_name == "抖音"


def test_csv_import_with_missing_date(client, auth_headers, app):
    client.post(
        "/api/v1/products",
        json={
            "hb_code": "HB7001",
            "barcode": "6900000000006",
            "name": "夜间修护乳",
            "spec": "60ml",
            "unit": "支",
            "base_unit": "支",
            "purchase_unit": "盒",
            "conversion_rate": 6,
        },
        headers=auth_headers,
    )

    csv_content = "hb_code,quantity,batch_no,cost\nHB7001,3,CSV-001,25.5\n"
    response = client.post(
        "/api/v1/inventory/import",
        data={
            "merge_mode": "accumulate",
            "file": (BytesIO(csv_content.encode("utf-8")), "inventory.csv"),
        },
        headers=auth_headers,
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    preview_row = response.get_json()["data"]["imported_rows"][0]
    assert preview_row["expiry_date"] == "2099-12-31"

    with app.app_context():
        batch = Batch.query.filter_by(hb_code="HB7001").first()
        assert batch is not None
        assert batch.expiry_date.isoformat() == "2099-12-31"


def test_expiry_status_calculation(client, auth_headers):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    client.post(
        "/api/v1/products",
        json={
            "hb_code": "HB8001",
            "barcode": "6900000000007",
            "name": "维稳乳霜",
            "spec": "50g",
            "unit": "瓶",
            "base_unit": "瓶",
            "purchase_unit": "盒",
            "conversion_rate": 1,
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/inventory/inbound",
        json={
            "hb_code": "HB8001",
            "batch_no": "EXP-001",
            "expiry_date": tomorrow,
            "quantity": 4,
            "cost": 88.0,
            "unit_type": "base",
        },
        headers=auth_headers,
    )

    stats_response = client.get("/api/v1/dashboard/stats", headers=auth_headers)
    report_response = client.get("/api/v1/inventory/expiry-report?status=warning", headers=auth_headers)

    assert stats_response.status_code == 200
    assert stats_response.get_json()["data"]["warning_count"] >= 1
    assert report_response.status_code == 200
    warning_rows = report_response.get_json()["data"]["items"]
    assert any(row["hb_code"] == "HB8001" and row["status"] == "warning" for row in warning_rows)


def test_import_conversion(client, auth_headers, app):
    client.post(
        "/api/v1/products",
        json={
            "hb_code": "HB9001",
            "barcode": "6900000000008",
            "name": "焕亮精华",
            "spec": "15ml*10",
            "unit": "支",
            "base_unit": "支",
            "purchase_unit": "盒",
            "conversion_rate": 10,
        },
        headers=auth_headers,
    )

    csv_content = "hb_code,quantity,expiry_date,batch_no,unit_type,cost\nHB9001,2,2027-12-31,CSV-BOX,purchase,12\n"
    response = client.post(
        "/api/v1/inventory/import",
        data={
            "merge_mode": "accumulate",
            "file": (BytesIO(csv_content.encode("utf-8")), "import_conversion.csv"),
        },
        headers=auth_headers,
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    imported_row = response.get_json()["data"]["imported_rows"][0]
    assert imported_row["normalized_quantity"] == 20

    with app.app_context():
        batch = Batch.query.filter_by(hb_code="HB9001").first()
        assert batch is not None
        assert batch.current_quantity == 20


def test_external_order_sync(client, auth_headers, app):
    client.post(
        "/api/v1/products",
        json={
            "hb_code": "HB10001",
            "barcode": "6900000000010",
            "name": "修护精华",
            "spec": "30ml",
            "unit": "支",
            "base_unit": "支",
            "purchase_unit": "盒",
            "conversion_rate": 1,
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/channel-mappings",
        json={
            "channel_name": "抖音",
            "external_sku_id": "DY-SKU-10001",
            "hb_code": "HB10001",
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/inventory/inbound",
        json={
            "hb_code": "HB10001",
            "batch_no": "EARLY-LOT",
            "expiry_date": "2027-01-01",
            "quantity": 3,
            "cost": 50,
            "unit_type": "base",
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/inventory/inbound",
        json={
            "hb_code": "HB10001",
            "batch_no": "LATE-LOT",
            "expiry_date": "2027-06-01",
            "quantity": 5,
            "cost": 50,
            "unit_type": "base",
        },
        headers=auth_headers,
    )

    response = client.post(
        "/api/v1/orders/sync",
        json={"channel_name": "抖音", "external_sku_id": "DY-SKU-10001", "quantity": 2},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["order"]["hb_code"] == "HB10001"
    assert payload["order"]["status"] == "reserved"
    assert payload["allocations"][0]["batch_no"] == "EARLY-LOT"

    with app.app_context():
        early_batch = Batch.query.filter_by(batch_no="EARLY-LOT").first()
        late_batch = Batch.query.filter_by(batch_no="LATE-LOT").first()
        order = SalesOrder.query.first()
        allocation = OrderAllocation.query.first()

        assert order is not None
        assert allocation is not None
        assert early_batch.reserved_quantity == 2
        assert late_batch.reserved_quantity == 0


def test_role_restriction(client, staff_auth_headers):
    response = client.get("/api/v1/reports/export?format=csv", headers=staff_auth_headers)

    assert response.status_code == 403
    assert response.get_json()["msg"] == "admin role required"


def test_fulfill_logic(client, auth_headers, app):
    client.post(
        "/api/v1/products",
        json={
            "hb_code": "HB11001",
            "barcode": "6900000000011",
            "name": "舒敏喷雾",
            "spec": "80ml",
            "unit": "瓶",
            "base_unit": "瓶",
            "purchase_unit": "盒",
            "conversion_rate": 1,
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/channel-mappings",
        json={
            "channel_name": "抖音",
            "external_sku_id": "DY-SKU-11001",
            "hb_code": "HB11001",
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/inventory/inbound",
        json={
            "hb_code": "HB11001",
            "batch_no": "FULFILL-LOT",
            "expiry_date": "2027-03-01",
            "quantity": 6,
            "cost": 40,
            "unit_type": "base",
        },
        headers=auth_headers,
    )

    sync_response = client.post(
        "/api/v1/orders/sync",
        json={"channel_name": "抖音", "external_sku_id": "DY-SKU-11001", "quantity": 3},
        headers=auth_headers,
    )
    order_id = sync_response.get_json()["data"]["order"]["id"]

    fulfill_response = client.post(
        "/api/v1/orders/fulfill",
        json={"order_id": order_id},
        headers=auth_headers,
    )

    assert fulfill_response.status_code == 200
    assert fulfill_response.get_json()["data"]["order"]["status"] == "fulfilled"

    with app.app_context():
        batch = Batch.query.filter_by(batch_no="FULFILL-LOT").first()
        order = db.session.get(SalesOrder, order_id)
        transactions = InventoryTransaction.query.filter_by(order_id=order_id, transaction_type="OUT").all()

        assert batch.current_quantity == 3
        assert batch.reserved_quantity == 0
        assert order.status == "fulfilled"
        assert len(transactions) == 1
        assert transactions[0].quantity == 3


def test_inbound_creates_receipt_line_and_in_transaction(client, auth_headers, app):
    client.post(
        "/api/v1/products",
        json={
            "hb_code": "HB12001",
            "barcode": "6900000000012",
            "name": "入库台账测试品",
            "spec": "10ml",
            "unit": "支",
            "base_unit": "支",
            "purchase_unit": "盒",
            "conversion_rate": 10,
        },
        headers=auth_headers,
    )

    response = client.post(
        "/api/v1/inventory/inbound",
        json={
            "hb_code": "HB12001",
            "batch_no": "IN-LOT-001",
            "expiry_date": "2027-01-01",
            "quantity": 1,
            "cost": 9.9,
            "unit_type": "purchase",
            "supplier_name": "测试供应商",
            "remark": "首次入库",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["receipt"]["receipt_no"].startswith("IN-")
    assert payload["normalized_quantity"] == 10

    with app.app_context():
        receipt = InboundReceipt.query.filter_by(receipt_no=payload["receipt"]["receipt_no"]).first()
        assert receipt is not None
        assert receipt.supplier_name == "测试供应商"

        line = InboundLine.query.filter_by(receipt_id=receipt.id).first()
        assert line is not None
        assert line.hb_code == "HB12001"
        assert line.normalized_quantity == 10
        assert line.unit_cost == 9.9

        tx = InventoryTransaction.query.filter_by(transaction_type="IN", batch_id=line.batch_id).first()
        assert tx is not None
        assert tx.quantity == 10
        assert tx.get_extra_data()["doc_no"] == receipt.receipt_no


def test_ledger_export_running_balance_product_scope(client, auth_headers, app):
    client.post(
        "/api/v1/products",
        json={
            "hb_code": "HB13001",
            "barcode": "6900000000013",
            "name": "台账结存测试品",
            "spec": "80ml",
            "unit": "瓶",
            "base_unit": "瓶",
            "purchase_unit": "盒",
            "conversion_rate": 1,
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/channel-mappings",
        json={
            "channel_name": "抖音",
            "external_sku_id": "DY-SKU-13001",
            "hb_code": "HB13001",
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/inventory/inbound",
        json={
            "hb_code": "HB13001",
            "batch_no": "LEDGER-LOT",
            "expiry_date": "2027-03-01",
            "quantity": 10,
            "cost": 5.0,
            "unit_type": "base",
        },
        headers=auth_headers,
    )

    sync_response = client.post(
        "/api/v1/orders/sync",
        json={"channel_name": "抖音", "external_sku_id": "DY-SKU-13001", "quantity": 3},
        headers=auth_headers,
    )
    order_id = sync_response.get_json()["data"]["order"]["id"]
    client.post(
        "/api/v1/orders/fulfill",
        json={"order_id": order_id},
        headers=auth_headers,
    )

    export_response = client.get(
        "/api/v1/reports/ledger-export?format=csv&balance_scope=product&include_batch=1",
        headers=auth_headers,
    )
    assert export_response.status_code == 200

    reader = csv.DictReader(StringIO(export_response.get_data(as_text=True)))
    rows = list(reader)
    rows = [row for row in rows if row["商品编码"] == "HB13001"]
    assert len(rows) == 2

    # IN then OUT => 10 then 7
    assert int(float(rows[0]["结存数量"])) == 10
    assert int(float(rows[1]["结存数量"])) == 7


def test_ledger_export_running_balance_batch_scope(client, auth_headers, app):
    client.post(
        "/api/v1/products",
        json={
            "hb_code": "HB14001",
            "barcode": "6900000000014",
            "name": "批次结存测试品",
            "spec": "30ml",
            "unit": "支",
            "base_unit": "支",
            "purchase_unit": "盒",
            "conversion_rate": 1,
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/channel-mappings",
        json={
            "channel_name": "抖音",
            "external_sku_id": "DY-SKU-14001",
            "hb_code": "HB14001",
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/inventory/inbound",
        json={
            "hb_code": "HB14001",
            "batch_no": "BATCH-A",
            "expiry_date": "2027-01-01",
            "quantity": 5,
            "cost": 10.0,
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/inventory/inbound",
        json={
            "hb_code": "HB14001",
            "batch_no": "BATCH-B",
            "expiry_date": "2027-06-01",
            "quantity": 6,
            "cost": 10.0,
        },
        headers=auth_headers,
    )

    sync_response = client.post(
        "/api/v1/orders/sync",
        json={"channel_name": "抖音", "external_sku_id": "DY-SKU-14001", "quantity": 3},
        headers=auth_headers,
    )
    order_id = sync_response.get_json()["data"]["order"]["id"]
    client.post(
        "/api/v1/orders/fulfill",
        json={"order_id": order_id},
        headers=auth_headers,
    )

    export_response = client.get(
        "/api/v1/reports/ledger-export?format=csv&balance_scope=batch&include_batch=1",
        headers=auth_headers,
    )
    assert export_response.status_code == 200

    reader = csv.DictReader(StringIO(export_response.get_data(as_text=True)))
    rows = [row for row in reader if row["商品编码"] == "HB14001"]
    assert len(rows) == 3

    by_batch = {}
    for row in rows:
        batch_no = row.get("批次号") or ""
        if not batch_no:
            continue
        by_batch.setdefault(batch_no, []).append(int(float(row["结存数量"])))

    assert by_batch["BATCH-A"][0] == 5
    assert by_batch["BATCH-A"][-1] == 2
    assert by_batch["BATCH-B"][0] == 6
