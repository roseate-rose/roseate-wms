from datetime import date, timedelta
import os
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from flask import Flask, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy import or_

from backend.extensions import db, jwt
from backend.models import Batch, Product, User


def api_response(code=200, data=None, msg="success"):
    return jsonify({"code": code, "data": data or {}, "msg": msg}), code


def parse_date(value, field_name, required=False):
    if value in {None, ""}:
        if required:
            return None, f"{field_name} is required"
        return None, None

    try:
        return date.fromisoformat(value), None
    except ValueError:
        return None, f"{field_name} must be in YYYY-MM-DD format"


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

    @app.post("/api/v1/products")
    @jwt_required()
    def create_product():
        payload = request.get_json(silent=True) or {}

        hb_code = (payload.get("hb_code") or "").strip()
        name = (payload.get("name") or "").strip()
        spec = (payload.get("spec") or "").strip()
        unit = (payload.get("unit") or "").strip()
        barcode = (payload.get("barcode") or "").strip() or None
        extra_data = payload.get("extra_data") or {}

        if not all([hb_code, name, spec, unit]):
            return api_response(code=400, msg="hb_code, name, spec and unit are required")

        if Product.query.filter_by(hb_code=hb_code).first():
            return api_response(code=409, msg="product hb_code already exists")

        product = Product(
            hb_code=hb_code,
            barcode=barcode,
            name=name,
            spec=spec,
            unit=unit,
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

        try:
            quantity = int(payload.get("quantity"))
        except (TypeError, ValueError):
            return api_response(code=400, msg="quantity must be an integer")

        if quantity <= 0:
            return api_response(code=400, msg="quantity must be greater than 0")

        try:
            cost = float(payload.get("cost"))
        except (TypeError, ValueError):
            return api_response(code=400, msg="cost must be a number")

        if cost < 0:
            return api_response(code=400, msg="cost must be greater than or equal to 0")

        extra_data = payload.get("extra_data") or {}

        batch = Batch.query.filter_by(hb_code=product.hb_code, expiry_date=expiry_date).first()
        action = "created"

        if batch:
            batch.current_quantity += quantity
            batch.initial_quantity += quantity
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
                initial_quantity=quantity,
                current_quantity=quantity,
            )
            batch.set_extra_data(extra_data)
            db.session.add(batch)

        db.session.commit()

        return api_response(
            data={
                "action": action,
                "product": product.to_dict(include_stock=True),
                "batch": batch.to_dict(),
            }
        )


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
