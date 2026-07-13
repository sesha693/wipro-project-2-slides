from io import BytesIO
from typing import Iterable

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import CHART_SCALE, COLOR_ACCENT, COLOR_NEGATIVE, COLOR_POSITIVE, COLOR_SECONDARY


def _to_png_bytes(fig, width: int, height: int) -> bytes:
    return fig.to_image(format="png", width=width, height=height, scale=CHART_SCALE)


def horizontal_bar_target_vs_locked_risk(
    target: float,
    locked: float,
    risk: float,
    title: str,
    width: int = 1600,
    height: int = 600,
    accent_color: str = COLOR_ACCENT,
    secondary_color: str = COLOR_SECONDARY,
) -> bytes:
    total = locked + risk
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=["Target"],
            x=[target],
            orientation="h",
            name="Target",
            marker_color=accent_color,
            text=[f"{target:.2f}M"],
            textposition="inside",
        )
    )
    fig.add_trace(
        go.Bar(
            y=["Locked + Risk"],
            x=[total],
            orientation="h",
            name="Locked + Risk",
            marker_color=secondary_color,
            text=[f"{total:.2f}M"],
            textposition="inside",
        )
    )
    fig.update_layout(
        title=title,
        barmode="stack",
        plot_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#EDEDED"),
        yaxis=dict(showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return _to_png_bytes(fig, width, height)


def grouped_bar_q1_q2_q2target(
    q1: float,
    q2_target: float,
    q2_actual: float,
    title: str,
    width: int = 1600,
    height: int = 600,
    accent_color: str = COLOR_ACCENT,
    secondary_color: str = COLOR_SECONDARY,
    positive_color: str = COLOR_POSITIVE,
) -> bytes:
    labels = ["Q1'27", "Q2'27 Target", "Q2'27 Actual"]
    values = [q1, q2_target, q2_actual]
    colors = [accent_color, secondary_color, positive_color]
    fig = go.Figure(
        data=[
            go.Bar(x=labels, y=values, marker_color=colors, text=[f"{val:.2f}M" for val in values], textposition="auto"),
        ]
    )
    fig.update_layout(
        title=title,
        plot_bgcolor="white",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#EDEDED"),
    )
    return _to_png_bytes(fig, width, height)


def stacked_bar_people_nonpeople(
    prev_people: float,
    prev_non: float,
    curr_people: float,
    curr_non: float,
    title: str,
    width: int = 1600,
    height: int = 600,
    accent_color: str = COLOR_ACCENT,
    secondary_color: str = COLOR_SECONDARY,
    positive_color: str = COLOR_POSITIVE,
    negative_color: str = COLOR_NEGATIVE,
) -> bytes:
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Prev Week People", x=["Previous"], y=[prev_people], marker_color=accent_color, text=[f"{prev_people:.2f}M"], textposition="inside"))
    fig.add_trace(go.Bar(name="Prev Week Non-People", x=["Previous"], y=[prev_non], marker_color=secondary_color, text=[f"{prev_non:.2f}M"], textposition="inside"))
    fig.add_trace(go.Bar(name="Current Week People", x=["Current"], y=[curr_people], marker_color=positive_color, text=[f"{curr_people:.2f}M"], textposition="inside"))
    fig.add_trace(go.Bar(name="Current Week Non-People", x=["Current"], y=[curr_non], marker_color=negative_color, text=[f"{curr_non:.2f}M"], textposition="inside"))
    fig.update_layout(
        barmode="group",
        title=title,
        plot_bgcolor="white",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#EDEDED"),
    )
    return _to_png_bytes(fig, width, height)


def wk_bar_chart(
    week1: float,
    week2: float,
    labels: tuple[str, str],
    title: str,
    width: int = 1600,
    height: int = 600,
    accent_color: str = COLOR_ACCENT,
    secondary_color: str = COLOR_SECONDARY,
) -> bytes:
    values = [week1, week2]
    fig = go.Figure(
        data=[
            go.Bar(x=list(labels), y=values, marker_color=[accent_color, secondary_color], text=[f"{val:.2f}M" for val in values], textposition="auto"),
        ]
    )
    fig.update_layout(
        title=title,
        plot_bgcolor="white",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#EDEDED"),
    )
    return _to_png_bytes(fig, width, height)


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
