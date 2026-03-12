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
        df = pd.read_excel(file_stream)
    else:
        # Pandas handles utf-8-sig and most delimiter cases well for our usage.
        df = pd.read_csv(file_stream)

    df = df.fillna("")
    columns = [str(c).strip() for c in df.columns.tolist()]
    rows = df.to_dict(orient="records")
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

