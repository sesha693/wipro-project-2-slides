import math
from typing import Optional, Any


def safe_str(value: Any) -> str:
    """Return a readable string for values that may be None or NaN."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    return str(value)


def format_millions(value: Optional[float]) -> str:
    """Format numeric values in millions with two decimals."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    return f"{value:.2f}M"


def format_percent(value: Optional[float]) -> str:
    """Format numeric values as percentages with two decimals."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    return f"{value * 100:.2f}%"


def color_for_delta(value: Optional[float]) -> str:
    """Return a hex color for positive/negative delta values."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "#7F8C8D"
    return "#2ECC71" if value >= 0 else "#E74C3C"
