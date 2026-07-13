import io

import pandas as pd
from data_reader import read_workbook, get_row_for_adh, aggregate_sheet_summary
from slide_builder import create_pptx, SlideData, Card
from chart_builder import horizontal_bar_target_vs_locked_risk
from utils.formatting import format_millions, format_percent


def test_integration_full_pipeline(sample_data_path=None):
    excel_data = {
        "Revenue": {
            "ADH": ["Prachi", "Other"],
            "Account": ["Microsoft", "Google"],
            "Q1’27": [20.9, 10.0],
            "Q2’27 Target": [21, 15],
            "Q2’27": [15.6, 12.0],
            "Pipeline": [0, 2],
            "Locked-In": [0, 1],
            "Risk": [0, 0.5],
        },
        "NTE": {
            "ADH": ["Prachi", "Other"],
            "Actuals": [10, 8],
            "Target": [12, 9],
            "People Cost": [4, 3],
            "Non-People Cost": [6, 5],
            "Total": [10, 8],
            "Prev Week People Cost": [3, 2],
            "Prev Week Non-People Cost": [5, 4],
            "Curr Week People Cost": [4, 3],
            "Curr Week Non-People Cost": [6, 5],
        },
        "GM": {
            "ADH": ["Prachi", "Other"],
            "Q1’27 Actuals": [0.35, 0.30],
            "Q2’27 Target": [0.4, 0.35],
            "WK01 P&L": [0.38, 0.33],
            "WK02 P&L": [0.39, 0.34],
            "Delta": [0.01, -0.02],
            "WOW": [0.02, -0.01],
            "GM Forecast": [0.41, 0.37],
        },
    }
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, sheet_data in excel_data.items():
            pd.DataFrame(sheet_data).to_excel(writer, sheet_name=sheet_name, index=False)
    buffer.seek(0)
    dfs = read_workbook(buffer)
    assert "revenue" in dfs and "nte" in dfs and "gm" in dfs
    row = get_row_for_adh(dfs["revenue"], "Prachi")
    assert row is not None
    assert row["account"] == "Microsoft"
    summary = aggregate_sheet_summary(dfs["revenue"], "revenue")
    assert abs(summary["total_target"] - 36) < 1e-6
    slide_data = SlideData(
        title="Test",
        table_columns=["A"],
        table_values=["B"],
        cards=[Card("Delta", format_millions(1.0), "#2ECC71")],
        chart_png=horizontal_bar_target_vs_locked_risk(21.0, 0.0, 0.0, title="Test"),
    )
    result = create_pptx([slide_data], filename="integration_test.pptx")
    assert isinstance(result, (bytes, bytearray))
    assert len(result) > 2000
