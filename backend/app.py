from datetime import date, datetime, timedelta
from functools import wraps
from io import BytesIO
import os
from pathlib import Path
import secrets
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from flask import Flask, Response, jsonify, request, send_file, send_from_directory
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy import or_

from backend.extensions import db, jwt
from backend.models import (
    Batch,
    ChannelMapping,
    ExternalOrderRef,
    InboundLine,
    InboundReceipt,
    InventoryTransaction,
    OrderAllocation,
    Product,
    SalesOrder,
    User,
)
from backend.services.import_service import classify_expiry_status, import_from_csv
from backend.services.inbound_import_service import build_inbound_rows_from_file
from backend.services.order_import_service import build_order_rows_from_file
from backend.services.product_import_service import import_products_from_file

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"


def api_response(code=200, data=None, msg="success"):
    return jsonify({"code": code, "data": data or {}, "msg": msg}), code


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return api_response(code=403, msg="admin role required")
        return fn(*args, **kwargs)

    return wrapper


def parse_date(value, field_name, required=False):
    if value in {None, ""}:
        if required:
            return None, f"{field_name} is required"
        return None, None

    try:
        return date.fromisoformat(value), None
    except ValueError:
        return None, f"{field_name} must be in YYYY-MM-DD format"


def parse_positive_int(value, field_name, allow_zero=False):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, f"{field_name} must be an integer"

    if allow_zero:
        if parsed < 0:
            return None, f"{field_name} must be greater than or equal to 0"
    elif parsed <= 0:
        return None, f"{field_name} must be greater than 0"

    return parsed, None


def parse_non_negative_float(value, field_name):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None, f"{field_name} must be a number"

    if parsed < 0:
        return None, f"{field_name} must be greater than or equal to 0"

    return parsed, None


def find_product(payload):
    hb_code = (payload.get("hb_code") or "").strip()
    barcode = (payload.get("barcode") or "").strip()

    if hb_code:
        product = Product.query.filter_by(hb_code=hb_code).first()
        if product:
            return product, None, None

    if barcode:
        matches = Product.query.filter_by(barcode=barcode).order_by(Product.hb_code.asc()).all()
        if len(matches) == 1:
            return matches[0], None, None
        if len(matches) > 1:
            return None, "barcode is not unique; please use hb_code", 409

    return None, None, None


def normalize_inbound_quantity(product, quantity, unit_type):
    if unit_type == "purchase":
        return quantity * product.conversion_rate
    return quantity


def merge_batch_extra_data(existing_batch, incoming_extra_data, incoming_batch_no):
    merged = existing_batch.get_extra_data()

    if incoming_extra_data:
        merged.update(incoming_extra_data)

    if incoming_batch_no and incoming_batch_no != existing_batch.batch_no:
        merged_batch_nos = merged.get("merged_batch_nos", [])
        if existing_batch.batch_no not in merged_batch_nos:
            merged_batch_nos.append(existing_batch.batch_no)
        if incoming_batch_no not in merged_batch_nos:
            merged_batch_nos.append(incoming_batch_no)
        merged["merged_batch_nos"] = merged_batch_nos

    existing_batch.set_extra_data(merged)


def reserve_product_inventory(product, quantity):
    if product.sellable_stock < quantity:
        return None, "insufficient sellable stock"

    allocations = []
    remaining = quantity
    batches = (
        Batch.query.filter_by(hb_code=product.hb_code)
        .order_by(Batch.expiry_date.asc(), Batch.id.asc())
        .all()
    )

    for batch in batches:
        available = batch.available_quantity
        if available <= 0:
            continue

        reserved = min(available, remaining)
        batch.reserved_quantity += reserved
        allocations.append(
            {
                "batch": batch,
                "batch_id": batch.id,
                "batch_no": batch.batch_no,
                "reserved_quantity": reserved,
                "expiry_date": batch.expiry_date.isoformat(),
            }
        )
        remaining -= reserved

        if remaining == 0:
            break

    return allocations, None


def serialize_batch_for_report(batch, today=None):
    today = today or date.today()
    status = classify_expiry_status(batch.expiry_date, today=today)

    return {
        "id": batch.id,
        "hb_code": batch.hb_code,
        "product_name": batch.product.name if batch.product else None,
        "batch_no": batch.batch_no,
        "expiry_date": batch.expiry_date.isoformat(),
        "production_date": batch.production_date.isoformat() if batch.production_date else None,
        "cost": batch.cost,
        "current_quantity": batch.current_quantity,
        "reserved_quantity": batch.reserved_quantity,
        "available_quantity": batch.available_quantity,
        "status": status,
    }


def serialize_order(order):
    return order.to_dict(include_allocations=True)


def create_sales_order(
    channel_name,
    external_sku_id,
    quantity,
    *,
    extra_data=None,
    external_order_no=None,
    commit=True,
):
    if not external_order_no and isinstance(extra_data, dict):
        external_order_no = (extra_data.get("external_order_no") or "").strip() or None

    # Idempotency: if an external order number is provided, do not reserve again.
    if external_order_no:
        ref = ExternalOrderRef.query.filter_by(
            channel_name=channel_name,
            external_order_no=external_order_no,
        ).first()
        if ref and ref.order:
            existing = ref.order
            if existing.external_sku_id != external_sku_id or existing.quantity != quantity:
                return None, None, "external_order_no already exists with different payload", True

            # Return existing allocations; no stock changes.
            return existing, list(existing.allocations), None, True

    mapping = ChannelMapping.query.filter_by(
        channel_name=channel_name,
        external_sku_id=external_sku_id,
    ).first()
    if not mapping:
        return None, None, "channel mapping not found", False

    product = Product.query.filter_by(hb_code=mapping.hb_code).first()
    if not product:
        return None, None, "product not found", False

    allocations, reserve_error = reserve_product_inventory(product, quantity)
    if reserve_error:
        return None, None, reserve_error, False

    order = SalesOrder(
        channel_name=channel_name,
        external_sku_id=external_sku_id,
        hb_code=product.hb_code,
        quantity=quantity,
        status="reserved",
    )
    merged_extra = {"source": "external_sync"}
    if isinstance(extra_data, dict) and extra_data:
        merged_extra.update(extra_data)
    if external_order_no:
        merged_extra.setdefault("external_order_no", external_order_no)
    order.set_extra_data(merged_extra)
    db.session.add(order)
    db.session.flush()

    if external_order_no:
        ref = ExternalOrderRef(
            channel_name=channel_name,
            external_order_no=external_order_no,
            external_sku_id=external_sku_id,
            order_id=order.id,
        )
        ref.set_extra_data({"source": "idempotency"})
        db.session.add(ref)

    persisted_allocations = []
    for allocation in allocations:
        order_allocation = OrderAllocation(
            order_id=order.id,
            batch_id=allocation["batch_id"],
            quantity=allocation["reserved_quantity"],
        )
        order_allocation.set_extra_data({"expiry_date": allocation["expiry_date"]})
        db.session.add(order_allocation)
        persisted_allocations.append(order_allocation)

    if commit:
        db.session.commit()
        db.session.refresh(order)

    return order, persisted_allocations, None, False


def apply_inbound_payload(payload, *, receipt=None):
    """
    Apply a single inbound payload into the current SQLAlchemy session.
    Does not commit. Returns (result, error_message, http_code).
    """

    product, product_error, product_http = find_product(payload)
    if product_error:
        return None, product_error, product_http or 400
    if not product:
        return None, "product not found", 404

    batch_no = (payload.get("batch_no") or "").strip()
    if not batch_no:
        return None, "batch_no is required", 400

    expiry_date, expiry_error = parse_date(
        payload.get("expiry_date"),
        "expiry_date",
        required=True,
    )
    if expiry_error:
        return None, expiry_error, 400

    production_date, production_error = parse_date(
        payload.get("production_date"),
        "production_date",
    )
    if production_error:
        return None, production_error, 400

    quantity, quantity_error = parse_positive_int(payload.get("quantity"), "quantity")
    if quantity_error:
        return None, quantity_error, 400

    cost, cost_error = parse_non_negative_float(payload.get("cost", 0), "cost")
    if cost_error:
        return None, cost_error, 400

    unit_type = (payload.get("unit_type") or "base").strip().lower()
    if unit_type not in {"base", "purchase"}:
        return None, "unit_type must be one of: base, purchase", 400

    normalized_quantity = normalize_inbound_quantity(product, quantity, unit_type)

    batch_extra_data = payload.get("extra_data") or {}
    line_extra_data = payload.get("line_extra_data") or {}
    tx_extra_data = payload.get("tx_extra_data") or {}

    batch = Batch.query.filter_by(hb_code=product.hb_code, expiry_date=expiry_date).first()
    action = "created"

    if batch:
        old_qty = batch.current_quantity
        total_qty = old_qty + normalized_quantity
        # Weighted average cost to avoid overwriting historical cost during merges.
        if total_qty > 0:
            batch.cost = round((old_qty * batch.cost + normalized_quantity * cost) / total_qty, 6)
        else:
            batch.cost = cost

        batch.current_quantity += normalized_quantity
        batch.initial_quantity += normalized_quantity
        if not batch.production_date and production_date:
            batch.production_date = production_date
        merge_batch_extra_data(batch, batch_extra_data, batch_no)
        action = "merged"
    else:
        batch = Batch(
            hb_code=product.hb_code,
            batch_no=batch_no,
            production_date=production_date,
            expiry_date=expiry_date,
            cost=cost,
            initial_quantity=normalized_quantity,
            current_quantity=normalized_quantity,
            reserved_quantity=0,
        )
        batch.set_extra_data(batch_extra_data)
        db.session.add(batch)

    db.session.flush()

    receipt = receipt or get_or_create_inbound_receipt(payload)

    line = InboundLine(
        receipt_id=receipt.id,
        hb_code=product.hb_code,
        batch_id=batch.id,
        batch_no=batch_no,
        production_date=production_date,
        expiry_date=expiry_date,
        unit_type=unit_type,
        quantity_input=quantity,
        normalized_quantity=normalized_quantity,
        unit_cost=cost,
    )
    barcode_value = (payload.get("barcode") or "").strip() or None
    line_payload = {
        "action": action,
        "barcode": barcode_value,
    }
    if isinstance(line_extra_data, dict) and line_extra_data:
        line_payload.update(line_extra_data)
    line.set_extra_data(line_payload)
    db.session.add(line)

    inbound_tx = InventoryTransaction(
        hb_code=product.hb_code,
        batch_id=batch.id,
        order_id=None,
        transaction_type="IN",
        quantity=normalized_quantity,
    )
    tx_payload = {
        "doc_type": "inbound_receipt",
        "doc_no": receipt.receipt_no,
        "supplier_name": receipt.supplier_name,
        "unit_type": unit_type,
        "quantity_input": quantity,
        "unit_cost": cost,
    }
    if isinstance(tx_extra_data, dict) and tx_extra_data:
        tx_payload.update(tx_extra_data)
    inbound_tx.set_extra_data(tx_payload)
    db.session.add(inbound_tx)

    # Ensure stock aggregation reflects the in-session batch changes.
    db.session.flush()
    db.session.expire(product, ["batches"])

    return (
        {
            "action": action,
            "product": product.to_dict(include_stock=True),
            "batch": batch.to_dict(),
            "receipt": receipt.to_dict(),
            "normalized_quantity": normalized_quantity,
            "unit_type": unit_type,
        },
        None,
        None,
    )


def fulfill_sales_order(order):
    if order.status != "reserved":
        return None, "order is not in reserved status"

    transactions = []
    for allocation in order.allocations:
        batch = allocation.batch
        if not batch:
            return None, "allocated batch not found"
        if batch.reserved_quantity < allocation.quantity or batch.current_quantity < allocation.quantity:
            return None, "allocated batch stock is inconsistent"

        batch.reserved_quantity -= allocation.quantity
        batch.current_quantity -= allocation.quantity

        doc_no = f"SO-{order.id}"
        transaction = InventoryTransaction(
            hb_code=order.hb_code,
            batch_id=batch.id,
            order_id=order.id,
            transaction_type="OUT",
            quantity=allocation.quantity,
        )
        transaction.set_extra_data(
            {
                "doc_type": "sales_order",
                "doc_no": doc_no,
                "channel_name": order.channel_name,
                "external_sku_id": order.external_sku_id,
            }
        )
        db.session.add(transaction)
        transactions.append(transaction)

    order.status = "fulfilled"
    order.fulfilled_at = datetime.utcnow()
    db.session.commit()

    return transactions, None


def build_export_rows():
    rows = []
    products = Product.query.order_by(Product.hb_code.asc()).all()
    for product in products:
        if product.batches:
            for batch in product.batches:
                rows.append(
                    {
                        "hb_code": product.hb_code,
                        "barcode": product.barcode,
                        "name": product.name,
                        "spec": product.spec,
                        "base_unit": product.base_unit,
                        "purchase_unit": product.purchase_unit,
                        "conversion_rate": product.conversion_rate,
                        "total_stock": product.total_stock,
                        "reserved_stock": product.reserved_stock,
                        "sellable_stock": product.sellable_stock,
                        "batch_no": batch.batch_no,
                        "production_date": batch.production_date.isoformat() if batch.production_date else None,
                        "expiry_date": batch.expiry_date.isoformat(),
                        "cost": batch.cost,
                        "initial_quantity": batch.initial_quantity,
                        "current_quantity": batch.current_quantity,
                        "reserved_quantity": batch.reserved_quantity,
                        "available_quantity": batch.available_quantity,
                    }
                )
        else:
            rows.append(
                {
                    "hb_code": product.hb_code,
                    "barcode": product.barcode,
                    "name": product.name,
                    "spec": product.spec,
                    "base_unit": product.base_unit,
                    "purchase_unit": product.purchase_unit,
                    "conversion_rate": product.conversion_rate,
                    "total_stock": product.total_stock,
                    "reserved_stock": product.reserved_stock,
                    "sellable_stock": product.sellable_stock,
                    "batch_no": None,
                    "production_date": None,
                    "expiry_date": None,
                    "cost": None,
                    "initial_quantity": None,
                    "current_quantity": None,
                    "reserved_quantity": None,
                    "available_quantity": None,
                }
            )
    return rows


LEDGER_BASE_COLUMNS = [
    "操作日期",
    "单据编号",
    "商品编码",
    "商品名称",
    "规格型号",
    "单位",
    "入库数量",
    "出库数量",
    "结存数量",
    "入库单价",
    "出库单价",
    "操作类型",
    "来源",
    "去向",
    "供应商",
    "客户",
    "备注",
    "其他说明",
    "进货金额汇总",
    "向供应商付款记录",
]


def transaction_delta(transaction_type: str, quantity: int) -> int:
    if transaction_type in {"IN", "ADJUST_IN"}:
        return quantity
    if transaction_type in {"OUT", "ADJUST_OUT"}:
        return -quantity
    return 0


def transaction_operation_label(transaction_type: str) -> str:
    mapping = {
        "IN": "入库",
        "OUT": "出库",
        "ADJUST_IN": "盘盈",
        "ADJUST_OUT": "盘亏",
        "COUNT": "盘点",
    }
    return mapping.get(transaction_type, transaction_type)


def build_ledger_rows(balance_scope="product", include_batch=False):
    include_batch = bool(include_batch)
    columns = list(LEDGER_BASE_COLUMNS)
    if include_batch:
        columns.extend(["批次号", "到期日"])

    balances = {}
    transactions = (
        InventoryTransaction.query.order_by(
            InventoryTransaction.created_at.asc(),
            InventoryTransaction.id.asc(),
        )
        .all()
    )

    rows = []
    for tx in transactions:
        extra = tx.get_extra_data()
        product = tx.product
        batch = tx.batch

        doc_no = extra.get("doc_no")
        if not doc_no and tx.order_id:
            doc_no = f"SO-{tx.order_id}"
        if not doc_no:
            doc_no = f"TX-{tx.id}"

        in_qty = tx.quantity if tx.transaction_type in {"IN", "ADJUST_IN"} else 0
        out_qty = tx.quantity if tx.transaction_type in {"OUT", "ADJUST_OUT"} else 0

        key = tx.hb_code
        if balance_scope == "batch":
            key = tx.batch_id or tx.hb_code

        balances[key] = balances.get(key, 0) + transaction_delta(tx.transaction_type, tx.quantity)

        unit_cost_in = extra.get("unit_cost")
        if unit_cost_in is None and tx.transaction_type == "IN" and batch:
            unit_cost_in = batch.cost

        unit_price_out = extra.get("unit_price_out") or extra.get("unit_price")

        supplier_name = extra.get("supplier_name") or extra.get("supplier")
        customer_name = extra.get("customer_name") or extra.get("customer")

        source = extra.get("source") or (extra.get("channel_name") if tx.transaction_type == "OUT" else "采购入库")
        destination = extra.get("destination") or ""

        remark = extra.get("remark") or ""
        other_note = extra.get("other_note") or ""

        inbound_amount = ""
        if tx.transaction_type == "IN" and unit_cost_in is not None:
            try:
                inbound_amount = round(float(unit_cost_in) * int(tx.quantity), 2)
            except (TypeError, ValueError):
                inbound_amount = ""

        row = {
            "操作日期": tx.created_at.date().isoformat() if tx.created_at else None,
            "单据编号": doc_no,
            "商品编码": tx.hb_code,
            "商品名称": product.name if product else None,
            "规格型号": product.spec if product else None,
            "单位": product.base_unit if product else None,
            "入库数量": in_qty,
            "出库数量": out_qty,
            "结存数量": balances[key],
            "入库单价": unit_cost_in if unit_cost_in is not None else "",
            "出库单价": unit_price_out if unit_price_out is not None else "",
            "操作类型": transaction_operation_label(tx.transaction_type),
            "来源": source,
            "去向": destination,
            "供应商": supplier_name or "",
            "客户": customer_name or "",
            "备注": remark,
            "其他说明": other_note,
            "进货金额汇总": inbound_amount,
            "向供应商付款记录": "",
        }

        if include_batch:
            row["批次号"] = batch.batch_no if batch else ""
            row["到期日"] = batch.expiry_date.isoformat() if batch and batch.expiry_date else ""

        rows.append(row)

    return columns, rows


def generate_inbound_receipt_no(now=None):
    now = now or datetime.utcnow()
    return f"IN-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}-{secrets.token_hex(3)}"


def get_or_create_inbound_receipt(payload):
    receipt_no = (payload.get("receipt_no") or "").strip()
    supplier_name = (payload.get("supplier_name") or "").strip() or None
    remark = (payload.get("remark") or "").strip() or None
    extra_data = payload.get("receipt_extra_data") or {}

    if receipt_no:
        receipt = InboundReceipt.query.filter_by(receipt_no=receipt_no).first()
        if receipt:
            return receipt

        receipt = InboundReceipt(
            receipt_no=receipt_no,
            supplier_name=supplier_name,
            remark=remark,
        )
        receipt.set_extra_data(extra_data)
        db.session.add(receipt)
        db.session.flush()
        return receipt

    receipt = InboundReceipt(
        receipt_no=generate_inbound_receipt_no(),
        supplier_name=supplier_name,
        remark=remark,
    )
    receipt.set_extra_data(extra_data)
    db.session.add(receipt)
    db.session.flush()
    return receipt


def resolve_frontend_dist_dir(config=None):
    configured_path = None
    if config:
        configured_path = config.get("FRONTEND_DIST_DIR")

    configured_path = configured_path or os.getenv("FRONTEND_DIST_DIR")
    return str(Path(configured_path or DEFAULT_FRONTEND_DIST_DIR).resolve())


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", "roseate-wms-dev-secret"),
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=8),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///roseate_wms.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        DEFAULT_ADMIN_USERNAME=os.getenv("DEFAULT_ADMIN_USERNAME", "admin"),
        DEFAULT_ADMIN_PASSWORD=os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@123456"),
        DEFAULT_ADMIN_ROLE=os.getenv("DEFAULT_ADMIN_ROLE", "admin"),
        FRONTEND_DIST_DIR=resolve_frontend_dist_dir(config),
    )

    if config:
        app.config.update(config)

    db.init_app(app)
    jwt.init_app(app)

    register_error_handlers()
    register_routes(app)

    with app.app_context():
        db.create_all()
        ensure_default_admin(app)

    return app


def ensure_default_admin(app):
    username = app.config.get("DEFAULT_ADMIN_USERNAME")
    password = app.config.get("DEFAULT_ADMIN_PASSWORD")
    role = app.config.get("DEFAULT_ADMIN_ROLE", "admin")

    if not username or not password:
        return

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return

    user = User(username=username, role=role)
    user.set_password(password)
    user.set_extra_data({"seeded": True})
    db.session.add(user)
    db.session.commit()


def register_error_handlers():
    @jwt.unauthorized_loader
    def handle_missing_token(reason):
        return api_response(code=401, msg=reason)

    @jwt.invalid_token_loader
    def handle_invalid_token(reason):
        return api_response(code=401, msg=reason)

    @jwt.expired_token_loader
    def handle_expired_token(jwt_header, jwt_payload):
        return api_response(code=401, msg="token has expired")


def register_routes(app):
    @app.post("/api/v1/auth/login")
    def login():
        payload = request.get_json(silent=True) or {}
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""

        if not username or not password:
            return api_response(code=400, msg="username and password are required")

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return api_response(code=401, msg="invalid username or password")

        token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "username": user.username,
                "role": user.role,
            },
        )
        return api_response(
            data={
                "token": token,
                "user": user.to_dict(),
            }
        )

    if app.config.get("ENABLE_DEBUG_ENDPOINTS") or app.debug or app.testing:
        @app.get("/api/v1/inventory/test")
        @jwt_required()
        def inventory_test():
            # Debug-only endpoint: avoid leaking user identity details.
            return api_response(
                data={
                    "message": "inventory test endpoint is protected",
                    "user_id": get_jwt_identity(),
                }
            )

    @app.get("/api/v1/products")
    @jwt_required()
    def list_products():
        query_text = (request.args.get("q") or "").strip()
        query = Product.query

        if query_text:
            fuzzy_query = f"%{query_text}%"
            query = query.filter(
                or_(
                    Product.name.ilike(fuzzy_query),
                    Product.barcode.ilike(fuzzy_query),
                    Product.hb_code.ilike(fuzzy_query),
                )
            )

        products = query.order_by(Product.hb_code.asc()).all()
        return api_response(
            data={
                "items": [product.to_dict(include_stock=True) for product in products],
                "total": len(products),
                "query": query_text,
            }
        )

    @app.get("/api/v1/products/<string:hb_code>")
    @jwt_required()
    def get_product(hb_code):
        product = Product.query.filter_by(hb_code=hb_code).first()
        if not product:
            return api_response(code=404, msg="product not found")

        return api_response(
            data={
                "product": product.to_dict(
                    include_stock=True,
                    include_batches=True,
                    include_mappings=True,
                )
            }
        )

    @app.post("/api/v1/products")
    @admin_required
    def create_product():
        payload = request.get_json(silent=True) or {}

        hb_code = (payload.get("hb_code") or "").strip()
        name = (payload.get("name") or "").strip()
        spec = (payload.get("spec") or "").strip()
        unit = (payload.get("unit") or payload.get("base_unit") or "").strip()
        base_unit = (payload.get("base_unit") or unit or "").strip()
        purchase_unit = (payload.get("purchase_unit") or base_unit or "").strip()
        barcode = (payload.get("barcode") or "").strip() or None
        extra_data = payload.get("extra_data") or {}

        conversion_rate, conversion_error = parse_positive_int(
            payload.get("conversion_rate", 1),
            "conversion_rate",
        )
        if conversion_error:
            return api_response(code=400, msg=conversion_error)

        if not all([hb_code, name, spec, unit, base_unit, purchase_unit]):
            return api_response(
                code=400,
                msg="hb_code, name, spec, unit, base_unit and purchase_unit are required",
            )

        if Product.query.filter_by(hb_code=hb_code).first():
            return api_response(code=409, msg="product hb_code already exists")

        if barcode and Product.query.filter_by(barcode=barcode).first():
            return api_response(code=409, msg="barcode already exists")

        product = Product(
            hb_code=hb_code,
            barcode=barcode,
            name=name,
            spec=spec,
            unit=unit,
            base_unit=base_unit,
            purchase_unit=purchase_unit,
            conversion_rate=conversion_rate,
        )
        product.set_extra_data(extra_data)
        db.session.add(product)
        db.session.commit()

        return api_response(code=201, data={"product": product.to_dict(include_stock=True)})

    @app.post("/api/v1/products/import/preview")
    @admin_required
    def products_import_preview():
        upload = request.files.get("file")
        mode = (request.form.get("mode") or "skip").strip().lower()

        if not upload:
            return api_response(code=400, msg="file is required")

        try:
            result = import_products_from_file(
                file_stream=upload.stream,
                filename=upload.filename or "products.csv",
                mode=mode,
                commit=False,
                product_model=Product,
                db=db,
            )
        except ValueError as exc:
            return api_response(code=400, msg=str(exc))

        return api_response(
            data={
                "mode": mode,
                "columns": result["columns"],
                "preview_rows": result["preview_rows"],
                "total_rows": result["total_rows"],
                "valid_rows": result["valid_rows"],
                "error_rows": result["error_rows"],
                "errors": result["errors"],
            }
        )

    @app.post("/api/v1/products/import")
    @admin_required
    def products_import_commit():
        upload = request.files.get("file")
        mode = (request.form.get("mode") or "skip").strip().lower()

        if not upload:
            return api_response(code=400, msg="file is required")

        try:
            result = import_products_from_file(
                file_stream=upload.stream,
                filename=upload.filename or "products.csv",
                mode=mode,
                commit=True,
                product_model=Product,
                db=db,
            )
        except ValueError as exc:
            return api_response(code=400, msg=str(exc))

        return api_response(
            data={
                "mode": mode,
                "total_rows": result["total_rows"],
                "valid_rows": result["valid_rows"],
                "error_rows": result["error_rows"],
                "created": result.get("created", 0),
                "updated": result.get("updated", 0),
                "skipped": result.get("skipped", 0),
                "imported_rows": result.get("imported_rows", []),
                "errors": result["errors"],
            }
        )

    @app.post("/api/v1/inventory/inbound")
    @jwt_required()
    def inventory_inbound():
        payload = request.get_json(silent=True) or {}
        result, error_message, http_code = apply_inbound_payload(payload)
        if error_message:
            return api_response(code=http_code or 400, msg=error_message)

        db.session.commit()
        return api_response(data=result)

    @app.post("/api/v1/inventory/inbound-import/preview")
    @jwt_required()
    def inbound_import_preview():
        upload = request.files.get("file")
        mapping_raw = request.form.get("mapping") or ""
        default_receipt_no = (request.form.get("receipt_no") or "").strip() or None
        default_supplier_name = (request.form.get("supplier_name") or "").strip() or None
        default_remark = (request.form.get("remark") or "").strip() or None

        if not upload:
            return api_response(code=400, msg="file is required")

        mapping = {}
        if mapping_raw:
            try:
                import json

                mapping = json.loads(mapping_raw) or {}
            except Exception:
                return api_response(code=400, msg="mapping must be valid JSON")

        try:
            result = build_inbound_rows_from_file(
                file_stream=upload.stream,
                filename=upload.filename or "inbound.csv",
                mapping=mapping,
                default_receipt_no=default_receipt_no,
                default_supplier_name=default_supplier_name,
                default_remark=default_remark,
            )
        except ValueError as exc:
            return api_response(code=400, msg=str(exc))

        return api_response(
            data={
                "columns": result["columns"],
                "mapping_guess": result["mapping_guess"],
                "mapping_effective": result["mapping_effective"],
                "preview_rows": result["preview_rows"],
                "total_rows": result["total_rows"],
                "valid_rows": result["valid_rows"],
                "error_rows": result["error_rows"],
                "errors": result["errors"],
            }
        )

    @app.post("/api/v1/inventory/inbound-import")
    @jwt_required()
    def inbound_import_commit():
        upload = request.files.get("file")
        mapping_raw = request.form.get("mapping") or ""
        default_receipt_no = (request.form.get("receipt_no") or "").strip() or None
        default_supplier_name = (request.form.get("supplier_name") or "").strip() or None
        default_remark = (request.form.get("remark") or "").strip() or None

        if not upload:
            return api_response(code=400, msg="file is required")

        mapping = {}
        if mapping_raw:
            try:
                import json

                mapping = json.loads(mapping_raw) or {}
            except Exception:
                return api_response(code=400, msg="mapping must be valid JSON")

        try:
            parsed = build_inbound_rows_from_file(
                file_stream=upload.stream,
                filename=upload.filename or "inbound.csv",
                mapping=mapping,
                default_receipt_no=default_receipt_no,
                default_supplier_name=default_supplier_name,
                default_remark=default_remark,
            )
        except ValueError as exc:
            return api_response(code=400, msg=str(exc))

        # If user mapped a receipt_no column, respect per-row receipts.
        receipt_col = (parsed.get("mapping_effective") or {}).get("receipt_no") or ""
        use_row_receipt = bool(receipt_col)

        shared_receipt = None
        if not use_row_receipt:
            receipt_payload = {
                "receipt_no": default_receipt_no or "",
                "supplier_name": default_supplier_name or "",
                "remark": default_remark or "",
                "receipt_extra_data": {
                    "source": "inbound_import",
                    "filename": upload.filename,
                },
            }
            shared_receipt = get_or_create_inbound_receipt(receipt_payload)

        created = 0
        merged = 0
        imported_rows = []
        errors = list(parsed.get("errors") or [])

        for row in parsed.get("rows") or []:
            row_number = row.get("row_number")
            payload = row.get("payload") or {}

            # Keep row-level extras out of batch extra_data.
            row_extra = (payload.get("extra_data") or {}) if isinstance(payload.get("extra_data"), dict) else {}
            payload["extra_data"] = {}
            payload["line_extra_data"] = row_extra
            payload["tx_extra_data"] = {"import_row": row_number}

            nested = db.session.begin_nested()
            try:
                result, error_message, http_code = apply_inbound_payload(payload, receipt=shared_receipt)
                if error_message:
                    nested.rollback()
                    errors.append({"row_number": row_number, "error": error_message})
                    continue

                nested.commit()
                imported_rows.append(result)
                if result.get("action") == "merged":
                    merged += 1
                else:
                    created += 1
            except Exception as exc:  # noqa: BLE001 - isolate per-row failures
                nested.rollback()
                errors.append({"row_number": row_number, "error": str(exc)})

        db.session.commit()

        return api_response(
            data={
                "total_rows": parsed["total_rows"],
                "valid_rows": parsed["valid_rows"],
                "error_rows": len(errors),
                "created": created,
                "merged": merged,
                "receipt": shared_receipt.to_dict() if shared_receipt else None,
                "preview_rows": parsed["preview_rows"],
                "imported_rows": imported_rows[:20],
                "errors": errors[:20],
            }
        )

    @app.post("/api/v1/inventory/import/preview")
    @admin_required
    def inventory_import_preview():
        upload = request.files.get("file")
        merge_mode = (request.form.get("merge_mode") or "accumulate").strip().lower()

        if not upload:
            return api_response(code=400, msg="file is required")

        try:
            result = import_from_csv(upload.stream, merge_mode=merge_mode, commit=False)
        except ValueError as exc:
            return api_response(code=400, msg=str(exc))

        return api_response(
            data={
                "merge_mode": merge_mode,
                "preview_rows": result["preview_rows"],
                "total_rows": result["total_rows"],
            }
        )

    @app.post("/api/v1/inventory/import")
    @admin_required
    def inventory_import():
        upload = request.files.get("file")
        merge_mode = (request.form.get("merge_mode") or "accumulate").strip().lower()

        if not upload:
            return api_response(code=400, msg="file is required")

        try:
            result = import_from_csv(upload.stream, merge_mode=merge_mode, commit=True)
        except ValueError as exc:
            return api_response(code=400, msg=str(exc))

        return api_response(
            data={
                "merge_mode": merge_mode,
                "preview_rows": result["preview_rows"],
                "imported_rows": result["imported_rows"],
                "total_rows": result["total_rows"],
            }
        )

    @app.post("/api/v1/inventory/reserve")
    @jwt_required()
    def inventory_reserve():
        payload = request.get_json(silent=True) or {}
        hb_code = (payload.get("hb_code") or "").strip()

        if not hb_code:
            return api_response(code=400, msg="hb_code is required")

        quantity, quantity_error = parse_positive_int(payload.get("quantity"), "quantity")
        if quantity_error:
            return api_response(code=400, msg=quantity_error)

        product = Product.query.filter_by(hb_code=hb_code).first()
        if not product:
            return api_response(code=404, msg="product not found")

        allocations, reserve_error = reserve_product_inventory(product, quantity)
        if reserve_error:
            return api_response(code=409, msg=reserve_error)

        db.session.commit()

        return api_response(
            data={
                "product": product.to_dict(include_stock=True),
                "reserved_quantity": quantity,
                "allocations": [
                    {k: v for k, v in allocation.items() if k != "batch"} for allocation in allocations
                ],
            }
        )

    @app.get("/api/v1/inventory/expiry-report")
    @jwt_required()
    def inventory_expiry_report():
        status_filter = (request.args.get("status") or "").strip().lower()
        if status_filter and status_filter not in {"expired", "warning", "healthy"}:
            return api_response(code=400, msg="status must be one of: expired, warning, healthy")

        today = date.today()
        batches = (
            Batch.query.filter(Batch.current_quantity > 0)
            .order_by(Batch.expiry_date.asc(), Batch.id.asc())
            .all()
        )
        items = [serialize_batch_for_report(batch, today=today) for batch in batches]

        if status_filter:
            items = [item for item in items if item["status"] == status_filter]

        return api_response(
            data={
                "items": items,
                "total": len(items),
                "status": status_filter or "all",
            }
        )

    @app.get("/api/v1/dashboard/stats")
    @jwt_required()
    def dashboard_stats():
        today = date.today()
        batches = Batch.query.filter(Batch.current_quantity > 0).all()
        total_value = round(sum(batch.current_quantity * batch.cost for batch in batches), 2)

        expired_count = 0
        warning_count = 0
        healthy_count = 0

        for batch in batches:
            status = classify_expiry_status(batch.expiry_date, today=today)
            if status == "expired":
                expired_count += 1
            elif status == "warning":
                warning_count += 1
            else:
                healthy_count += 1

        return api_response(
            data={
                "total_value": total_value,
                "expired_count": expired_count,
                "warning_count": warning_count,
                "healthy_count": healthy_count,
            }
        )

    @app.get("/api/v1/orders")
    @jwt_required()
    def list_orders():
        status = (request.args.get("status") or "").strip().lower()
        query = SalesOrder.query
        if status:
            query = query.filter_by(status=status)

        orders = query.order_by(SalesOrder.created_at.desc(), SalesOrder.id.desc()).all()
        return api_response(data={"items": [serialize_order(order) for order in orders], "total": len(orders)})

    @app.post("/api/v1/orders/sync")
    @jwt_required()
    def sync_order():
        payload = request.get_json(silent=True) or {}
        channel_name = (payload.get("channel_name") or "").strip()
        external_sku_id = (payload.get("external_sku_id") or "").strip()
        external_order_no = (payload.get("external_order_no") or "").strip() or None
        quantity, quantity_error = parse_positive_int(payload.get("quantity", 1), "quantity")

        if not channel_name or not external_sku_id:
            return api_response(code=400, msg="channel_name and external_sku_id are required")
        if quantity_error:
            return api_response(code=400, msg=quantity_error)

        extra_data = payload.get("extra_data") or {}
        order, allocations, error_message, is_replay = create_sales_order(
            channel_name,
            external_sku_id,
            quantity,
            extra_data=extra_data,
            external_order_no=external_order_no,
            commit=True,
        )
        if error_message:
            return api_response(code=409, msg=error_message)

        return api_response(
            data={
                "order": serialize_order(order),
                "allocations": [allocation.to_dict() for allocation in allocations],
                "idempotent_replay": is_replay,
            }
        )

    @app.post("/api/v1/orders/import/preview")
    @jwt_required()
    def orders_import_preview():
        upload = request.files.get("file")
        mapping_raw = request.form.get("mapping") or ""
        default_channel_name = (request.form.get("default_channel_name") or "").strip()
        template_name = (request.form.get("template") or "generic").strip() or "generic"

        if not upload:
            return api_response(code=400, msg="file is required")

        mapping = {}
        if mapping_raw:
            try:
                import json

                mapping = json.loads(mapping_raw) or {}
            except Exception:
                return api_response(code=400, msg="mapping must be valid JSON")

        try:
            result = build_order_rows_from_file(
                file_stream=upload.stream,
                filename=upload.filename or "orders.csv",
                mapping=mapping,
                default_channel_name=default_channel_name,
                template_name=template_name,
            )
        except ValueError as exc:
            return api_response(code=400, msg=str(exc))

        return api_response(
            data={
                "columns": result["columns"],
                "mapping_guess": result["mapping_guess"],
                "mapping_effective": result["mapping_effective"],
                "preview_rows": result["preview_rows"],
                "total_rows": result["total_rows"],
                "valid_rows": result["valid_rows"],
                "error_rows": result["error_rows"],
                "errors": result["errors"],
                "template": result["template"],
            }
        )

    @app.post("/api/v1/orders/import")
    @jwt_required()
    def orders_import_commit():
        upload = request.files.get("file")
        mapping_raw = request.form.get("mapping") or ""
        default_channel_name = (request.form.get("default_channel_name") or "").strip()
        template_name = (request.form.get("template") or "generic").strip() or "generic"

        if not upload:
            return api_response(code=400, msg="file is required")

        mapping = {}
        if mapping_raw:
            try:
                import json

                mapping = json.loads(mapping_raw) or {}
            except Exception:
                return api_response(code=400, msg="mapping must be valid JSON")

        try:
            parsed = build_order_rows_from_file(
                file_stream=upload.stream,
                filename=upload.filename or "orders.csv",
                mapping=mapping,
                default_channel_name=default_channel_name,
                template_name=template_name,
            )
        except ValueError as exc:
            return api_response(code=400, msg=str(exc))

        created = 0
        replayed = 0
        imported = []
        errors = list(parsed.get("errors") or [])

        for row in parsed.get("rows") or []:
            row_number = row.get("row_number")
            payload = row.get("payload") or {}

            nested = db.session.begin_nested()
            try:
                external_order_no = None
                if isinstance(payload.get("extra_data"), dict):
                    external_order_no = (payload["extra_data"].get("external_order_no") or "").strip() or None

                order, allocations, error_message, is_replay = create_sales_order(
                    payload["channel_name"],
                    payload["external_sku_id"],
                    payload["quantity"],
                    extra_data=payload.get("extra_data") or {},
                    external_order_no=external_order_no,
                    commit=False,
                )
                if error_message:
                    nested.rollback()
                    errors.append({"row_number": row_number, "error": error_message})
                    continue

                nested.commit()
                if is_replay:
                    replayed += 1
                else:
                    created += 1
                imported.append({"order": serialize_order(order), "allocations": [a.to_dict() for a in allocations]})
            except Exception as exc:  # noqa: BLE001 - isolate per-row failures
                nested.rollback()
                errors.append({"row_number": row_number, "error": str(exc)})

        db.session.commit()

        return api_response(
            data={
                "total_rows": parsed["total_rows"],
                "valid_rows": parsed["valid_rows"],
                "error_rows": len(errors),
                "created": created,
                "replayed": replayed,
                "preview_rows": parsed["preview_rows"],
                "imported_rows": imported[:20],
                "errors": errors[:20],
                "template": parsed["template"],
            }
        )

    @app.post("/api/v1/orders/fulfill")
    @admin_required
    def fulfill_order():
        payload = request.get_json(silent=True) or {}
        order_id, order_id_error = parse_positive_int(payload.get("order_id"), "order_id")
        if order_id_error:
            return api_response(code=400, msg=order_id_error)

        order = db.session.get(SalesOrder, order_id)
        if not order:
            return api_response(code=404, msg="order not found")

        transactions, error_message = fulfill_sales_order(order)
        if error_message:
            return api_response(code=409, msg=error_message)

        return api_response(
            data={
                "order": serialize_order(order),
                "transactions": [transaction.to_dict() for transaction in transactions],
            }
        )

    @app.get("/api/v1/reports/export")
    @admin_required
    def export_report():
        export_format = (request.args.get("format") or "csv").strip().lower()
        if export_format not in {"csv", "xlsx"}:
            return api_response(code=400, msg="format must be one of: csv, xlsx")

        rows = build_export_rows()

        try:
            import pandas as pd
        except ImportError:
            return api_response(code=500, msg="pandas is required for export")

        dataframe = pd.DataFrame(rows)

        if export_format == "csv":
            csv_payload = dataframe.to_csv(index=False)
            return Response(
                csv_payload,
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment; filename=roseate_report.csv"},
            )

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            dataframe.to_excel(writer, index=False, sheet_name="report")
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="roseate_report.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @app.get("/api/v1/reports/ledger-export")
    @admin_required
    def export_ledger_report():
        export_format = (request.args.get("format") or "csv").strip().lower()
        if export_format not in {"csv", "xlsx"}:
            return api_response(code=400, msg="format must be one of: csv, xlsx")

        balance_scope = (request.args.get("balance_scope") or "product").strip().lower()
        if balance_scope not in {"product", "batch"}:
            return api_response(code=400, msg="balance_scope must be one of: product, batch")

        include_batch = (request.args.get("include_batch") or "").strip().lower() in {"1", "true", "yes"}

        columns, rows = build_ledger_rows(balance_scope=balance_scope, include_batch=include_batch)

        try:
            import pandas as pd
        except ImportError:
            return api_response(code=500, msg="pandas is required for export")

        dataframe = pd.DataFrame(rows, columns=columns)

        if export_format == "csv":
            csv_payload = dataframe.to_csv(index=False)
            return Response(
                csv_payload,
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment; filename=roseate_ledger.csv"},
            )

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            dataframe.to_excel(writer, index=False, sheet_name="ledger")
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="roseate_ledger.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @app.get("/api/v1/channel-mappings")
    @jwt_required()
    def list_channel_mappings():
        channel_name = (request.args.get("channel_name") or "").strip()
        external_sku_id = (request.args.get("external_sku_id") or "").strip()
        query = ChannelMapping.query

        if channel_name:
            query = query.filter(ChannelMapping.channel_name.ilike(f"%{channel_name}%"))
        if external_sku_id:
            query = query.filter(ChannelMapping.external_sku_id.ilike(f"%{external_sku_id}%"))

        mappings = query.order_by(ChannelMapping.channel_name.asc(), ChannelMapping.id.asc()).all()
        return api_response(
            data={
                "items": [mapping.to_dict() for mapping in mappings],
                "total": len(mappings),
            }
        )

    @app.get("/api/v1/channel-mappings/lookup")
    @jwt_required()
    def lookup_channel_mapping():
        channel_name = (request.args.get("channel_name") or "").strip()
        external_sku_id = (request.args.get("external_sku_id") or "").strip()

        if not channel_name or not external_sku_id:
            return api_response(code=400, msg="channel_name and external_sku_id are required")

        mapping = ChannelMapping.query.filter_by(
            channel_name=channel_name,
            external_sku_id=external_sku_id,
        ).first()
        if not mapping:
            return api_response(code=404, msg="channel mapping not found")

        return api_response(
            data={
                "hb_code": mapping.hb_code,
                "mapping": mapping.to_dict(),
            }
        )

    @app.post("/api/v1/channel-mappings")
    @admin_required
    def create_channel_mapping():
        payload = request.get_json(silent=True) or {}

        channel_name = (payload.get("channel_name") or "").strip()
        external_sku_id = (payload.get("external_sku_id") or "").strip()
        hb_code = (payload.get("hb_code") or "").strip()
        extra_data = payload.get("extra_data") or {}

        if not all([channel_name, external_sku_id, hb_code]):
            return api_response(code=400, msg="channel_name, external_sku_id and hb_code are required")

        product = Product.query.filter_by(hb_code=hb_code).first()
        if not product:
            return api_response(code=404, msg="product not found")

        existing_mapping = ChannelMapping.query.filter_by(
            channel_name=channel_name,
            external_sku_id=external_sku_id,
        ).first()
        if existing_mapping:
            return api_response(code=409, msg="channel mapping already exists")

        mapping = ChannelMapping(
            channel_name=channel_name,
            external_sku_id=external_sku_id,
            hb_code=hb_code,
        )
        mapping.set_extra_data(extra_data)
        db.session.add(mapping)
        db.session.commit()

        return api_response(code=201, data={"mapping": mapping.to_dict()})

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def serve_frontend(path):
        if path.startswith("api/"):
            return api_response(code=404, msg="resource not found")

        frontend_dist_dir = Path(app.config["FRONTEND_DIST_DIR"])
        if not frontend_dist_dir.exists():
            return api_response(code=404, msg="frontend dist not found")

        if path:
            requested_file = frontend_dist_dir / path
            if requested_file.is_file():
                return send_from_directory(frontend_dist_dir, path)

            if Path(path).suffix:
                return api_response(code=404, msg="static asset not found")

        return send_from_directory(frontend_dist_dir, "index.html")


app = create_app()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="roseate-wms backend dev server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true", default=True)
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=args.debug)
