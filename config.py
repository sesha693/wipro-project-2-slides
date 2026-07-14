from pathlib import Path

# General slide and chart defaults
SLIDE_WIDTH_INCHES = 13.3333
SLIDE_HEIGHT_INCHES = 7.5
HEADER_FONT = "Calibri"
HEADER_FONT_SIZE = 28
TABLE_HEADER_BG = "#F2F2F2"
TABLE_BORDER_COLOR = "#D9D9D9"
CARD_BG = "#FFFFFF"
CARD_BORDER_WIDTH = 1.5
CARD_BORDER_RADIUS = 8
CARD_LABEL_FONT_SIZE = 10
CARD_VALUE_FONT_SIZE = 24
CHART_DPI = 150
CHART_SCALE = 2
BACKGROUND_COLOR = "#EDF2F7"
HEADER_ACCENT_COLOR = "#1F3A57"
PANEL_BG_COLOR = "#FFFFFF"
CARD_BORDER_COLOR = "#D9E2EA"

# Color palette
COLOR_POSITIVE = "#2ECC71"
COLOR_NEGATIVE = "#E74C3C"
COLOR_ACCENT = "#34495E"
COLOR_SECONDARY = "#5DADE2"
COLOR_TABLE_HEADER = "#F3F6F8"

# ADH sheet matcher tokens
SHEET_MATCHERS = {
    "revenue": ["rev", "revenue"],
    "nte": ["nte", "cost", "expense", "people"],
    "gm": ["gm", "gross"],
}

# Workbook and week detection
WEEK_COLUMN_REGEX = r"(?i)wk[\s_]*0*?(\d+)|wk(\d+)|wk[\s_]*\d+[\s_]*p&l"

# Paths
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "template.pptx"
