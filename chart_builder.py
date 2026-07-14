from io import BytesIO
from typing import Iterable

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import CHART_SCALE, COLOR_ACCENT, COLOR_NEGATIVE, COLOR_POSITIVE, COLOR_SECONDARY


def _to_png_bytes(fig, width: int, height: int) -> bytes:
    return fig.to_image(format="png", width=width, height=height, scale=CHART_SCALE)


def _apply_chart_style(fig, title: str, width: int, height: int, showlegend: bool = False):
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Calibri, Arial, sans-serif", size=12, color="#2C3E50"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=22, b=18),
        width=width,
        height=height,
        showlegend=showlegend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=9),
            bgcolor="rgba(255,255,255,0)",
        ),
        title=dict(text=title, x=0.01, xanchor="left", yanchor="top", font=dict(size=12), pad=dict(t=6, b=0)),
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showline=False,
        tickfont=dict(size=10),
        automargin=True,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#E8EDF2",
        zeroline=False,
        showline=False,
        tickfont=dict(size=10),
    )
    return fig


def horizontal_bar_target_vs_locked_risk(
    target: float,
    locked: float,
    risk: float,
    title: str,
    width: int = 820,
    height: int = 240,
    accent_color: str = COLOR_ACCENT,
    secondary_color: str = COLOR_SECONDARY,
    positive_color: str = COLOR_POSITIVE,
) -> bytes:
    total = locked + risk
    fig = go.Figure(
        data=[
            go.Bar(
                y=[""],
                x=[target],
                orientation="h",
                name="Target",
                marker_color=accent_color,
                text=[f"{target:.2f}M"],
                textposition="inside",
                textfont=dict(size=10, color="white"),
                marker_line_color="#ffffff",
                marker_line_width=2,
            ),
            go.Bar(
                y=[""],
                x=[total],
                orientation="h",
                name="Locked + Risk",
                marker_color=secondary_color,
                text=[f"{total:.2f}M"],
                textposition="inside",
                textfont=dict(size=10, color="white"),
                marker_line_color="#ffffff",
                marker_line_width=2,
            ),
        ]
    )
    fig.update_traces(textfont=dict(size=10), cliponaxis=False)
    _apply_chart_style(fig, title, width, height, showlegend=False)
    fig.update_layout(barmode="overlay", bargap=0.18, uniformtext_minsize=8, uniformtext_mode="hide")
    fig.update_yaxes(showgrid=False)
    return _to_png_bytes(fig, width, height)


def grouped_bar_q1_q2_q2target(
    q1: float,
    q2_target: float,
    q2_actual: float,
    title: str,
    width: int = 760,
    height: int = 240,
    accent_color: str = COLOR_ACCENT,
    secondary_color: str = COLOR_SECONDARY,
    positive_color: str = COLOR_POSITIVE,
) -> bytes:
    labels = ["Q1'27", "Q2'27 Target", "Q2'27 Actual"]
    values = [q1, q2_target, q2_actual]
    colors = [accent_color, secondary_color, positive_color]
    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color=colors,
                text=[f"{val:.2f}M" for val in values],
                textposition="outside",
                textfont=dict(size=10),
                marker_line_color="#ffffff",
                marker_line_width=1,
            ),
        ]
    )
    fig.update_traces(cliponaxis=False)
    _apply_chart_style(fig, title, width, height, showlegend=False)
    fig.update_layout(margin=dict(l=10, r=10, t=22, b=30), uniformtext_minsize=8, uniformtext_mode="hide")
    fig.update_xaxes(tickangle=-15)
    fig.update_yaxes(showgrid=False)
    return _to_png_bytes(fig, width, height)


def stacked_bar_people_nonpeople(
    prev_people: float,
    prev_non: float,
    curr_people: float,
    curr_non: float,
    title: str,
    width: int = 760,
    height: int = 260,
    accent_color: str = COLOR_ACCENT,
    secondary_color: str = COLOR_SECONDARY,
    positive_color: str = COLOR_POSITIVE,
    negative_color: str = COLOR_NEGATIVE,
) -> bytes:
    fig = go.Figure()
    fig.add_trace(go.Bar(name="People", x=["Previous", "Current"], y=[prev_people, curr_people], marker_color=accent_color, text=[f"{prev_people:.2f}M", f"{curr_people:.2f}M"], textposition="inside", textfont=dict(size=10)))
    fig.add_trace(go.Bar(name="Non-People", x=["Previous", "Current"], y=[prev_non, curr_non], marker_color=secondary_color, text=[f"{prev_non:.2f}M", f"{curr_non:.2f}M"], textposition="inside", textfont=dict(size=10)))
    fig.update_traces(cliponaxis=False)
    _apply_chart_style(fig, title, width, height, showlegend=True)
    fig.update_layout(barmode="stack", bargap=0.15, margin=dict(l=15, r=15, t=22, b=18), uniformtext_minsize=8, uniformtext_mode="hide")
    return _to_png_bytes(fig, width, height)


def wk_bar_chart(
    week1: float,
    week2: float,
    labels: tuple[str, str],
    title: str,
    width: int = 760,
    height: int = 240,
    accent_color: str = COLOR_ACCENT,
    secondary_color: str = COLOR_SECONDARY,
    percent: bool = False,
) -> bytes:
    values = [week1, week2]
    text_values = [f"{val:.2f}%" if percent else f"{val:.2f}M" for val in values]
    fig = go.Figure(
        data=[
            go.Bar(
                x=list(labels),
                y=values,
                marker_color=[accent_color, secondary_color],
                text=text_values,
                textposition="outside",
                textfont=dict(size=10),
                marker_line_color="#ffffff",
                marker_line_width=1,
            ),
        ]
    )
    fig.update_traces(cliponaxis=False)
    _apply_chart_style(fig, title, width, height, showlegend=False)
    fig.update_layout(margin=dict(l=18, r=18, t=22, b=30), uniformtext_minsize=8, uniformtext_mode="hide")
    fig.update_xaxes(tickangle=-20)
    fig.update_yaxes(showgrid=False)
    return _to_png_bytes(fig, width, height)


def summary_revenue_chart(total_target: float, total_projection: float, title: str, width: int = 760, height: int = 240) -> bytes:
    fig = go.Figure(
        data=[
            go.Bar(
                x=["Target", "Projection"],
                y=[total_target, total_projection],
                marker_color=[COLOR_SECONDARY, COLOR_ACCENT],
                text=[f"{total_target:.2f}M", f"{total_projection:.2f}M"],
                textposition="outside",
                textfont=dict(size=10),
                marker_line_color="#ffffff",
                marker_line_width=1,
            ),
        ]
    )
    fig.update_traces(cliponaxis=False)
    _apply_chart_style(fig, title, width, height, showlegend=False)
    fig.update_layout(margin=dict(l=18, r=18, t=22, b=30), uniformtext_minsize=8, uniformtext_mode="hide")
    fig.update_yaxes(showgrid=True, gridcolor="#F0F0F0")
    return _to_png_bytes(fig, width, height)


def summary_nte_chart(total_prev: float, total_curr: float, title: str, width: int = 760, height: int = 240) -> bytes:
    fig = go.Figure(
        data=[
            go.Bar(
                x=["Previous Total", "Current Total"],
                y=[total_prev, total_curr],
                marker_color=[COLOR_SECONDARY, COLOR_ACCENT],
                text=[f"{total_prev:.2f}M", f"{total_curr:.2f}M"],
                textposition="outside",
                textfont=dict(size=10),
                marker_line_color="#ffffff",
                marker_line_width=1,
            ),
        ]
    )
    fig.update_traces(cliponaxis=False)
    _apply_chart_style(fig, title, width, height, showlegend=False)
    fig.update_layout(margin=dict(l=18, r=18, t=22, b=30), uniformtext_minsize=8, uniformtext_mode="hide")
    fig.update_yaxes(showgrid=True, gridcolor="#F0F0F0")
    return _to_png_bytes(fig, width, height)


def summary_gm_chart(week1: float, week2: float, labels: tuple[str, str], title: str, width: int = 760, height: int = 240) -> bytes:
    return wk_bar_chart(week1, week2, labels, title=title, width=width, height=height, percent=True)


def sparkline(series: Iterable[float], width: int = 800, height: int = 120, accent_color: str = COLOR_ACCENT, secondary_color: str = COLOR_SECONDARY) -> bytes:
    values = [float(value) for value in series if value is not None]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(range(len(values))), y=values, mode="lines+markers", line=dict(color=accent_color), marker=dict(size=6, color=secondary_color)))
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="white",
    )
    return _to_png_bytes(fig, width, height)
