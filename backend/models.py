import json
from datetime import date, datetime

from werkzeug.security import check_password_hash, generate_password_hash

from backend.extensions import db


class ExtraDataMixin:
    extra_data = db.Column(db.Text, nullable=False, default="{}")

    def set_extra_data(self, payload) -> None:
        self.extra_data = json.dumps(payload or {}, ensure_ascii=False)

    def get_extra_data(self):
        try:
            return json.loads(self.extra_data or "{}")
        except json.JSONDecodeError:
            return {}


class TimestampMixin:
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class User(ExtraDataMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="staff")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "extra_data": self.get_extra_data(),
        }


class Product(ExtraDataMixin, db.Model):
    __tablename__ = "products"

    hb_code = db.Column(db.String(50), primary_key=True)
    barcode = db.Column(db.String(50), nullable=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    spec = db.Column(db.String(80), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    base_unit = db.Column(db.String(20), nullable=False, default="件")
    purchase_unit = db.Column(db.String(20), nullable=False, default="件")
    conversion_rate = db.Column(db.Integer, nullable=False, default=1)

    batches = db.relationship(
        "Batch",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Batch.expiry_date.asc(), Batch.id.asc()",
    )
    channel_mappings = db.relationship(
        "ChannelMapping",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    orders = db.relationship(
        "SalesOrder",
        back_populates="product",
        lazy="selectin",
    )
    inventory_transactions = db.relationship(
        "InventoryTransaction",
        back_populates="product",
        lazy="selectin",
    )

    @property
    def total_stock(self) -> int:
        return sum(batch.current_quantity for batch in self.batches if batch.current_quantity > 0)

    @property
    def reserved_stock(self) -> int:
        return sum(batch.reserved_quantity for batch in self.batches if batch.reserved_quantity > 0)

    @property
    def sellable_stock(self) -> int:
        today = date.today()
        return sum(
            batch.available_quantity
            for batch in self.batches
            if batch.available_quantity > 0 and batch.expiry_date and batch.expiry_date > today
        )

    def to_dict(self, include_stock=False, include_batches=False, include_mappings=False):
        payload = {
            "hb_code": self.hb_code,
            "barcode": self.barcode,
            "name": self.name,
            "spec": self.spec,
            "unit": self.unit,
            "base_unit": self.base_unit,
            "purchase_unit": self.purchase_unit,
            "conversion_rate": self.conversion_rate,
            "extra_data": self.get_extra_data(),
        }

        if include_stock:
            payload.update(
                {
                    "total_stock": self.total_stock,
                    "reserved_stock": self.reserved_stock,
                    "sellable_stock": self.sellable_stock,
                }
            )

        if include_batches:
            payload["batches"] = [batch.to_dict() for batch in self.batches]

        if include_mappings:
            payload["channel_mappings"] = [mapping.to_dict() for mapping in self.channel_mappings]

        return payload


class Batch(ExtraDataMixin, db.Model):
    __tablename__ = "batches"
    __table_args__ = (
        db.UniqueConstraint("hb_code", "expiry_date", name="uq_batch_hb_code_expiry_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    hb_code = db.Column(db.String(50), db.ForeignKey("products.hb_code"), nullable=False, index=True)
    batch_no = db.Column(db.String(80), nullable=False)
    production_date = db.Column(db.Date, nullable=True)
    expiry_date = db.Column(db.Date, nullable=False, index=True)
    cost = db.Column(db.Float, nullable=False, default=0.0)
    initial_quantity = db.Column(db.Integer, nullable=False, default=0)
    current_quantity = db.Column(db.Integer, nullable=False, default=0)
    reserved_quantity = db.Column(db.Integer, nullable=False, default=0)

    product = db.relationship("Product", back_populates="batches")
    allocations = db.relationship(
        "OrderAllocation",
        back_populates="batch",
        lazy="selectin",
    )
    inventory_transactions = db.relationship(
        "InventoryTransaction",
        back_populates="batch",
        lazy="selectin",
    )

    @property
    def available_quantity(self) -> int:
        return max(self.current_quantity - self.reserved_quantity, 0)

    def to_dict(self):
        return {
            "id": self.id,
            "hb_code": self.hb_code,
            "batch_no": self.batch_no,
            "production_date": self.production_date.isoformat() if self.production_date else None,
            "expiry_date": self.expiry_date.isoformat(),
            "cost": self.cost,
            "initial_quantity": self.initial_quantity,
            "current_quantity": self.current_quantity,
            "reserved_quantity": self.reserved_quantity,
            "available_quantity": self.available_quantity,
            "base_unit": self.product.base_unit if self.product else None,
            "purchase_unit": self.product.purchase_unit if self.product else None,
            "conversion_rate": self.product.conversion_rate if self.product else None,
            "extra_data": self.get_extra_data(),
        }


class ChannelMapping(ExtraDataMixin, db.Model):
    __tablename__ = "channel_mappings"
    __table_args__ = (
        db.UniqueConstraint(
            "channel_name",
            "external_sku_id",
            name="uq_channel_mapping_channel_external",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    channel_name = db.Column(db.String(50), nullable=False, index=True)
    external_sku_id = db.Column(db.String(100), nullable=False, index=True)
    hb_code = db.Column(db.String(50), db.ForeignKey("products.hb_code"), nullable=False, index=True)

    product = db.relationship("Product", back_populates="channel_mappings")

    def to_dict(self):
        return {
            "id": self.id,
            "channel_name": self.channel_name,
            "external_sku_id": self.external_sku_id,
            "hb_code": self.hb_code,
            "extra_data": self.get_extra_data(),
        }


class InboundReceipt(TimestampMixin, ExtraDataMixin, db.Model):
    __tablename__ = "inbound_receipts"

    id = db.Column(db.Integer, primary_key=True)
    receipt_no = db.Column(db.String(80), nullable=False, unique=True, index=True)
    received_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    supplier_name = db.Column(db.String(120), nullable=True, index=True)
    remark = db.Column(db.String(255), nullable=True)

    lines = db.relationship(
        "InboundLine",
        back_populates="receipt",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="InboundLine.id.asc()",
    )

    def to_dict(self, include_lines=False):
        payload = {
            "id": self.id,
            "receipt_no": self.receipt_no,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "supplier_name": self.supplier_name,
            "remark": self.remark,
            "extra_data": self.get_extra_data(),
        }

        if include_lines:
            payload["lines"] = [line.to_dict() for line in self.lines]

        return payload


class InboundLine(TimestampMixin, ExtraDataMixin, db.Model):
    __tablename__ = "inbound_lines"

    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey("inbound_receipts.id"), nullable=False, index=True)
    hb_code = db.Column(db.String(50), db.ForeignKey("products.hb_code"), nullable=False, index=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("batches.id"), nullable=True, index=True)

    batch_no = db.Column(db.String(80), nullable=False)
    production_date = db.Column(db.Date, nullable=True)
    expiry_date = db.Column(db.Date, nullable=False, index=True)

    unit_type = db.Column(db.String(20), nullable=False, default="base")
    quantity_input = db.Column(db.Integer, nullable=False, default=0)
    normalized_quantity = db.Column(db.Integer, nullable=False, default=0)
    unit_cost = db.Column(db.Float, nullable=False, default=0.0)

    receipt = db.relationship("InboundReceipt", back_populates="lines")
    product = db.relationship("Product", lazy="selectin")
    batch = db.relationship("Batch", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "receipt_id": self.receipt_id,
            "hb_code": self.hb_code,
            "batch_id": self.batch_id,
            "batch_no": self.batch_no,
            "production_date": self.production_date.isoformat() if self.production_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "unit_type": self.unit_type,
            "quantity_input": self.quantity_input,
            "normalized_quantity": self.normalized_quantity,
            "unit_cost": self.unit_cost,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "extra_data": self.get_extra_data(),
        }


class SalesOrder(TimestampMixin, ExtraDataMixin, db.Model):
    __tablename__ = "sales_orders"

    id = db.Column(db.Integer, primary_key=True)
    channel_name = db.Column(db.String(50), nullable=False, index=True)
    external_sku_id = db.Column(db.String(100), nullable=False, index=True)
    hb_code = db.Column(db.String(50), db.ForeignKey("products.hb_code"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="reserved", index=True)
    fulfilled_at = db.Column(db.DateTime, nullable=True)

    product = db.relationship("Product", back_populates="orders")
    allocations = db.relationship(
        "OrderAllocation",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="OrderAllocation.id.asc()",
    )
    transactions = db.relationship(
        "InventoryTransaction",
        back_populates="order",
        lazy="selectin",
    )

    def to_dict(self, include_allocations=False):
        payload = {
            "id": self.id,
            "channel_name": self.channel_name,
            "external_sku_id": self.external_sku_id,
            "hb_code": self.hb_code,
            "quantity": self.quantity,
            "status": self.status,
            "fulfilled_at": self.fulfilled_at.isoformat() if self.fulfilled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "base_unit": self.product.base_unit if self.product else None,
            "purchase_unit": self.product.purchase_unit if self.product else None,
            "conversion_rate": self.product.conversion_rate if self.product else None,
            "extra_data": self.get_extra_data(),
        }

        if include_allocations:
            payload["allocations"] = [allocation.to_dict() for allocation in self.allocations]

        return payload


class ExternalOrderRef(TimestampMixin, ExtraDataMixin, db.Model):
    """
    Idempotency mapping for external orders.

    We keep this as a separate table to avoid schema migrations on the `sales_orders`
    table while still enabling fast lookups and uniqueness constraints in SQLite.
    """

    __tablename__ = "external_order_refs"
    __table_args__ = (
        db.UniqueConstraint(
            "channel_name",
            "external_order_no",
            name="uq_external_order_ref_channel_order_no",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    channel_name = db.Column(db.String(50), nullable=False, index=True)
    external_order_no = db.Column(db.String(120), nullable=False, index=True)
    external_sku_id = db.Column(db.String(100), nullable=True, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id"), nullable=False, index=True)

    order = db.relationship("SalesOrder", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "channel_name": self.channel_name,
            "external_order_no": self.external_order_no,
            "external_sku_id": self.external_sku_id,
            "order_id": self.order_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "extra_data": self.get_extra_data(),
        }


class OrderAllocation(TimestampMixin, ExtraDataMixin, db.Model):
    __tablename__ = "order_allocations"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id"), nullable=False, index=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("batches.id"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)

    order = db.relationship("SalesOrder", back_populates="allocations")
    batch = db.relationship("Batch", back_populates="allocations")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "batch_id": self.batch_id,
            "batch_no": self.batch.batch_no if self.batch else None,
            "expiry_date": self.batch.expiry_date.isoformat() if self.batch else None,
            "quantity": self.quantity,
            "extra_data": self.get_extra_data(),
        }


class InventoryTransaction(TimestampMixin, ExtraDataMixin, db.Model):
    __tablename__ = "inventory_transactions"

    id = db.Column(db.Integer, primary_key=True)
    hb_code = db.Column(db.String(50), db.ForeignKey("products.hb_code"), nullable=False, index=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("batches.id"), nullable=True, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id"), nullable=True, index=True)
    transaction_type = db.Column(db.String(20), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)

    product = db.relationship("Product", back_populates="inventory_transactions")
    batch = db.relationship("Batch", back_populates="inventory_transactions")
    order = db.relationship("SalesOrder", back_populates="transactions")

    def to_dict(self):
        return {
            "id": self.id,
            "hb_code": self.hb_code,
            "batch_id": self.batch_id,
            "order_id": self.order_id,
            "transaction_type": self.transaction_type,
            "quantity": self.quantity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "extra_data": self.get_extra_data(),
        }
