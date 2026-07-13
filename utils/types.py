from typing import TypedDict


class CoercionWarning(TypedDict):
    sheet: str
    row_index: int
    column: str
    original_value: str
    coerced_value: str
    reason: str
