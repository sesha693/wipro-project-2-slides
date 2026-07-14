import csv
import datetime
import io
from pathlib import Path
from typing import Optional

import data_reader
import pandas as pd
import streamlit as st
from PIL import Image

from chart_builder import (
    grouped_bar_q1_q2_q2target,
    horizontal_bar_target_vs_locked_risk,
    sparkline,
    stacked_bar_people_nonpeople,
    summary_gm_chart,
    summary_nte_chart,
    summary_revenue_chart,
    wk_bar_chart,
)
from config import COLOR_ACCENT, COLOR_NEGATIVE, COLOR_POSITIVE, COLOR_SECONDARY
from data_reader import (
    aggregate_sheet_summary,
    detect_week_columns,
    find_similar_adh_names,
    get_row_for_adh,
    get_sheet_adh_values,
    get_adh_list,
    read_workbook,
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


def _resolve_field(row: pd.Series, *fields: str):
    for field in fields:
        if field in row and pd.notna(row.get(field)):
            return row.get(field)
    return None


def _format_slide_value(column: str, value):
    if value is None or pd.isna(value):
        return "N/A"
    column = column.lower()
    if column in {"adh", "account"}:
        return safe_str(value)
    if "gm" in column or column.startswith("wk") or column.endswith("_p_l") or column == "gm_forecast":
        return format_percent(value)
    return format_millions(value)


def _build_revenue_slide(row: pd.Series, summary: Optional[dict] = None):
    target = _resolve_field(row, "q2_27_target", "target")
    actual = _resolve_field(row, "q2_27", "q2_27_actual", "q2_27_actuals")
    locked = _resolve_field(row, "locked_in") or 0.0
    risk = _resolve_field(row, "risk") or 0.0
    delta = actual - target if pd.notna(actual) and pd.notna(target) else None
    cards = [
        Card("Delta to Target", format_millions(delta) if delta is not None else "N/A", color_for_delta(delta)),
        Card("Pipeline", format_millions(_resolve_field(row, "pipeline") or 0.0), COLOR_ACCENT),
        Card("Locked-In", format_millions(locked), COLOR_ACCENT),
        Card("Risk", format_millions(risk), COLOR_NEGATIVE),
    ]
    chart_png = horizontal_bar_target_vs_locked_risk(
        float(target or 0.0), float(locked or 0.0), float(risk or 0.0), title="Target vs Locked + Risk"
    )
    columns = ["adh", "account", "q1_27", "q2_27_target", "q2_27"]
    values = [
        safe_str(row.get("adh")),
        safe_str(row.get("account")),
        format_millions(_resolve_field(row, "q1_27", "q1_27_actual", "q1_27_actuals")) if pd.notna(_resolve_field(row, "q1_27", "q1_27_actual", "q1_27_actuals")) else "N/A",
        format_millions(target) if pd.notna(target) else "N/A",
        format_millions(actual) if pd.notna(actual) else "N/A",
    ]
    callouts = [
        f"Delta to target is {format_millions(delta)}." if delta is not None else "Delta to target is not available.",
        f"Locked-in coverage is {format_millions(locked)} with risk at {format_millions(risk)}.",
    ]
    title = f"Revenue - {safe_str(row.get('adh'))}"
    return SlideData(
        title=title,
        table_columns=columns,
        table_values=values,
        cards=cards,
        chart_png=chart_png,
        table_title="Revenue View",
        chart_title="Revenue Movement Matrix",
        callouts=callouts,
    )


def _build_nte_slide(row: pd.Series, summary: Optional[dict] = None):
    actuals = _resolve_field(row, "actuals", "q2_27", "q2_27_actuals")
    target = _resolve_field(row, "target", "q2_27_target")
    prev_people = _resolve_field(row, "prev_week_people_cost", "people_cost") or 0.0
    prev_non = _resolve_field(row, "prev_week_non_people_cost", "non_people_cost") or 0.0
    curr_people = _resolve_field(row, "curr_week_people_cost", "people_cost") or 0.0
    curr_non = _resolve_field(row, "curr_week_non_people_cost", "non_people_cost") or 0.0
    prev_total = _resolve_field(row, "prev_week_total") if pd.notna(_resolve_field(row, "prev_week_total")) else prev_people + prev_non
    curr_total = _resolve_field(row, "curr_week_total") if pd.notna(_resolve_field(row, "curr_week_total")) else curr_people + curr_non
    wow = float(curr_total or 0.0) - float(prev_total or 0.0)
    delta = float(actuals or 0.0) - float(target or 0.0)
    cards = [
        Card("WOW", format_millions(wow), color_for_delta(wow)),
        Card("Delta", format_millions(delta), color_for_delta(delta)),
    ]
    chart_png = stacked_bar_people_nonpeople(
        _resolve_field(row, "prev_week_people_cost", "people_cost") or 0.0,
        _resolve_field(row, "prev_week_non_people_cost", "non_people_cost") or 0.0,
        _resolve_field(row, "curr_week_people_cost", "people_cost") or 0.0,
        _resolve_field(row, "curr_week_non_people_cost", "non_people_cost") or 0.0,
        title="People vs Non-People",
    )
    columns = ["actuals", "target", "people_cost", "non_people_cost", "prev_week_total", "curr_week_total"]
    values = [
        format_millions(actuals) if pd.notna(actuals) else "N/A",
        format_millions(target) if pd.notna(target) else "N/A",
        format_millions(_resolve_field(row, "people_cost", "prev_week_people_cost", "curr_week_people_cost")) if pd.notna(_resolve_field(row, "people_cost", "prev_week_people_cost", "curr_week_people_cost")) else "N/A",
        format_millions(_resolve_field(row, "non_people_cost", "prev_week_non_people_cost", "curr_week_non_people_cost")) if pd.notna(_resolve_field(row, "non_people_cost", "prev_week_non_people_cost", "curr_week_non_people_cost")) else "N/A",
        format_millions(prev_total) if pd.notna(prev_total) else "N/A",
        format_millions(curr_total) if pd.notna(curr_total) else "N/A",
    ]
    callouts = [
        f"Week-over-week movement is {format_millions(wow)}.",
        f"Target gap is {format_millions(delta)}.",
    ]
    title = f"NTE - {safe_str(row.get('adh'))}"
    return SlideData(
        title=title,
        table_columns=columns,
        table_values=values,
        cards=cards,
        chart_png=chart_png,
        table_title="NTE View",
        chart_title="NTE Movement Matrix",
        callouts=callouts,
    )


def _build_gm_slide(row: pd.Series, week_columns: list[str], summary: Optional[dict] = None):
    q1 = _resolve_field(row, "q1_gm", "q1_27")
    q2_target = _resolve_field(row, "q2_gm_target", "q2_27_target")
    wow = _resolve_field(row, "wow") or 0.0
    gm_forecast = _resolve_field(row, "gm_forecast") or 0.0
    if len(week_columns) >= 2:
        recent_label1 = week_columns[-2]
        recent_label2 = week_columns[-1]
    elif len(week_columns) == 1:
        recent_label1 = week_columns[0]
        recent_label2 = week_columns[0]
    else:
        recent_label1 = "wk_1"
        recent_label2 = "wk_2"
    week1 = _resolve_field(row, recent_label1) or 0.0
    week2 = _resolve_field(row, recent_label2) or 0.0
    cards = [
        Card("Delta", format_percent(_resolve_field(row, "delta") or 0.0), color_for_delta(_resolve_field(row, "delta") or 0.0)),
        Card("WOW", format_percent(wow), color_for_delta(wow)),
        Card("GM Forecast", format_percent(gm_forecast), COLOR_ACCENT),
    ]
    chart_png = wk_bar_chart(float(week1 or 0.0), float(week2 or 0.0), (recent_label1, recent_label2), title="Recent P&L Weeks", percent=True)
    columns = ["q1_gm", "q2_gm_target", recent_label1, recent_label2]
    values = [
        format_percent(q1) if pd.notna(q1) else "N/A",
        format_percent(q2_target) if pd.notna(q2_target) else "N/A",
        format_percent(week1),
        format_percent(week2),
    ]
    callouts = [
        f"{recent_label2} is {format_percent(week2)} compared to {recent_label1} at {format_percent(week1)}.",
        f"Forecast margin is {format_percent(gm_forecast)}.",
    ]
    title = f"GM - {safe_str(row.get('adh'))}"
    return SlideData(
        title=title,
        table_columns=columns,
        table_values=values,
        cards=cards,
        chart_png=chart_png,
        table_title="GM View",
        chart_title="GM Movement Matrix",
        callouts=callouts,
    )


def _build_summary_slide(sheet_name: str, summary: dict):
    if sheet_name == "revenue":
        total_target = float(summary.get("total_target", 0.0) or 0.0)
        total_projection = float(summary.get("total_projection", 0.0) or 0.0)
        delta = total_projection - total_target
        cards = [
            Card("Total Target", format_millions(total_target), COLOR_ACCENT),
            Card("Total Projection", format_millions(total_projection), COLOR_SECONDARY),
            Card("Delta", format_millions(delta), color_for_delta(delta)),
        ]
        chart_png = summary_revenue_chart(total_target, total_projection, title="Revenue Target vs Projection")
        columns = ["metric", "value"]
        values = ["Projection", format_millions(total_projection)]
        callouts = [
            f"Projection is {format_millions(total_projection)} versus target {format_millions(total_target)}.",
            f"Delta is {format_millions(delta)}.",
        ]
        table_title = "Revenue Summary"
        chart_title = "Revenue Projection Matrix"
    elif sheet_name == "nte":
        total_prev = float(summary.get("total_prev", 0.0) or 0.0)
        total_curr = float(summary.get("total_curr", 0.0) or 0.0)
        delta_total = total_curr - total_prev
        cards = [
            Card("Previous Total", format_millions(total_prev), COLOR_ACCENT),
            Card("Current Total", format_millions(total_curr), COLOR_SECONDARY),
            Card("Delta", format_millions(delta_total), color_for_delta(delta_total)),
        ]
        chart_png = summary_nte_chart(total_prev, total_curr, title="NTE Previous vs Current")
        columns = ["metric", "value"]
        values = ["Current Total", format_millions(total_curr)]
        callouts = [
            f"Current total increased to {format_millions(total_curr)}.",
            f"Change versus previous is {format_millions(delta_total)}.",
        ]
        table_title = "NTE Summary"
        chart_title = "NTE Movement Matrix"
    else:
        week_1 = float(summary.get("recent_week_1", 0.0) or 0.0)
        week_2 = float(summary.get("recent_week_2", 0.0) or 0.0)
        cards = [
            Card("Recent Week 1", format_percent(week_1), COLOR_ACCENT),
            Card("Recent Week 2", format_percent(week_2), COLOR_SECONDARY),
            Card("GM Forecast", format_percent(summary.get("gm_forecast")), COLOR_ACCENT),
        ]
        chart_png = summary_gm_chart(week_1, week_2, ("Recent 1", "Recent 2"), title="GM Recent Weeks")
        columns = ["metric", "value"]
        values = ["Forecast", format_percent(summary.get("gm_forecast"))]
        callouts = [
            f"Recent weeks show {format_percent(week_1)} and {format_percent(week_2)}.",
            f"GM forecast is {format_percent(summary.get('gm_forecast'))}.",
        ]
        table_title = "GM Summary"
        chart_title = "GM Movement Matrix"
    title = f"Summary - {sheet_name.title()}"
    return SlideData(
        title=title,
        table_columns=columns,
        table_values=values,
        cards=cards,
        chart_png=chart_png,
        table_title=table_title,
        chart_title=chart_title,
        callouts=callouts,
    )


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
        st.write(f"Using data_reader module from: {Path(data_reader.__file__).resolve()}")
        st.write(f"Pandas version: {pd.__version__}")
        with st.spinner("Reading workbook..."):
            sheet_dfs = read_workbook(uploaded_file)
        st.markdown("### Detected sheets")
        for sheet_key, df in sheet_dfs.items():
            original_sheet = df.attrs.get("original_sheet_name") if hasattr(df, "attrs") else None
            original_sheet = original_sheet or df.get("original_sheet_name", None)
            st.write(f"**{sheet_key.title()}** - original sheet: {original_sheet or sheet_key}")
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

        sheet_adh_values = get_sheet_adh_values(sheet_dfs)
        st.markdown("### ADH values by sheet")
        for sheet_key, adh_list in sheet_adh_values.items():
            st.write(f"**{sheet_key.title()}**")
            if adh_list:
                st.write(", ".join(adh_list))
            else:
                st.write("No ADH values detected")

        similar_adh = find_similar_adh_names(sheet_dfs)
        if similar_adh:
            st.markdown("### Similar ADH names across sheets")
            st.table(pd.DataFrame(similar_adh).drop(columns=["score"]).assign(score=[item["score"] for item in similar_adh]))

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
