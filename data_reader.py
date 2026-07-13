import re
from io import BytesIO
from typing import BinaryIO, Iterable, Optional

import numpy as np
import pandas as pd
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from config import SHEET_MATCHERS, WEEK_COLUMN_REGEX
from utils.logging_config import log_coercion, logger

ADH_COLUMN_NAMES = ["adh", "accountable_delivery_head", "accountable delivery head"]


def normalize_headers(columns: Iterable[str]) -> list[str]:
    """Normalize workbook headers to snake_case and consistent tokens."""
    normalized = []
    for raw in columns:
        if raw is None:
            normalized.append("")
            continue
        header = str(raw).strip()
        header = header.replace("’", "_").replace("‘", "_").replace("'", "_")
        header = re.sub(r"[^0-9A-Za-z_]+", "_", header)
        header = re.sub(r"_+", "_", header).strip("_")
        header = header.lower()
        normalized.append(header)
    return normalized


def coerce_numeric(series: pd.Series) -> pd.Series:
    """Coerce string values to numeric, handling commas, percent signs, parentheses, N/A, and em dash."""
    results = []
    for idx, value in series.iteritems():
        original = value
        if pd.isna(value):
            results.append(np.nan)
            continue
        text = str(value).strip()
        if text == "" or text.lower() in {"n/a", "na", "—", "--", "none"}:
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
        except ValueError:
            results.append(np.nan)
            log_coercion(
                sheet=str(series.name),
                row_index=int(idx) if isinstance(idx, (int, float)) else -1,
                column=str(series.name),
                original_value=str(original),
                coerced_value="NaN",
                reason="unparsable_numeric",
            )
    return pd.to_numeric(pd.Series(results, index=series.index), errors="coerce")


def detect_week_columns(df: pd.DataFrame) -> list[str]:
    """Detect week columns using the configured regex and return sorted list by numeric suffix."""
    candidates = []
    for col in df.columns:
        match = re.search(WEEK_COLUMN_REGEX, str(col))
        if match:
            week_num = next((group for group in match.groups() if group), None)
            if week_num is not None:
                candidates.append((int(week_num), col))
    candidates.sort(key=lambda item: item[0])
    return [col for _, col in candidates]


def get_adh_list(dfs: dict[str, pd.DataFrame]) -> list[str]:
    """Return a sorted unique list of ADH names across all sheets."""
    adh_values = set()
    for df in dfs.values():
        for column in df.columns:
            if column in ADH_COLUMN_NAMES:
                adh_values.update(df[column].dropna().astype(str).str.strip().str.title())
    return sorted(adh_values)


def get_row_for_adh(df: pd.DataFrame, adh: str) -> Optional[pd.Series]:
    """Return the first row matching the ADH value, using case-insensitive and fuzzy substring fallback."""
    adh_lower = adh.lower().strip()
    if any(col in ADH_COLUMN_NAMES for col in df.columns):
        for col in df.columns:
            if col in ADH_COLUMN_NAMES:
                match_rows = df[df[col].astype(str).str.lower().str.strip() == adh_lower]
                if not match_rows.empty:
                    return match_rows.iloc[0]
                potential = df[col].astype(str).str.lower().str.strip().tolist()
                if potential:
                    best = process.extractOne(adh_lower, potential, scorer=fuzz.partial_ratio)
                    if best and best[1] >= 80:
                        return df.iloc[potential.index(best[0])]
    return None


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
        result["gm_forecast"] = numeric_df.get("q2_27_target", pd.Series(dtype=float)).mean()
        wk_cols = detect_week_columns(df)
        if wk_cols:
            result["recent_week_1"] = numeric_df.get(wk_cols[-2], pd.Series(dtype=float)).sum() if len(wk_cols) >= 2 else np.nan
            result["recent_week_2"] = numeric_df.get(wk_cols[-1], pd.Series(dtype=float)).sum()
    return result


def read_workbook(file: BinaryIO) -> dict[str, pd.DataFrame]:
    """Read an Excel workbook and return normalized DataFrames for revenue, nte, and gm sheets."""
    workbook = pd.ExcelFile(file)
    results: dict[str, pd.DataFrame] = {}
    for sheet_name in workbook.sheet_names:
        raw = workbook.parse(sheet_name, dtype=str)
        normalized_columns = normalize_headers(raw.columns)
        raw.columns = normalized_columns
        for column in raw.columns:
            if column not in ADH_COLUMN_NAMES:
                raw[column] = coerce_numeric(raw[column])
        raw._meta = {"original_sheet_name": sheet_name}
        lower_name = sheet_name.lower()
        for key, tokens in SHEET_MATCHERS.items():
            if any(token in lower_name for token in tokens):
                results[key] = raw
                break
    return results
