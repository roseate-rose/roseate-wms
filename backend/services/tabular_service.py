import re
from typing import Any, Dict, List, Optional, Tuple


def read_tabular(file_stream, filename: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Read a CSV / Excel file into a list of row dicts.
    Uses pandas (already a dependency for other import/export flows).
    """

    import pandas as pd

    name = (filename or "").lower()
    if name.endswith(".xlsx") or name.endswith(".xls"):
        df = pd.read_excel(file_stream, dtype=object)
    else:
        # Pandas handles utf-8-sig and most delimiter cases well for our usage.
        df = pd.read_csv(file_stream, dtype=object, keep_default_na=False)

    df = df.fillna("")
    kept_columns: List[str] = []
    source_columns: List[str] = []
    seen_names: Dict[str, int] = {}

    for index, column in enumerate(df.columns.tolist(), start=1):
        raw_name = "" if column is None else str(column).strip()
        is_unnamed = not raw_name or raw_name.lower().startswith("unnamed:")
        series = df.iloc[:, index - 1]
        has_values = any(str(value).strip() for value in series.tolist() if value not in (None, ""))

        if is_unnamed and not has_values:
            continue

        normalized_name = raw_name or f"__unnamed_{index}"
        duplicate_count = seen_names.get(normalized_name, 0)
        seen_names[normalized_name] = duplicate_count + 1
        final_name = normalized_name if duplicate_count == 0 else f"{normalized_name}__dup{duplicate_count + 1}"

        kept_columns.append(final_name)
        source_columns.append(column)

    rows: List[Dict[str, Any]] = []
    for _, frame_row in df.iterrows():
        payload: Dict[str, Any] = {}
        for final_name, source_name in zip(kept_columns, source_columns):
            value = frame_row[source_name]
            payload[final_name] = "" if value is None else value
        rows.append(payload)

    columns = kept_columns
    return columns, rows


def _normalize_col(text: str) -> str:
    if text is None:
        return ""
    raw = str(text).strip().lower()
    raw = raw.replace("\u3000", " ")
    raw = re.sub(r"\s+", "", raw)
    raw = raw.replace("_", "").replace("-", "")
    return raw


def guess_column(columns: List[str], aliases: List[str]) -> Optional[str]:
    """
    Guess the best matching column name from `columns` given a list of alias candidates.
    Returns an actual column from `columns` or None.
    """

    if not columns:
        return None

    normalized = {_normalize_col(col): col for col in columns}
    for alias in aliases:
        key = _normalize_col(alias)
        if key in normalized:
            return normalized[key]
    return None


def build_row_extra_data(raw_row: Dict[str, Any], used_columns: List[str]) -> Dict[str, Any]:
    """
    Preserve unmapped columns for future integrations (e.g. logistics APIs).
    Only keeps non-empty values to avoid noise.
    """

    used = {c for c in used_columns if c}
    extra: Dict[str, Any] = {}
    for col, value in (raw_row or {}).items():
        if col in used:
            continue
        if value in (None, ""):
            continue
        extra[str(col)] = value
    return extra
