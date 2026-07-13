import pandas as pd

from data_reader import coerce_numeric, detect_week_columns, normalize_headers


def test_normalize_headers_variations():
    raw = ["Q1’27", "Q2’27 Target", " ADH ", "WK01 P&L"]
    expected = ["q1_27", "q2_27_target", "adh", "wk01_p_l"]
    assert normalize_headers(raw) == expected


def test_coerce_numeric_values():
    series = pd.Series(["1,234", "(1,234)", "—", "N/A", "12.3%", "na", "  5 "])
    coerced = coerce_numeric(series)
    assert coerced.iloc[0] == 1234.0
    assert coerced.iloc[1] == -1234.0
    assert pd.isna(coerced.iloc[2])
    assert pd.isna(coerced.iloc[3])
    assert coerced.iloc[4] == 12.3
    assert pd.isna(coerced.iloc[5])
    assert coerced.iloc[6] == 5.0


def test_detect_week_columns_ordered():
    df = pd.DataFrame({"WK01": [1], "wk02 P&L": [2], "WK5": [3], "other": [4]})
    assert detect_week_columns(df) == ["WK01", "wk02 P&L", "WK5"]
