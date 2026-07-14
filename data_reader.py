import re
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Iterable, Optional

import numpy as np
import pandas as pd
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from config import SHEET_MATCHERS, WEEK_COLUMN_REGEX
from utils.logging_config import log_coercion, logger

ADH_COLUMN_NAMES = ["adh"]
ADH_COLUMN_SYNONYMS = [
    "accountable_delivery_head",
    "accountable delivery head",
    "accountable_head",
    "project_owner",
    "project lead",
    "project_lead",
    "delivery_head",
    "delivery head",
    "owner",
    "lead",
    "manager",
    "responsible",
    "assigned",
]
INVALID_ADH_VALUES = {
    "total",
    "totals",
    "other",
    "others",
    "grand total",
    "summary",
    "all",
    "misc",
    "miscellaneous",
    "sub total",
    "subtotal",
    "overall",
    "unknown",
    "team",
    "team total",
    "adh",
    "account",
    "accounts",
    "customer",
    "client",
    "apple",
}

CANONICAL_HEADER_MAP = {
    "accountable_delivery_head": "adh",
    "accountable delivery head": "adh",
    "accountable_head": "adh",
    "adh": "adh",
    "account": "account",
    "client": "account",
    "customer": "account",
    "q1_27": "q1_27",
    "q1_27_actuals": "q1_27",
    "q1_27_actual": "q1_27",
    "q2_27_target": "q2_27_target",
    "q2_27_targeted": "q2_27_target",
    "q2_27": "q2_27",
    "q2_27_actual": "q2_27",
    "q2_27_actuals": "q2_27",
    "q2_27_locked_in": "locked_in",
    "q2_27_lockedin": "locked_in",
    "q2_27_locked": "locked_in",
    "q2_27_total_projections": "q2_27",
    "q2_27_total_projection": "q2_27",
    "total_projections": "q2_27",
    "projection": "q2_27",
    "q2_revenue_projections": "q2_27",
    "q2_revenue_projection": "q2_27",
    "q2_27_budget": "q2_27_target",
    "q2_27_budgeted": "q2_27_target",
    "budget": "target",
    "budgeted": "target",
    "actual": "actuals",
    "actuals": "actuals",
    "target": "target",
    "q1_gm": "q1_gm",
    "q1_gm_percent": "q1_gm",
    "q1_gm_percent_actual": "q1_gm",
    "q1_gm%": "q1_gm",
    "q2_gm_target": "q2_gm_target",
    "q2_gm_percent_target": "q2_gm_target",
    "q2_gm%_target": "q2_gm_target",
    "q2_gm_forecast": "gm_forecast",
    "q2_27_prev_week_people_cost": "prev_week_people_cost",
    "q2_27_prev_week_non_people_cost": "prev_week_non_people_cost",
    "q2_27_prev_week_total": "prev_week_total",
    "q2_27_current_week_people_cost": "curr_week_people_cost",
    "q2_27_current_week_non_people_cost": "curr_week_non_people_cost",
    "q2_27_current_week_total": "curr_week_total",
    "q2_prev_week_people_cost": "prev_week_people_cost",
    "q2_prev_week_non_people_cost": "prev_week_non_people_cost",
    "q2_prev_week_total": "prev_week_total",
    "q2_current_week_people_cost": "curr_week_people_cost",
    "q2_current_week_non_people_cost": "curr_week_non_people_cost",
    "q2_current_week_total": "curr_week_total",
    "pipeline": "pipeline",
    "locked_in": "locked_in",
    "lockedin": "locked_in",
    "risk": "risk",
    "delta": "delta",
    "delta_to_target": "delta",
    "wow": "wow",
    "gm_forecast": "gm_forecast",
    "people_cost": "people_cost",
    "people_costs": "people_cost",
    "non_people_cost": "non_people_cost",
    "nonpeople_cost": "non_people_cost",
    "total": "total",
    "prev_week_people_cost": "prev_week_people_cost",
    "prev_week_non_people_cost": "prev_week_non_people_cost",
    "curr_week_people_cost": "curr_week_people_cost",
    "curr_week_non_people_cost": "curr_week_non_people_cost",
    "prev_week_cost": "prev_week_people_cost",
    "curr_week_cost": "curr_week_people_cost",
    "wk01_p_l": "wk01_p_l",
    "wk02_p_l": "wk02_p_l",
}
TEXT_COLUMN_NAMES = {"adh", "account"}


def _normalize_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip().lower()
    text = text.replace("’", "_").replace("‘", "_").replace("'", "_")
    text = re.sub(r"[^0-9a-z]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def _is_adh_label(normalized: str) -> bool:
    if normalized == "adh":
        return True
    if normalized in ADH_COLUMN_SYNONYMS:
        return True
    if "accountable" in normalized and "head" in normalized:
        return True
    if "delivery" in normalized and "head" in normalized:
        return True
    if "project" in normalized and "lead" in normalized:
        return True
    if "adh" in normalized and len(normalized) <= 20:
        return True
    return False


def _header_context_prefix(text: object) -> Optional[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return None
    if "prev" in normalized or "previous" in normalized:
        if "week" in normalized or "q2" in normalized:
            return "prev_week"
    if "curr" in normalized or "current" in normalized:
        if "week" in normalized or "q2" in normalized:
            return "curr_week"
    if "q2" in normalized and "prev" in normalized:
        return "prev_week"
    if "q2" in normalized and ("curr" in normalized or "current" in normalized):
        return "curr_week"
    if "q2" in normalized and "week" in normalized and "prev" in normalized:
        return "prev_week"
    if "q2" in normalized and "week" in normalized and ("curr" in normalized or "current" in normalized):
        return "curr_week"
    return None


def _combine_header_rows(upper_row: pd.Series, lower_row: pd.Series) -> list[str]:
    upper = [str(value) if not pd.isna(value) else "" for value in upper_row.tolist()]
    lower = [str(value) if not pd.isna(value) else "" for value in lower_row.tolist()]
    combined = []
    prefix = None
    for parent, child in zip(upper, lower):
        child_norm = _normalize_text(child)
        parent_norm = _normalize_text(parent)
        prefix = _header_context_prefix(parent)
        if prefix and child_norm:
            if child_norm in {"people_cost", "non_people_cost", "total", "wow", "delta", "actual", "target", "risk", "pipeline", "locked_in"}:
                combined.append(f"{prefix}_{child_norm}")
                continue
            if child_norm in {"people", "non_people", "total"}:
                combined.append(f"{prefix}_{child_norm}")
                continue
        if child_norm:
            combined.append(child_norm)
        elif parent_norm:
            combined.append(parent_norm)
        else:
            combined.append("")
    return [re.sub(r"_+", "_", col).strip("_") for col in combined]


def _match_column_name(raw_label: object) -> Optional[str]:
    normalized = _normalize_text(raw_label)
    if not normalized:
        return None
    if normalized in CANONICAL_HEADER_MAP:
        return CANONICAL_HEADER_MAP[normalized]
    if _is_adh_label(normalized):
        return "adh"

    tokens = set(normalized.split("_"))
    if "account" in tokens or "client" in tokens or "customer" in tokens:
        return "account"
    if "pipeline" in tokens:
        return "pipeline"
    if "locked" in tokens and "in" in tokens:
        return "locked_in"
    if "risk" in tokens:
        return "risk"
    if "delta" in tokens and "reason" not in tokens:
        return "delta"
    if "wow" in tokens:
        return "wow"
    if "forecast" in tokens and "gm" in tokens:
        return "gm_forecast"
    if "gm" in tokens and "target" in tokens:
        return "q2_gm_target"
    if "gm" in tokens and "forecast" in tokens:
        return "gm_forecast"
    if "q1" in tokens and "gm" in tokens:
        return "q1_gm"
    if "people" in tokens and "prev" in tokens and "week" in tokens:
        return "prev_week_people_cost"
    if "non" in tokens and "prev" in tokens and "week" in tokens:
        return "prev_week_non_people_cost"
    if ("curr" in tokens or "current" in tokens) and "week" in tokens and "people" in tokens:
        return "curr_week_people_cost"
    if ("curr" in tokens or "current" in tokens) and "week" in tokens and "non" in tokens:
        return "curr_week_non_people_cost"
    if "prev" in tokens and "week" in tokens and "total" in tokens:
        return "prev_week_total"
    if ("curr" in tokens or "current" in tokens) and "week" in tokens and "total" in tokens:
        return "curr_week_total"
    if "people" in tokens and "cost" in tokens:
        return "people_cost"
    if "non" in tokens and "cost" in tokens:
        return "non_people_cost"
    if "total" in tokens:
        return "total"
    if "q1" in tokens and "27" in tokens and ("act" in tokens or "actual" in tokens):
        return "q1_27_actuals"
    if "gm" in tokens and "target" in tokens:
        return "q2_gm_target"
    if "gm" in tokens and "forecast" in tokens:
        return "gm_forecast"
    if "q1" in tokens and "gm" in tokens:
        return "q1_gm"
    if "q2" in tokens and "27" in tokens and "target" in tokens:
        return "q2_27_target"
    if "q2" in tokens and "27" in tokens and ("act" in tokens or "actual" in tokens):
        return "q2_27"
    if "actual" in tokens or "actuals" in tokens:
        return "actuals"
    if "target" in tokens and not ("q1" in tokens or "q2" in tokens or "gm" in tokens):
        return "target"
    if "q1" in tokens and "27" in tokens:
        return "q1_27"
    if re.search(r"wk\d+.*p&l|p&l.*wk\d+|wk\d+.*pl", normalized):
        return normalized
    if re.search(r"wk\d+", normalized):
        return normalized
    return None


def normalize_headers(columns: Iterable[str]) -> list[str]:
    """Normalize workbook headers to snake_case and consistent tokens."""
    return [_normalize_text(col) for col in columns]


def canonicalize_headers(columns: list[str]) -> list[str]:
    """Map normalized headers to canonical field names used by the slide generator."""
    canonical = []
    for header in columns:
        mapped = CANONICAL_HEADER_MAP.get(header)
        if mapped:
            canonical.append(mapped)
            continue
        matched = _match_column_name(header)
        if matched:
            canonical.append(matched)
            continue
        canonical.append(header)
    return canonical


def _find_header_row(excel_file: pd.ExcelFile, sheet_name: str, max_rows: int = 30) -> int:
    preview = pd.read_excel(excel_file, sheet_name=sheet_name, header=None, nrows=max_rows, dtype=str)
    best_match = (-1, None)
    for row_index, row in preview.iterrows():
        matches = 0
        non_empty = 0
        for cell in row:
            if pd.isna(cell) or str(cell).strip() == "":
                continue
            non_empty += 1
            if _match_column_name(cell) is not None:
                matches += 1
            else:
                normalized = _normalize_text(cell)
                if any(token in normalized for token in ["adh", "account", "client", "customer", "q1", "q2", "target", "actual", "pipeline", "locked", "risk", "people", "non", "gm", "wk"]):
                    matches += 0.25
        if non_empty == 0:
            continue
        score = matches + min(non_empty, 5) * 0.1
        if score > best_match[0]:
            best_match = (score, row_index)
    return best_match[1] if best_match[1] is not None else 0


def _read_workbook_bytes(file: BinaryIO) -> bytes:
    if isinstance(file, (bytes, bytearray)):
        return bytes(file)
    if hasattr(file, "read"):
        position = None
        try:
            position = file.tell()
        except Exception:
            pass
        data = file.read()
        if position is not None:
            try:
                file.seek(position)
            except Exception:
                pass
        return data
    if isinstance(file, str):
        return Path(file).read_bytes()
    raise ValueError("Unsupported workbook source")


def coerce_numeric(series: pd.Series) -> pd.Series:
    """Coerce string values to numeric and log parsing issues."""
    results = []
    values = list(series.to_numpy())
    indexes = list(series.index)
    for idx, value in zip(indexes, values):
        original = value
        if pd.isna(value):
            results.append(np.nan)
            continue
        text = str(value).strip()
        if not text or text.lower() in {"n/a", "na", "—", "--", "none", "null"}:
            results.append(np.nan)
            continue
        negative = False
        if text.startswith("(") and text.endswith(")"):
            negative = True
            text = text[1:-1].strip()
        text = text.replace(",", "").replace("%", "")
        try:
            coerced = float(text)
            if negative:
                coerced = -coerced
            results.append(coerced)
        except (ValueError, TypeError):
            results.append(np.nan)
            log_coercion(
                sheet=str(series.name or "unknown"),
                row_index=int(idx) if isinstance(idx, (int, float)) else -1,
                column=str(series.name),
                original_value=str(original),
                coerced_value="NaN",
                reason="unparsable_numeric",
            )
    return pd.to_numeric(pd.Series(results, index=series.index, name=series.name), errors="coerce")


def detect_week_columns(df: pd.DataFrame) -> list[str]:
    """Detect weekly columns by regex and return them sorted by numeric suffix."""
    candidates = []
    for col in df.columns:
        match = re.search(WEEK_COLUMN_REGEX, str(col))
        if match:
            week_num = next((group for group in match.groups() if group), None)
            if week_num is not None:
                candidates.append((int(week_num), col))
    candidates.sort(key=lambda item: item[0])
    return [col for _, col in candidates]


def _is_adh_column(col_name: str) -> bool:
    normalized = _normalize_text(col_name)
    return _is_adh_label(normalized)


def _is_valid_adh_value(value: str) -> bool:
    normalized = _normalize_text(value)
    if not normalized:
        return False
    if normalized in INVALID_ADH_VALUES:
        return False
    if any(keyword in normalized for keyword in ["total", "summary", "subtotal", "grand", "misc", "overall"]):
        return False
    if len(normalized) <= 1:
        return False
    if re.fullmatch(r"[0-9]+", normalized):
        return False
    return True


def _looks_like_name(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    normalized = _normalize_text(text)
    if not _is_valid_adh_value(normalized):
        return False
    if len(re.findall(r"[a-zA-Z]", text)) < 2:
        return False
    if re.search(r"\b(total|summary|subtotal|grand|misc|others?)\b", normalized):
        return False
    return True


def _normalize_adh_text(value: object) -> str:
    normalized = _normalize_text(value)
    return normalized


def _adh_names_similar(name_a: str, name_b: str, threshold: int = 85) -> bool:
    if not name_a or not name_b:
        return False
    a = _normalize_adh_text(name_a)
    b = _normalize_adh_text(name_b)
    if not a or not b:
        return False
    if a == b:
        return True
    if a in b or b in a:
        return True
    return fuzz.token_sort_ratio(a, b) >= threshold


def _group_similar_adh_values(values: list[str], threshold: int = 85) -> list[str]:
    groups: list[list[str]] = []
    for value in sorted(values, key=lambda v: (-len(v), v)):
        placed = False
        for group in groups:
            if _adh_names_similar(value, group[0], threshold):
                group.append(value)
                placed = True
                break
        if not placed:
            groups.append([value])
    canonical = []
    for group in groups:
        representative = max(group, key=lambda x: (len(x.split()), len(x)))
        canonical.append(representative)
    return sorted(set(canonical), key=str.casefold)


def _score_adh_column(series: pd.Series) -> float:
    values = series.dropna().astype(str).str.strip()
    if values.empty:
        return 0.0
    valid = values.apply(_looks_like_name)
    proportion = valid.sum() / len(values)
    if proportion < 0.3:
        return 0.0
    distinct = values.nunique()
    return proportion + min(distinct / 20.0, 0.5)


def _find_best_adh_column(df: pd.DataFrame) -> Optional[str]:
    best_col, best_score = None, 0.0
    for col in df.columns:
        normalized = _normalize_text(col)
        if normalized in CANONICAL_HEADER_MAP and CANONICAL_HEADER_MAP[normalized] == "adh":
            return col
        if _is_adh_label(normalized):
            return col
        score = _score_adh_column(df[col])
        if score > best_score:
            best_col, best_score = col, score
    return best_col if best_score >= 0.45 else None


def _is_week_detail_column(column_name: str) -> bool:
    normalized = _normalize_text(column_name)
    return bool(re.search(WEEK_COLUMN_REGEX, normalized)) or bool(re.search(r"^wk\d+.*p_l$", normalized))


def _filter_sheet_columns(sheet_type: str, df: pd.DataFrame) -> pd.DataFrame:
    allowed = {
        "revenue": {
            "adh",
            "account",
            "q1_27",
            "q2_27_target",
            "q2_27",
            "locked_in",
            "risk",
            "pipeline",
            "wow",
            "delta",
            "q2_27_total_projections",
            "q2_27_total_projection",
        },
        "nte": {
            "adh",
            "actuals",
            "target",
            "people_cost",
            "non_people_cost",
            "total",
            "wow",
            "delta",
            "prev_week_people_cost",
            "prev_week_non_people_cost",
            "curr_week_people_cost",
            "curr_week_non_people_cost",
            "prev_week_total",
            "curr_week_total",
        },
        "gm": {
            "adh",
            "account",
            "q1_gm",
            "q2_gm_target",
            "gm_forecast",
            "wow",
            "delta",
        },
    }.get(sheet_type, set(df.columns.tolist()))
    columns = [
        col
        for col in df.columns
        if col in allowed or (sheet_type == "gm" and _is_week_detail_column(col))
    ]
    return df.loc[:, columns]


def get_adh_list(dfs: dict[str, pd.DataFrame]) -> list[str]:
    """Return a sorted unique list of ADH names across all sheets."""
    all_values = []
    for df in dfs.values():
        adh_columns = [col for col in df.columns if _is_adh_column(col)]
        for col in adh_columns:
            values = df[col].dropna().astype(str).str.strip().str.title()
            all_values.extend(value for value in values if _is_valid_adh_value(value))
    return _group_similar_adh_values(sorted(set(all_values)))


def get_row_for_adh(df: pd.DataFrame, adh: str) -> Optional[pd.Series]:
    """Return the first row matching the ADH value with case-insensitive and fuzzy substring fallback."""
    adh_norm = _normalize_adh_text(adh)
    adh_columns = [col for col in df.columns if _is_adh_column(col)]
    for col in adh_columns:
        raw_values = df[col].astype(str).str.strip()
        normalized_values = raw_values.apply(_normalize_adh_text)
        exact_matches = normalized_values == adh_norm
        if exact_matches.any():
            return df.loc[exact_matches].iloc[0]
        for index, candidate in enumerate(raw_values.tolist()):
            if _adh_names_similar(candidate, adh, threshold=85):
                return df.iloc[index]
    return None


def get_sheet_adh_values(dfs: dict[str, pd.DataFrame]) -> dict[str, list[str]]:
    """Return sorted unique ADH names for each sheet independently."""
    result: dict[str, list[str]] = {}
    for sheet_name, df in dfs.items():
        adh_columns = [col for col in df.columns if _is_adh_column(col)]
        values = set()
        for col in adh_columns:
            values.update(
                df[col]
                .dropna()
                .astype(str)
                .str.strip()
                .loc[lambda x: x.apply(lambda v: _is_valid_adh_value(str(v).strip()))]
                .str.title()
                .tolist()
            )
        result[sheet_name] = _group_similar_adh_values(sorted(values))
    return result


def find_similar_adh_names(dfs: dict[str, pd.DataFrame], threshold: int = 85) -> list[dict]:
    """Return likely similar ADH name pairs across sheets."""
    sheet_adh_values = get_sheet_adh_values(dfs)
    pairs = []
    sheet_names = list(sheet_adh_values.keys())
    for i, sheet_a in enumerate(sheet_names):
        for sheet_b in sheet_names[i + 1 :]:
            for adh_a in sheet_adh_values[sheet_a]:
                matches = process.extract(adh_a, sheet_adh_values[sheet_b], scorer=fuzz.token_sort_ratio)
                for matched_name, score in matches:
                    if score >= threshold and matched_name.lower() != adh_a.lower():
                        pairs.append(
                            {
                                "sheet_a": sheet_a,
                                "adh_a": adh_a,
                                "sheet_b": sheet_b,
                                "adh_b": matched_name,
                                "score": score,
                            }
                        )
    return sorted(pairs, key=lambda item: (-item["score"], item["sheet_a"], item["adh_a"]))


def aggregate_sheet_summary(df: pd.DataFrame, sheet_name: str) -> dict:
    """Return aggregated totals and metrics for summary slide generation."""
    result = {}
    numeric_df = df.select_dtypes(include=["number"]).fillna(0)
    if sheet_name == "revenue":
        result["total_target"] = numeric_df.get("q2_27_target", pd.Series(dtype=float)).sum()
        result["total_projection"] = numeric_df.get("q2_27", pd.Series(dtype=float)).sum()
        result["total_delta"] = result["total_projection"] - result["total_target"]
    elif sheet_name == "nte":
        prev_people = numeric_df.get("prev_week_people_cost", pd.Series(dtype=float)).sum()
        prev_non = numeric_df.get("prev_week_non_people_cost", pd.Series(dtype=float)).sum()
        curr_people = numeric_df.get("curr_week_people_cost", pd.Series(dtype=float)).sum()
        curr_non = numeric_df.get("curr_week_non_people_cost", pd.Series(dtype=float)).sum()
        result.update(
            total_prev_people=prev_people,
            total_prev_non=prev_non,
            total_curr_people=curr_people,
            total_curr_non=curr_non,
            total_prev=prev_people + prev_non,
            total_curr=curr_people + curr_non,
        )
    elif sheet_name == "gm":
        result["gm_forecast"] = numeric_df.get("gm_forecast", pd.Series(dtype=float)).mean()
        wk_cols = detect_week_columns(df)
        if wk_cols:
            result["recent_week_1"] = numeric_df.get(wk_cols[-2], pd.Series(dtype=float)).sum() if len(wk_cols) >= 2 else np.nan
            result["recent_week_2"] = numeric_df.get(wk_cols[-1], pd.Series(dtype=float)).sum()
    return result


def infer_sheet_type(sheet_name: str, headers: list[str]) -> Optional[str]:
    """Infer whether a sheet contains revenue, nte, or gm data."""
    normalized_name = _normalize_text(sheet_name)
    for key, tokens in SHEET_MATCHERS.items():
        if any(token in normalized_name for token in tokens):
            return key
    header_text = " ".join([_normalize_text(h) for h in headers])
    if any(token in header_text for token in ["q1_27", "q2_27_target", "q2_27_total_projections", "q2_27_locked_in", "locked_in", "pipeline", "risk", "delta_to_target"]):
        return "revenue"
    if any(token in header_text for token in ["prev_week_people_cost", "curr_week_people_cost", "prev_week_non_people_cost", "curr_week_non_people_cost", "prev_week_total", "curr_week_total", "wow", "delta"]):
        return "nte"
    if any(token in header_text for token in ["q1_gm", "q2_gm_target", "gm_forecast", "wk", "pl"]):
        return "gm"
    if any(token in normalized_name for token in ["gm", "gross", "margin"]):
        return "gm"
    return None


def _header_row_looks_like_labels(row: pd.Series) -> bool:
    non_blank = 0
    label_count = 0
    for cell in row:
        if pd.isna(cell) or str(cell).strip() == "":
            continue
        non_blank += 1
        normalized = _normalize_text(cell)
        if _match_column_name(cell) is not None or any(token in normalized for token in ["adh", "account", "client", "customer", "q1", "q2", "gm", "target", "actual", "people", "non", "week", "cost", "p&l", "pl", "wow", "delta"]):
            label_count += 1
    return non_blank > 0 and label_count / non_blank >= 0.4


def _read_sheet_with_combined_headers(workbook_bytes: bytes, sheet_name: str, header_row: int) -> pd.DataFrame:
    raw_preview = pd.read_excel(BytesIO(workbook_bytes), sheet_name=sheet_name, header=None, nrows=header_row + 2, dtype=str)
    if header_row + 1 < len(raw_preview):
        first_header = raw_preview.iloc[header_row]
        second_header = raw_preview.iloc[header_row + 1]
        if _header_row_looks_like_labels(second_header):
            combined_columns = _combine_header_rows(first_header, second_header)
            data = pd.read_excel(BytesIO(workbook_bytes), sheet_name=sheet_name, header=None, skiprows=header_row + 2, dtype=str)
            data.columns = combined_columns[: len(data.columns)]
            return data
    return pd.read_excel(BytesIO(workbook_bytes), sheet_name=sheet_name, header=header_row, dtype=str)


def read_workbook(file: BinaryIO) -> dict[str, pd.DataFrame]:
    """Read an Excel workbook and return normalized DataFrames for revenue, nte, and gm sheets."""
    workbook_bytes = _read_workbook_bytes(file)
    xls = pd.ExcelFile(BytesIO(workbook_bytes))
    results: dict[str, pd.DataFrame] = {}
    for sheet_name in xls.sheet_names:
        header_row = _find_header_row(xls, sheet_name)
        if header_row is None:
            header_row = 0
        sheet_df = _read_sheet_with_combined_headers(workbook_bytes, sheet_name, header_row)
        normalized_columns = normalize_headers(sheet_df.columns.tolist())
        canonical_columns = canonicalize_headers(normalized_columns)
        rename_map = {orig: canonical for orig, canonical in zip(sheet_df.columns.tolist(), canonical_columns)}
        sheet_df = sheet_df.rename(columns=rename_map)
        sheet_df = sheet_df.loc[:, ~sheet_df.columns.duplicated()]
        if not any(col == "adh" for col in sheet_df.columns):
            adh_columns = [col for col in sheet_df.columns if _is_adh_column(col)]
            if not adh_columns:
                best_adh = _find_best_adh_column(sheet_df)
                if best_adh:
                    adh_columns = [best_adh]
            if adh_columns:
                for col in adh_columns:
                    sheet_df = sheet_df.rename(columns={col: "adh"})
                sheet_df = sheet_df.loc[:, ~sheet_df.columns.duplicated()]

        for column in sheet_df.columns:
            if column in TEXT_COLUMN_NAMES:
                continue
            sheet_df[column] = coerce_numeric(sheet_df[column])
        if "adh" in sheet_df.columns:
            valid_mask = sheet_df["adh"].astype(str).str.strip().apply(_is_valid_adh_value)
            if valid_mask.any():
                sheet_df = sheet_df.loc[valid_mask]
        sheet_df.attrs["original_sheet_name"] = sheet_name
        sheet_df.attrs["header_row"] = header_row
        sheet_type = infer_sheet_type(sheet_name, sheet_df.columns.tolist())
        if sheet_type:
            sheet_df = _filter_sheet_columns(sheet_type, sheet_df)
            results[sheet_type] = sheet_df
        else:
            logger.warning("Unable to infer sheet type for '%s' with columns %s", sheet_name, sheet_df.columns.tolist())
    return results
