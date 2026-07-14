import io
import pandas as pd

from data_reader import coerce_numeric, detect_week_columns, get_adh_list, normalize_headers, read_workbook


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


def test_adh_value_filtering_and_grouping():
    df_revenue = pd.DataFrame({"ADH": ["Vsv", "Vsv Ramesh", "ADH", "Apple", "Prachi"], "Q2’27 Target": [10, 20, 30, 40, 50]})
    dfs = {"revenue": df_revenue}
    values = get_adh_list(dfs)
    assert "Apple" not in values
    assert "Adh" not in values
    assert any(name.lower() in ["vsv", "vsv ramesh"] for name in values)


def test_read_workbook_preserves_account_column_and_filters_invalid_adh():
    excel_data = {
        "Revenue": {
            "ADH": ["Prachi", "Apple", "Other"],
            "Account": ["Microsoft", "Google", "Amazon"],
            "Q2’27 Target": [21, 15, 10],
            "Q2’27": [19, 12, 8],
        }
    }
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(excel_data["Revenue"]).to_excel(writer, sheet_name="Revenue", index=False)
    buffer.seek(0)
    dfs = read_workbook(buffer)
    assert "revenue" in dfs
    assert "account" in dfs["revenue"].columns
    assert all(val != "Apple" for val in dfs["revenue"]["adh"].astype(str).tolist())
