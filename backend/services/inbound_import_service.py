from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.models import Batch, Product
from backend.services.tabular_service import build_row_extra_data, guess_column, read_tabular


DEFAULT_EXPIRY_DATE = date(2099, 12, 31)


def _safe_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_int(value, default: Optional[int] = None) -> Optional[int]:
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_date(value, *, default: Optional[date] = None) -> Optional[date]:
    if value in (None, ""):
        return default
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    raw = str(value).strip()
    if not raw:
        return default
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def normalize_unit_type(value) -> str:
    raw = _safe_str(value).lower()
    if not raw:
        return "base"
    if raw in {"purchase", "采购", "采购单位", "盒", "箱"}:
        return "purchase"
    # Tolerate values like "purchase_unit" or "采购入库"
    if "purchase" in raw or "采购" in raw:
        return "purchase"
    return "base"


def guess_inbound_mapping(columns: List[str]) -> Dict[str, Optional[str]]:
    return {
        "hb_code": guess_column(columns, ["hb_code", "hb编码", "内部编码", "商品编码", "蕴香编码"]),
        "barcode": guess_column(columns, ["barcode", "条码", "国际条码", "ean", "upc"]),
        "batch_no": guess_column(columns, ["batch_no", "批号", "批次", "生产批号"]),
        "expiry_date": guess_column(columns, ["expiry_date", "到期日", "有效期至", "失效日期"]),
        "production_date": guess_column(columns, ["production_date", "生产日期", "生产日"]),
        "quantity": guess_column(columns, ["quantity", "数量", "入库数量", "件数"]),
        "unit_type": guess_column(columns, ["unit_type", "单位类型", "入库单位", "单位"]),
        "cost": guess_column(columns, ["cost", "单价", "成本", "入库单价", "采购单价"]),
        "receipt_no": guess_column(columns, ["receipt_no", "入库单号", "单据号", "单号"]),
        "supplier_name": guess_column(columns, ["supplier_name", "供应商", "供货商"]),
        "remark": guess_column(columns, ["remark", "备注"]),
    }


def build_inbound_rows_from_file(
    *,
    file_stream,
    filename: str,
    mapping: Optional[Dict[str, str]] = None,
    default_receipt_no: Optional[str] = None,
    default_supplier_name: Optional[str] = None,
    default_remark: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse inbound-import file into normalized per-row payloads.
    This function does not write to DB; it only validates and enriches with lookup data.

    Required: (hb_code or barcode), quantity
    Optional: expiry_date (defaults to 2099-12-31), batch_no (defaults to IMPORT-0001), unit_type (defaults base), cost (defaults 0).
    """

    columns, raw_rows = read_tabular(file_stream, filename=filename)
    guessed = guess_inbound_mapping(columns)
    effective_mapping: Dict[str, str] = {}
    for key, col in (mapping or {}).items():
        if col:
            effective_mapping[key] = col
    for key, col in guessed.items():
        if key not in effective_mapping and col:
            effective_mapping[key] = col

    rows: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    simulated_batches: Dict[Tuple[str, date], bool] = {}

    for idx, raw in enumerate(raw_rows, start=1):
        hb_code = _safe_str(raw.get(effective_mapping.get("hb_code", ""))) if effective_mapping.get("hb_code") else ""
        barcode = _safe_str(raw.get(effective_mapping.get("barcode", ""))) if effective_mapping.get("barcode") else ""
        if not hb_code and not barcode:
            errors.append({"row_number": idx, "error": "hb_code or barcode is required", "raw": raw})
            continue

        product = None
        if hb_code:
            product = Product.query.filter_by(hb_code=hb_code).first()
        if not product and barcode:
            product = Product.query.filter_by(barcode=barcode).first()
        if not product:
            errors.append({"row_number": idx, "error": "product not found", "raw": raw})
            continue

        quantity_value = raw.get(effective_mapping.get("quantity", "")) if effective_mapping.get("quantity") else None
        quantity = _safe_int(quantity_value)
        if not quantity or quantity <= 0:
            errors.append({"row_number": idx, "error": "quantity must be a positive integer", "raw": raw})
            continue

        unit_value = raw.get(effective_mapping.get("unit_type", "")) if effective_mapping.get("unit_type") else None
        unit_type = normalize_unit_type(unit_value)

        expiry_value = raw.get(effective_mapping.get("expiry_date", "")) if effective_mapping.get("expiry_date") else None
        expiry_date = _parse_date(expiry_value, default=DEFAULT_EXPIRY_DATE)
        if not expiry_date:
            errors.append({"row_number": idx, "error": "expiry_date must be in YYYY-MM-DD format", "raw": raw})
            continue

        prod_value = raw.get(effective_mapping.get("production_date", "")) if effective_mapping.get("production_date") else None
        production_date = _parse_date(prod_value, default=None)
        if effective_mapping.get("production_date") and prod_value not in (None, "") and not production_date:
            errors.append({"row_number": idx, "error": "production_date must be in YYYY-MM-DD format", "raw": raw})
            continue

        batch_value = raw.get(effective_mapping.get("batch_no", "")) if effective_mapping.get("batch_no") else None
        batch_no = _safe_str(batch_value) or f"IMPORT-{idx:04d}"

        cost_value = raw.get(effective_mapping.get("cost", "")) if effective_mapping.get("cost") else None
        cost = _safe_float(cost_value, default=0.0)
        if cost < 0:
            cost = 0.0

        receipt_value = raw.get(effective_mapping.get("receipt_no", "")) if effective_mapping.get("receipt_no") else None
        receipt_no = _safe_str(receipt_value) or (default_receipt_no or "")

        supplier_value = raw.get(effective_mapping.get("supplier_name", "")) if effective_mapping.get("supplier_name") else None
        supplier_name = _safe_str(supplier_value) or (default_supplier_name or "")

        remark_value = raw.get(effective_mapping.get("remark", "")) if effective_mapping.get("remark") else None
        remark = _safe_str(remark_value) or (default_remark or "")

        normalized_quantity = quantity * product.conversion_rate if unit_type == "purchase" else quantity

        key = (product.hb_code, expiry_date)
        exists_now = bool(Batch.query.filter_by(hb_code=product.hb_code, expiry_date=expiry_date).first())
        exists_simulated = simulated_batches.get(key, False)
        action = "merged" if (exists_now or exists_simulated) else "created"
        simulated_batches[key] = True

        used_columns = [effective_mapping.get(k) for k in effective_mapping.keys()]
        extra = build_row_extra_data(raw, used_columns=used_columns)

        rows.append(
            {
                "row_number": idx,
                "payload": {
                    "hb_code": product.hb_code,
                    "barcode": barcode or product.barcode or "",
                    "batch_no": batch_no,
                    "production_date": production_date.isoformat() if production_date else None,
                    "expiry_date": expiry_date.isoformat(),
                    "quantity": quantity,
                    "cost": cost,
                    "unit_type": unit_type,
                    "receipt_no": receipt_no or None,
                    "supplier_name": supplier_name or None,
                    "remark": remark or None,
                    "extra_data": {"import_row": idx, "row_extra": extra} if extra else {"import_row": idx},
                },
                "preview": {
                    "hb_code": product.hb_code,
                    "barcode": barcode or product.barcode,
                    "product_name": product.name,
                    "batch_no": batch_no,
                    "expiry_date": expiry_date.isoformat(),
                    "production_date": production_date.isoformat() if production_date else None,
                    "quantity": quantity,
                    "unit_type": unit_type,
                    "normalized_quantity": normalized_quantity,
                    "cost": round(cost, 4),
                    "action": action,
                    "receipt_no": receipt_no or None,
                },
            }
        )

    return {
        "columns": columns,
        "mapping_guess": guessed,
        "mapping_effective": effective_mapping,
        "total_rows": len(raw_rows),
        "valid_rows": len(rows),
        "error_rows": len(errors),
        "rows": rows,
        "preview_rows": [r["preview"] | {"row_number": r["row_number"]} for r in rows[:5]],
        "errors": errors[:10],
    }

