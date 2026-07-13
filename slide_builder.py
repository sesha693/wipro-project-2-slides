from dataclasses import dataclass
from io import BytesIO
from typing import Optional

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from config import CARD_BORDER_RADIUS, CARD_BORDER_WIDTH, CARD_BG, HEADER_FONT, HEADER_FONT_SIZE, SLIDE_HEIGHT_INCHES, SLIDE_WIDTH_INCHES, TABLE_HEADER_BG, TABLE_BORDER_COLOR


def _hex_to_rgb(hex_color: str) -> RGBColor:
    hex_color = hex_color.lstrip("#")
    return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


@dataclass
class Card:
    label: str
    value: str
    color_hex: str


@dataclass
class SlideData:
    title: str
    table_columns: list[str]
    table_values: list[str]
    cards: list[Card]
    chart_png: bytes
    notes: Optional[str] = None


def add_header(slide, text: str, left: Inches, top: Inches, width: Inches, height: Inches):
    shape = slide.shapes.add_textbox(left, top, width, height)
    frame = shape.text_frame
    frame.clear()
    p = frame.paragraphs[0]
    p.text = text
    p.font.name = HEADER_FONT
    p.font.size = Pt(HEADER_FONT_SIZE)
    p.font.bold = True
    p.alignment = PP_ALIGN.LEFT


def add_single_row_table(slide, columns: list[str], values: list[str], left, top, width, height):
    table_shape = slide.shapes.add_table(rows=2, cols=len(columns), left=left, top=top, width=width, height=height)
    table = table_shape.table
    header_color = _hex_to_rgb(TABLE_HEADER_BG)
    for idx, header in enumerate(columns):
        cell = table.cell(0, idx)
        cell.text = header
        cell.fill.solid()
        cell.fill.fore_color.rgb = header_color
        para = cell.text_frame.paragraphs[0]
        para.font.bold = True
        para.font.size = Pt(10)
    for idx, value in enumerate(values):
        cell = table.cell(1, idx)
        cell.text = value
        para = cell.text_frame.paragraphs[0]
        para.font.size = Pt(12)
    border_color = _hex_to_rgb(TABLE_BORDER_COLOR)
    for row in range(2):
        for col in range(len(columns)):
            cell = table.cell(row, col)
            for side in (cell.border_top, cell.border_bottom, cell.border_left, cell.border_right):
                side.fill.solid()
                side.fill.fore_color.rgb = border_color


def add_data_cards(slide, cards: list[Card], left, top, width, height, cols=4):
    card_width = width / cols
    card_height = height
    for index, card in enumerate(cards):
        card_left = left + card_width * index
        shape = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            card_left,
            top,
            card_width - Inches(0.1),
            card_height,
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = _hex_to_rgb(CARD_BG)
        shape.line.color.rgb = _hex_to_rgb(card.color_hex)
        shape.line.width = Pt(CARD_BORDER_WIDTH)
        text_frame = shape.text_frame
        text_frame.clear()
        label_para = text_frame.paragraphs[0]
        label_para.text = card.label.upper()
        label_para.font.size = Pt(9)
        label_para.font.bold = True
        label_para.alignment = PP_ALIGN.LEFT
        label_para.space_after = Pt(4)
        value_para = text_frame.add_paragraph()
        value_para.text = card.value
        value_para.font.size = Pt(20)
        value_para.font.bold = True
        value_para.alignment = PP_ALIGN.LEFT


def add_chart_image(slide, image_bytes: bytes, left, top, width, height):
    stream = BytesIO(image_bytes)
    slide.shapes.add_picture(stream, left, top, width=width, height=height)


def create_pptx(slide_data_list: list[SlideData], filename: str, template_path: Optional[str] = None) -> bytes:
    prs = Presentation(template_path) if template_path else Presentation()
    prs.slide_width = Inches(SLIDE_WIDTH_INCHES)
    prs.slide_height = Inches(SLIDE_HEIGHT_INCHES)
    for slide_data in slide_data_list:
        slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(slide_layout)
        add_header(slide, slide_data.title, Inches(0.3), Inches(0.2), Inches(12.7), Inches(0.6))
        add_single_row_table(slide, slide_data.table_columns, slide_data.table_values, Inches(0.3), Inches(1.0), Inches(7.5), Inches(0.7))
        add_data_cards(slide, slide_data.cards, Inches(0.3), Inches(1.9), Inches(7.5), Inches(1.4))
        add_chart_image(slide, slide_data.chart_png, Inches(8.3), Inches(1.0), Inches(4.7), Inches(4.3))
        if slide_data.notes:
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = slide_data.notes
    output = BytesIO()
    prs.save(output)
    output.seek(0)
    return output.read()
