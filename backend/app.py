from datetime import date, datetime, timedelta
from functools import wraps
from io import BytesIO
import os
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from flask import Flask, Response, jsonify, request, send_file
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
    InventoryTransaction,
    OrderAllocation,
    Product,
    SalesOrder,
    User,
)
from backend.services.import_service import classify_expiry_status, import_from_csv


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
            return product

    if barcode:
        return Product.query.filter_by(barcode=barcode).first()

    return None


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


def create_sales_order(channel_name, external_sku_id, quantity):
    mapping = ChannelMapping.query.filter_by(
        channel_name=channel_name,
        external_sku_id=external_sku_id,
    ).first()
    if not mapping:
        return None, None, "channel mapping not found"

    product = Product.query.filter_by(hb_code=mapping.hb_code).first()
    if not product:
        return None, None, "product not found"

    allocations, reserve_error = reserve_product_inventory(product, quantity)
    if reserve_error:
        return None, None, reserve_error

    order = SalesOrder(
        channel_name=channel_name,
        external_sku_id=external_sku_id,
        hb_code=product.hb_code,
        quantity=quantity,
        status="reserved",
    )
    order.set_extra_data({"source": "external_sync"})
    db.session.add(order)
    db.session.flush()

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

    db.session.commit()
    db.session.refresh(order)

    return order, persisted_allocations, None


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

        transaction = InventoryTransaction(
            hb_code=order.hb_code,
            batch_id=batch.id,
            order_id=order.id,
            transaction_type="OUT",
            quantity=allocation.quantity,
        )
        transaction.set_extra_data(
            {
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

    @app.get("/api/v1/inventory/test")
    @jwt_required()
    def inventory_test():
        claims = get_jwt()
        return api_response(
            data={
                "message": "inventory test endpoint is protected",
                "current_user": {
                    "id": get_jwt_identity(),
                    "username": claims.get("username"),
                    "role": claims.get("role"),
                },
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
    @jwt_required()
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

    @app.post("/api/v1/inventory/inbound")
    @jwt_required()
    def inventory_inbound():
        payload = request.get_json(silent=True) or {}

        product = find_product(payload)
        if not product:
            return api_response(code=404, msg="product not found")

        batch_no = (payload.get("batch_no") or "").strip()
        if not batch_no:
            return api_response(code=400, msg="batch_no is required")

        expiry_date, expiry_error = parse_date(
            payload.get("expiry_date"),
            "expiry_date",
            required=True,
        )
        if expiry_error:
            return api_response(code=400, msg=expiry_error)

        production_date, production_error = parse_date(
            payload.get("production_date"),
            "production_date",
        )
        if production_error:
            return api_response(code=400, msg=production_error)

        quantity, quantity_error = parse_positive_int(payload.get("quantity"), "quantity")
        if quantity_error:
            return api_response(code=400, msg=quantity_error)

        cost, cost_error = parse_non_negative_float(payload.get("cost"), "cost")
        if cost_error:
            return api_response(code=400, msg=cost_error)

        unit_type = (payload.get("unit_type") or "base").strip().lower()
        if unit_type not in {"base", "purchase"}:
            return api_response(code=400, msg="unit_type must be one of: base, purchase")

        normalized_quantity = normalize_inbound_quantity(product, quantity, unit_type)
        extra_data = payload.get("extra_data") or {}

        batch = Batch.query.filter_by(hb_code=product.hb_code, expiry_date=expiry_date).first()
        action = "created"

        if batch:
            batch.current_quantity += normalized_quantity
            batch.initial_quantity += normalized_quantity
            batch.cost = cost
            if not batch.production_date and production_date:
                batch.production_date = production_date
            merge_batch_extra_data(batch, extra_data, batch_no)
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
            batch.set_extra_data(extra_data)
            db.session.add(batch)

        db.session.commit()

        return api_response(
            data={
                "action": action,
                "product": product.to_dict(include_stock=True),
                "batch": batch.to_dict(),
                "normalized_quantity": normalized_quantity,
                "unit_type": unit_type,
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
        quantity, quantity_error = parse_positive_int(payload.get("quantity", 1), "quantity")

        if not channel_name or not external_sku_id:
            return api_response(code=400, msg="channel_name and external_sku_id are required")
        if quantity_error:
            return api_response(code=400, msg=quantity_error)

        order, allocations, error_message = create_sales_order(channel_name, external_sku_id, quantity)
        if error_message:
            return api_response(code=409, msg=error_message)

        return api_response(
            data={
                "order": serialize_order(order),
                "allocations": [allocation.to_dict() for allocation in allocations],
            }
        )

    @app.post("/api/v1/orders/fulfill")
    @jwt_required()
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


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
