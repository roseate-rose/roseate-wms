from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.models import ChannelMapping, Product
from backend.services.tabular_service import build_row_extra_data, guess_column, read_tabular


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


def guess_order_mapping(columns: List[str]) -> Dict[str, Optional[str]]:
    return {
        "channel_name": guess_column(columns, ["channel_name", "渠道", "平台", "店铺"]),
        "external_sku_id": guess_column(
            columns,
            [
                "external_sku_id",
                "外部skuid",
                "外部sku",
                "sku",
                "skuid",
                "商家编码",
                "商品编码",
                "货号",
                "商品id",
            ],
        ),
        "quantity": guess_column(columns, ["quantity", "数量", "件数", "购买数量", "商品数量"]),
        "external_order_no": guess_column(columns, ["external_order_no", "订单号", "外部订单号", "平台订单号"]),
    }


def build_order_rows_from_file(
    *,
    file_stream,
    filename: str,
    mapping: Optional[Dict[str, str]] = None,
    default_channel_name: str = "",
    template_name: str = "generic",
) -> Dict[str, Any]:
    """
    Parse an orders import file into normalized row payloads (no DB writes).

    Required: external_sku_id, quantity
    Optional: channel_name (fallback to default_channel_name), external_order_no.
    Unmapped columns are preserved to `extra_data` for future logistics API integration.
    """

    columns, raw_rows = read_tabular(file_stream, filename=filename)
    guessed = guess_order_mapping(columns)

    effective_mapping: Dict[str, str] = {}
    for key, col in (mapping or {}).items():
        if col:
            effective_mapping[key] = col
    for key, col in guessed.items():
        if key not in effective_mapping and col:
            effective_mapping[key] = col

    rows: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    # Rough preview simulation: subtract requested quantities from product-level sellable stock.
    remaining_sellable: Dict[str, int] = {}

    for idx, raw in enumerate(raw_rows, start=1):
        channel_value = raw.get(effective_mapping.get("channel_name", "")) if effective_mapping.get("channel_name") else None
        channel_name = _safe_str(channel_value) or (default_channel_name or "").strip()
        if not channel_name:
            errors.append({"row_number": idx, "error": "channel_name is required (or provide default_channel_name)", "raw": raw})
            continue

        sku_value = raw.get(effective_mapping.get("external_sku_id", "")) if effective_mapping.get("external_sku_id") else None
        external_sku_id = _safe_str(sku_value)
        if not external_sku_id:
            errors.append({"row_number": idx, "error": "external_sku_id is required", "raw": raw})
            continue

        qty_value = raw.get(effective_mapping.get("quantity", "")) if effective_mapping.get("quantity") else None
        quantity = _safe_int(qty_value)
        if not quantity or quantity <= 0:
            errors.append({"row_number": idx, "error": "quantity must be a positive integer", "raw": raw})
            continue

        mapping_row = ChannelMapping.query.filter_by(channel_name=channel_name, external_sku_id=external_sku_id).first()
        if not mapping_row:
            errors.append({"row_number": idx, "error": "channel mapping not found", "raw": raw})
            continue

        product = Product.query.filter_by(hb_code=mapping_row.hb_code).first()
        if not product:
            errors.append({"row_number": idx, "error": "product not found", "raw": raw})
            continue

        order_no_value = raw.get(effective_mapping.get("external_order_no", "")) if effective_mapping.get("external_order_no") else None
        external_order_no = _safe_str(order_no_value) or None

        if product.hb_code not in remaining_sellable:
            remaining_sellable[product.hb_code] = product.sellable_stock
        remaining_sellable[product.hb_code] -= quantity
        predicted_status = "ok" if remaining_sellable[product.hb_code] >= 0 else "insufficient_stock"

        used_columns = [effective_mapping.get(k) for k in effective_mapping.keys()]
        extra = build_row_extra_data(raw, used_columns=used_columns)
        extra_payload = {"source": "import", "template": template_name}
        if external_order_no:
            extra_payload["external_order_no"] = external_order_no
        if extra:
            extra_payload["row_extra"] = extra

        rows.append(
            {
                "row_number": idx,
                "payload": {
                    "channel_name": channel_name,
                    "external_sku_id": external_sku_id,
                    "quantity": quantity,
                    "extra_data": extra_payload,
                },
                "preview": {
                    "channel_name": channel_name,
                    "external_sku_id": external_sku_id,
                    "hb_code": product.hb_code,
                    "product_name": product.name,
                    "quantity": quantity,
                    "sellable_stock": product.sellable_stock,
                    "predicted_status": predicted_status,
                    "external_order_no": external_order_no,
                },
            }
        )

    return {
        "columns": columns,
        "mapping_guess": guessed,
        "mapping_effective": effective_mapping,
        "template": template_name,
        "total_rows": len(raw_rows),
        "valid_rows": len(rows),
        "error_rows": len(errors),
        "rows": rows,
        "preview_rows": [r["preview"] | {"row_number": r["row_number"]} for r in rows[:5]],
        "errors": errors[:10],
    }

