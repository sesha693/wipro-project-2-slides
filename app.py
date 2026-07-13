import csv
import datetime
import io
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st
from PIL import Image

from chart_builder import (
    grouped_bar_q1_q2_q2target,
    horizontal_bar_target_vs_locked_risk,
    sparkline,
    stacked_bar_people_nonpeople,
    wk_bar_chart,
)
from config import COLOR_ACCENT, COLOR_NEGATIVE, COLOR_POSITIVE, COLOR_SECONDARY
from data_reader import (
    aggregate_sheet_summary,
    detect_week_columns,
    get_adh_list,
    get_row_for_adh,
    read_workbook,
    normalize_headers,
)
from slide_builder import Card, SlideData, create_pptx
from utils.formatting import color_for_delta, format_millions, format_percent, safe_str
from utils.logging_config import clear_warnings, get_warnings


def _format_date() -> str:
    return datetime.datetime.now().strftime("%Y%m%d")


def _download_csv(warnings: list[dict]) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["sheet", "row_index", "column", "original_value", "coerced_value", "reason"])
    writer.writeheader()
    writer.writerows(warnings)
    return output.getvalue().encode("utf-8")


def _preview_slide_image(png_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(png_bytes))


def _build_revenue_slide(row: pd.Series, summary: Optional[dict] = None):
    target = row.get("q2_27_target")
    actual = row.get("q2_27")
    locked = row.get("locked_in") or 0.0
    risk = row.get("risk") or 0.0
    delta = actual - target if pd.notna(actual) and pd.notna(target) else None
    cards = [
        Card("Delta to Target", format_millions(delta) if delta is not None else "N/A", color_for_delta(delta)),
        Card("Pipeline", format_millions(row.get("pipeline")), COLOR_ACCENT),
        Card("Locked-In", format_millions(locked), COLOR_ACCENT),
        Card("Risk", format_millions(risk), COLOR_NEGATIVE),
    ]
    chart_png = horizontal_bar_target_vs_locked_risk(
        float(target or 0.0), float(locked or 0.0), float(risk or 0.0), title="Target vs Locked + Risk"
    )
    columns = ["adh", "account", "q1_27", "q2_27_target", "q2_27"]
    values = [safe_str(row.get(col)) for col in columns]
    title = f"Revenue - {safe_str(row.get('adh'))}"
    return SlideData(title=title, table_columns=columns, table_values=values, cards=cards, chart_png=chart_png)


def _build_nte_slide(row: pd.Series, summary: Optional[dict] = None):
    prev_people = row.get("prev_week_people_cost") or 0.0
    prev_non = row.get("prev_week_non_people_cost") or 0.0
    curr_people = row.get("curr_week_people_cost") or 0.0
    curr_non = row.get("curr_week_non_people_cost") or 0.0
    wow = (curr_people + curr_non) - (prev_people + prev_non)
    delta = curr_people - prev_people
    cards = [
        Card("WOW", format_millions(wow), color_for_delta(wow)),
        Card("Delta", format_millions(delta), color_for_delta(delta)),
    ]
    chart_png = stacked_bar_people_nonpeople(prev_people, prev_non, curr_people, curr_non, title="People vs Non-People")
    columns = ["actuals", "target", "people_cost", "non_people_cost", "total"]
    values = [safe_str(row.get(col)) for col in columns]
    title = f"NTE - {safe_str(row.get('adh'))}"
    return SlideData(title=title, table_columns=columns, table_values=values, cards=cards, chart_png=chart_png)


def _build_gm_slide(row: pd.Series, week_columns: list[str], summary: Optional[dict] = None):
    q1 = row.get("q1_27_actuals")
    q2_target = row.get("q2_27_target")
    wow = row.get("wow") or 0.0
    gm_forecast = row.get("gm_forecast") or 0.0
    recent_label1 = week_columns[-2] if len(week_columns) >= 2 else "wk_1"
    recent_label2 = week_columns[-1] if week_columns else "wk_2"
    week1 = row.get(recent_label1) or 0.0
    week2 = row.get(recent_label2) or 0.0
    cards = [
        Card("Delta", format_percent(row.get("delta") or 0.0), color_for_delta(row.get("delta"))),
        Card("WOW", format_percent(wow), color_for_delta(wow)),
        Card("GM Forecast", format_percent(gm_forecast), COLOR_ACCENT),
    ]
    chart_png = wk_bar_chart(float(week1 or 0.0), float(week2 or 0.0), (recent_label1, recent_label2), title="Recent P&L Weeks")
    columns = ["q1_27_actuals", "q2_27_target"] + week_columns[-2:]
    values = [safe_str(row.get(col)) for col in columns]
    title = f"GM - {safe_str(row.get('adh'))}"
    return SlideData(title=title, table_columns=columns, table_values=values, cards=cards, chart_png=chart_png)


def _build_summary_slide(sheet_name: str, summary: dict):
    if sheet_name == "revenue":
        cards = [
            Card("Target", format_millions(summary.get("total_target")), COLOR_ACCENT),
            Card("Projection", format_millions(summary.get("total_projection")), COLOR_SECONDARY),
            Card("Delta", format_millions(summary.get("total_delta")), color_for_delta(summary.get("total_delta"))),
        ]
        chart_png = horizontal_bar_target_vs_locked_risk(
            float(summary.get("total_target" or 0.0)), 0.0, float(summary.get("total_projection" or 0.0)), title="Sheet Projection vs Target"
        )
        columns = ["metric", "value"]
        values = ["Total", safe_str(summary.get("total_projection"))]
    elif sheet_name == "nte":
        cards = [
            Card("Previous Total", format_millions(summary.get("total_prev")), COLOR_ACCENT),
            Card("Current Total", format_millions(summary.get("total_curr")), COLOR_SECONDARY),
            Card("Delta", format_millions(summary.get("total_curr" - summary.get("total_prev", 0.0))), color_for_delta(summary.get("total_curr" - summary.get("total_prev", 0.0)))),
        ]
        chart_png = stacked_bar_people_nonpeople(
            float(summary.get("total_prev_people" or 0.0)),
            float(summary.get("total_prev_non" or 0.0)),
            float(summary.get("total_curr_people" or 0.0)),
            float(summary.get("total_curr_non" or 0.0)),
            title="Sheet People vs Non-People",
        )
        columns = ["metric", "value"]
        values = ["Current Total", safe_str(summary.get("total_curr"))]
    else:
        cards = [
            Card("Recent Week 1", format_millions(summary.get("recent_week_1")), COLOR_ACCENT),
            Card("Recent Week 2", format_millions(summary.get("recent_week_2")), COLOR_SECONDARY),
            Card("GM Forecast", format_percent(summary.get("gm_forecast")), COLOR_ACCENT),
        ]
        chart_png = wk_bar_chart(
            float(summary.get("recent_week_1" or 0.0)),
            float(summary.get("recent_week_2" or 0.0)),
            ("Recent 1", "Recent 2"),
            title="Sheet GM Weeks",
        )
        columns = ["metric", "value"]
        values = ["Forecast", safe_str(summary.get("gm_forecast"))]
    title = f"Summary - {sheet_name.title()}"
    return SlideData(title=title, table_columns=columns, table_values=values, cards=cards, chart_png=chart_png)


def main():
    st.set_page_config(page_title="Excel to PPTX Slide Generator", layout="wide")
    st.title("Excel Workbook to 16:9 PPTX Slide Deck")
    st.caption("Upload Revenue, NTE, and GM sheets to generate preview slides and download a PowerPoint deck.")

    clear_warnings()
    uploaded_file = st.sidebar.file_uploader("Upload .xlsx workbook", type=["xlsx"])
    mode = st.sidebar.radio("Select mode", ["ADH", "Sheet summary"])
    show_preview = st.sidebar.checkbox("Preview first 3 slides", value=True)
    positive_color = st.sidebar.color_picker("Positive delta color", COLOR_POSITIVE)
    negative_color = st.sidebar.color_picker("Negative delta color", COLOR_NEGATIVE)
    accent_color = st.sidebar.color_picker("Accent color", COLOR_ACCENT)
    sheet_selection = []
    selected_adh = None
    sheet_dfs = {}
    if uploaded_file is not None:
        with st.spinner("Reading workbook..."):
            sheet_dfs = read_workbook(uploaded_file)
        st.markdown("### Detected sheets")
        for sheet_key, df in sheet_dfs.items():
            st.write(f"**{sheet_key.title()}** - original sheet: {df._meta.get('original_sheet_name')}")
            st.dataframe(df.head(5))
        adh_options = get_adh_list(sheet_dfs)
        st.markdown("### ADH presence matrix")
        adh_matrix = []
        for adh in adh_options:
            row = {"adh": adh}
            for sheet_key, df in sheet_dfs.items():
                row[sheet_key] = "Yes" if get_row_for_adh(df, adh) is not None else "No"
            adh_matrix.append(row)
        st.table(pd.DataFrame(adh_matrix))

        if mode == "ADH":
            selected_adh = st.sidebar.selectbox("Choose ADH", adh_options)
        else:
            sheet_selection = st.sidebar.multiselect("Select sheets", list(sheet_dfs.keys()), default=list(sheet_dfs.keys()))

        if st.sidebar.button("Generate slides"):
            slide_data_list = []
            if mode == "ADH" and selected_adh:
                for sheet_key, df in sheet_dfs.items():
                    row = get_row_for_adh(df, selected_adh)
                    if row is None:
                        st.warning(f"ADH '{selected_adh}' not found in {sheet_key.title()} sheet.")
                        continue
                    if sheet_key == "revenue":
                        slide_data_list.append(_build_revenue_slide(row))
                    elif sheet_key == "nte":
                        slide_data_list.append(_build_nte_slide(row))
                    elif sheet_key == "gm":
                        week_columns = detect_week_columns(df)
                        slide_data_list.append(_build_gm_slide(row, week_columns))
            else:
                for sheet_key in sheet_selection:
                    df = sheet_dfs.get(sheet_key)
                    if df is None:
                        continue
                    summary = aggregate_sheet_summary(df, sheet_key)
                    slide_data_list.append(_build_summary_slide(sheet_key, summary))
            if not slide_data_list:
                st.error("No slides could be generated. Check sheet mapping and ADH selection.")
                return
            pptx_bytes = create_pptx(slide_data_list, filename="slides.pptx")
            file_tag = selected_adh if mode == "ADH" else "_".join(sheet_selection)
            file_name = f"slides_{file_tag}_{_format_date()}.pptx"
            st.success("PPTX deck generated successfully.")
            st.download_button("Download PPTX", pptx_bytes, file_name, "application/vnd.openxmlformats-officedocument.presentationml.presentation")
            warnings = get_warnings()
            if warnings:
                st.warning("Some values could not be coerced cleanly. Download the warning CSV for details.")
                st.download_button("Download coercion warnings", _download_csv(warnings), "coercion_warnings.csv", "text/csv")
            if show_preview:
                preview_images = []
                for slide_data in slide_data_list[:3]:
                    preview_images.append(_preview_slide_image(slide_data.chart_png))
                st.markdown("### Chart preview for first slides")
                cols = st.columns(len(preview_images))
                for col, img in zip(cols, preview_images):
                    col.image(img, use_column_width=True)


if __name__ == "__main__":
    main()
