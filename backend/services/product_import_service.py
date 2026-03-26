import json
from typing import Any, Dict, List, Optional, Tuple

from backend.services.tabular_service import guess_column, read_tabular


REQUIRED_COLUMNS = {"hb_code", "name", "spec"}
PRODUCT_IMPORT_ALIASES = {
    "hb_code": ["hb_code", "HB编码", "商品编码", "货号", "内部编码"],
    "barcode": ["barcode", "条码", "国际条码"],
    "name": ["name", "商品名称", "名称"],
    "spec": ["spec", "规格", "规格型号"],
    "unit": ["unit", "单位", "计量单位", "measure_unit"],
    "base_unit": ["base_unit", "最小单位", "最小售卖单位", "基本单位"],
    "purchase_unit": ["purchase_unit", "采购单位", "进货单位"],
    "conversion_rate": ["conversion_rate", "换算率", "换算比例", "装箱数"],
    "extra_data": ["extra_data", "extra_data(JSON)", "扩展字段", "扩展字段(JSON)", "额外信息", "附加信息"],
}


def _safe_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _parse_extra_data(value) -> Dict[str, Any]:
    if value in (None, ""):
        return {}
    if isinstance(value, dict):
        return value
    raw = str(value).strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {"_raw": parsed}
    except json.JSONDecodeError:
        pass

    # Tolerate common CSV/Excel escaping patterns.
    candidates = []
    if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
        candidates.append(raw[1:-1].strip())
    candidates.append(raw.replace('""', '"'))
    candidates.append(raw.replace('\\"', '"'))

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else {"_raw": parsed}
        except json.JSONDecodeError:
            continue

    return {"_raw": raw}


def resolve_product_import_mapping(columns: List[str]) -> Dict[str, Optional[str]]:
    return {field: guess_column(columns, aliases) for field, aliases in PRODUCT_IMPORT_ALIASES.items()}


def canonicalize_product_row(
    raw: Dict[str, Any],
    *,
    column_mapping: Dict[str, Optional[str]],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for field in PRODUCT_IMPORT_ALIASES.keys():
        source_col = column_mapping.get(field)
        payload[field] = raw.get(source_col, "") if source_col else ""
    return payload


def normalize_product_row(row: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    hb_code = _safe_str(row.get("hb_code"))
    name = _safe_str(row.get("name"))
    spec = _safe_str(row.get("spec"))

    if not hb_code:
        return None, "hb_code is required"
    if not name:
        return None, "name is required"
    if not spec:
        return None, "spec is required"

    barcode = _safe_str(row.get("barcode")) or None
    unit = _safe_str(row.get("unit")) or _safe_str(row.get("measure_unit")) or ""
    base_unit = _safe_str(row.get("base_unit")) or unit or ""
    purchase_unit = _safe_str(row.get("purchase_unit")) or base_unit or ""
    conversion_rate = _safe_int(row.get("conversion_rate"), default=1)
    if conversion_rate <= 0:
        conversion_rate = 1

    extra_data = _parse_extra_data(row.get("extra_data"))

    return (
        {
            "hb_code": hb_code,
            "barcode": barcode,
            "name": name,
            "spec": spec,
            "unit": unit or base_unit,
            "base_unit": base_unit or "件",
            "purchase_unit": purchase_unit or (base_unit or "件"),
            "conversion_rate": conversion_rate,
            "extra_data": extra_data,
        },
        None,
    )


def import_products_from_file(
    *,
    file_stream,
    filename: str,
    mode: str = "skip",
    commit: bool = False,
    product_model=None,
    db=None,
) -> Dict[str, Any]:
    """
    mode:
      - skip: existing hb_code rows are ignored
      - overwrite: existing hb_code rows are updated
    """
    if mode not in {"skip", "overwrite"}:
        raise ValueError("mode must be one of: skip, overwrite")

    columns, raw_rows = read_tabular(file_stream, filename=filename)
    column_mapping = resolve_product_import_mapping(columns)
    normalized_rows = []
    errors = []

    missing = [field for field in REQUIRED_COLUMNS if not column_mapping.get(field)]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")

    # Detect duplicates within the import file itself: barcode must map to a single hb_code.
    barcode_to_hb = {}

    for idx, raw in enumerate(raw_rows, start=1):
        canonical_row = canonicalize_product_row(raw, column_mapping=column_mapping)
        payload, err = normalize_product_row(canonical_row)
        if err:
            errors.append({"row_number": idx, "error": err, "raw": raw})
            continue

        barcode = payload.get("barcode")
        if barcode:
            existing_hb = barcode_to_hb.get(barcode)
            if existing_hb and existing_hb != payload["hb_code"]:
                errors.append(
                    {
                        "row_number": idx,
                        "error": "barcode collides with another hb_code in the same file",
                        "raw": raw,
                    }
                )
                continue
            barcode_to_hb[barcode] = payload["hb_code"]

        # Detect collisions with existing DB (when model is available).
        if product_model is not None and barcode:
            existing_by_barcode = product_model.query.filter_by(barcode=barcode).first()
            if existing_by_barcode and existing_by_barcode.hb_code != payload["hb_code"]:
                errors.append(
                    {
                        "row_number": idx,
                        "error": "barcode already exists for another hb_code",
                        "raw": raw,
                    }
                )
                continue

        normalized_rows.append(payload)

    preview_rows = [
        {
            "row_number": i + 1,
            "hb_code": r["hb_code"],
            "barcode": r["barcode"],
            "name": r["name"],
            "spec": r["spec"],
            "unit": r["unit"],
            "base_unit": r["base_unit"],
            "purchase_unit": r["purchase_unit"],
            "conversion_rate": r["conversion_rate"],
            "extra_data": r["extra_data"],
        }
        for i, r in enumerate(normalized_rows[:5])
    ]

    result = {
        "mode": mode,
        "columns": columns,
        "total_rows": len(raw_rows),
        "valid_rows": len(normalized_rows),
        "error_rows": len(errors),
        "column_mapping": column_mapping,
        "preview_rows": preview_rows,
        "errors": errors[:10],
    }

    if not commit:
        return result

    if product_model is None or db is None:
        raise ValueError("product_model and db are required when commit=True")

    created = 0
    updated = 0
    skipped = 0
    imported = []

    for row in normalized_rows:
        existing = product_model.query.filter_by(hb_code=row["hb_code"]).first()
        if existing:
            if mode == "skip":
                skipped += 1
                continue

            # Avoid barcode collisions during overwrite.
            if row.get("barcode"):
                other = product_model.query.filter_by(barcode=row["barcode"]).first()
                if other and other.hb_code != existing.hb_code:
                    errors.append(
                        {
                            "row_number": None,
                            "error": f"barcode {row['barcode']} already exists for another hb_code",
                            "raw": {"hb_code": row["hb_code"], "barcode": row["barcode"]},
                        }
                    )
                    continue

            existing.barcode = row["barcode"]
            existing.name = row["name"]
            existing.spec = row["spec"]
            existing.unit = row["unit"]
            existing.base_unit = row["base_unit"]
            existing.purchase_unit = row["purchase_unit"]
            existing.conversion_rate = row["conversion_rate"]
            existing.set_extra_data(row["extra_data"])
            updated += 1
            imported.append(existing.to_dict(include_stock=True))
            continue

        if row.get("barcode"):
            other = product_model.query.filter_by(barcode=row["barcode"]).first()
            if other:
                errors.append(
                    {
                        "row_number": None,
                        "error": f"barcode {row['barcode']} already exists for another hb_code",
                        "raw": {"hb_code": row["hb_code"], "barcode": row["barcode"]},
                    }
                )
                continue

        product = product_model(
            hb_code=row["hb_code"],
            barcode=row["barcode"],
            name=row["name"],
            spec=row["spec"],
            unit=row["unit"],
            base_unit=row["base_unit"],
            purchase_unit=row["purchase_unit"],
            conversion_rate=row["conversion_rate"],
        )
        product.set_extra_data(row["extra_data"])
        db.session.add(product)
        created += 1
        imported.append(product.to_dict(include_stock=True))

    db.session.commit()

    result.update(
        {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "imported_rows": imported[:50],
            "error_rows": len(errors),
            "errors": errors[:10],
        }
    )
    return result
