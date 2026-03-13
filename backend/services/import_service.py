import csv
from datetime import date
from io import StringIO

from backend.extensions import db
from backend.models import Batch, Product

DEFAULT_EXPIRY_DATE = date(2099, 12, 31)


def classify_expiry_status(expiry_date, today=None):
    today = today or date.today()
    # Business rule: expiry_date == today is treated as expired.
    if expiry_date <= today:
        return "expired"
    if expiry_date <= date.fromordinal(today.toordinal() + 30):
        return "warning"
    return "healthy"


def _parse_date(value):
    if value in {None, ""}:
        return DEFAULT_EXPIRY_DATE
    return date.fromisoformat(value)


def _parse_optional_date(value):
    if value in {None, ""}:
        return None
    return date.fromisoformat(value)


def _parse_int(value, field_name):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc

    if parsed <= 0:
        raise ValueError(f"{field_name} must be greater than 0")

    return parsed


def _parse_float(value, field_name, default=0.0):
    if value in {None, ""}:
        return default

    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc

    if parsed < 0:
        raise ValueError(f"{field_name} must be greater than or equal to 0")

    return parsed


def parse_csv_rows(file_stream):
    raw_bytes = file_stream.read()
    if isinstance(raw_bytes, bytes):
        text = raw_bytes.decode("utf-8-sig")
    else:
        text = str(raw_bytes)

    if not text.strip():
        raise ValueError("csv file is empty")

    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("csv header is required")

    required_columns = {"hb_code", "quantity"}
    missing_columns = required_columns - set(reader.fieldnames)
    if missing_columns:
        raise ValueError(f"missing required columns: {', '.join(sorted(missing_columns))}")

    rows = []
    for index, row in enumerate(reader, start=1):
        hb_code = (row.get("hb_code") or "").strip()
        if not hb_code:
            raise ValueError(f"row {index}: hb_code is required")

        product = Product.query.filter_by(hb_code=hb_code).first()
        if not product:
            raise ValueError(f"row {index}: product {hb_code} not found")

        quantity = _parse_int(row.get("quantity"), f"row {index} quantity")
        unit_type = (row.get("unit_type") or "base").strip().lower() or "base"
        if unit_type not in {"base", "purchase"}:
            raise ValueError(f"row {index}: unit_type must be base or purchase")

        normalized_quantity = quantity * product.conversion_rate if unit_type == "purchase" else quantity
        expiry_date = _parse_date((row.get("expiry_date") or "").strip())
        production_date = _parse_optional_date((row.get("production_date") or "").strip())
        cost = _parse_float((row.get("cost") or "").strip(), f"row {index} cost", default=0.0)
        batch_no = (row.get("batch_no") or "").strip() or f"CSV-{index:04d}"

        rows.append(
            {
                "row_number": index,
                "hb_code": hb_code,
                "product_name": product.name,
                "batch_no": batch_no,
                "quantity": quantity,
                "unit_type": unit_type,
                "normalized_quantity": normalized_quantity,
                "expiry_date": expiry_date,
                "production_date": production_date,
                "cost": cost,
            }
        )

    return rows


def import_from_csv(file_stream, merge_mode="accumulate", commit=True):
    if merge_mode not in {"accumulate", "overwrite"}:
        raise ValueError("merge_mode must be accumulate or overwrite")

    rows = parse_csv_rows(file_stream)
    imported_rows = []

    for row in rows:
        batch = Batch.query.filter_by(
            hb_code=row["hb_code"],
            expiry_date=row["expiry_date"],
        ).first()

        if commit:
            if batch:
                if merge_mode == "overwrite":
                    batch.batch_no = row["batch_no"]
                    batch.production_date = row["production_date"]
                    batch.cost = row["cost"]
                    batch.initial_quantity = row["normalized_quantity"]
                    batch.current_quantity = row["normalized_quantity"]
                    batch.reserved_quantity = min(batch.reserved_quantity, batch.current_quantity)
                    action = "overwritten"
                else:
                    old_qty = batch.current_quantity
                    total_qty = old_qty + row["normalized_quantity"]
                    if total_qty > 0:
                        batch.cost = round(
                            (old_qty * batch.cost + row["normalized_quantity"] * row["cost"]) / total_qty,
                            6,
                        )
                    else:
                        batch.cost = row["cost"]
                    batch.current_quantity += row["normalized_quantity"]
                    batch.initial_quantity += row["normalized_quantity"]
                    if not batch.production_date and row["production_date"]:
                        batch.production_date = row["production_date"]
                    action = "merged"
            else:
                batch = Batch(
                    hb_code=row["hb_code"],
                    batch_no=row["batch_no"],
                    production_date=row["production_date"],
                    expiry_date=row["expiry_date"],
                    cost=row["cost"],
                    initial_quantity=row["normalized_quantity"],
                    current_quantity=row["normalized_quantity"],
                    reserved_quantity=0,
                )
                batch.set_extra_data({"imported": True, "source": "csv"})
                db.session.add(batch)
                action = "created"
        else:
            action = "preview"

        imported_rows.append(
            {
                "row_number": row["row_number"],
                "hb_code": row["hb_code"],
                "product_name": row["product_name"],
                "batch_no": row["batch_no"],
                "quantity": row["quantity"],
                "unit_type": row["unit_type"],
                "normalized_quantity": row["normalized_quantity"],
                "expiry_date": row["expiry_date"].isoformat(),
                "production_date": row["production_date"].isoformat() if row["production_date"] else None,
                "cost": row["cost"],
                "action": action,
            }
        )

    if commit:
        db.session.commit()

    return {
        "total_rows": len(imported_rows),
        "preview_rows": imported_rows[:5],
        "imported_rows": imported_rows,
    }
