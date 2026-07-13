import logging
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent.parent / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)

logger = logging.getLogger("slide_builder_app")

coercion_warnings = []


def log_coercion(sheet: str, row_index: int, column: str, original_value: str, coerced_value: str, reason: str) -> None:
    message = {
        "sheet": sheet,
        "row_index": row_index,
        "column": column,
        "original_value": original_value,
        "coerced_value": coerced_value,
        "reason": reason,
    }
    coercion_warnings.append(message)
    logger.warning("Coercion warning: %s", message)


def get_warnings() -> list[dict]:
    return coercion_warnings


def clear_warnings() -> None:
    coercion_warnings.clear()
