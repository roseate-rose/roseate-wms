import json

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

    batches = db.relationship(
        "Batch",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Batch.expiry_date.asc()",
    )

    @property
    def total_stock(self) -> int:
        return sum(batch.current_quantity for batch in self.batches if batch.current_quantity > 0)

    def to_dict(self, include_stock=False):
        payload = {
            "hb_code": self.hb_code,
            "barcode": self.barcode,
            "name": self.name,
            "spec": self.spec,
            "unit": self.unit,
            "extra_data": self.get_extra_data(),
        }

        if include_stock:
            payload["total_stock"] = self.total_stock

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

    product = db.relationship("Product", back_populates="batches")

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
            "extra_data": self.get_extra_data(),
        }
