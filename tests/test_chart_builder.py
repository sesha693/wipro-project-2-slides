from chart_builder import (
    grouped_bar_q1_q2_q2target,
    horizontal_bar_target_vs_locked_risk,
    sparkline,
    stacked_bar_people_nonpeople,
    wk_bar_chart,
)


def test_horizontal_bar_returns_bytes():
    png = horizontal_bar_target_vs_locked_risk(20.0, 0.0, 0.0, title="Test")
    assert isinstance(png, (bytes, bytearray))
    assert len(png) > 1000


def test_grouped_bar_returns_bytes():
    png = grouped_bar_q1_q2_q2target(10.0, 12.0, 9.0, title="Test")
    assert isinstance(png, (bytes, bytearray))
    assert len(png) > 1000


def test_stacked_bar_returns_bytes():
    png = stacked_bar_people_nonpeople(5.0, 3.0, 6.0, 4.0, title="Test")
    assert isinstance(png, (bytes, bytearray))
    assert len(png) > 1000


def test_wk_bar_chart_returns_bytes():
    png = wk_bar_chart(1.0, 2.0, ("WK1", "WK2"), title="Test")
    assert isinstance(png, (bytes, bytearray))
    assert len(png) > 1000


def test_sparkline_returns_bytes():
    png = sparkline([1, 2, 3, 4, 5])
    assert isinstance(png, (bytes, bytearray))
    assert len(png) > 1000
