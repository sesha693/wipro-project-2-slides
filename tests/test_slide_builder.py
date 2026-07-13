from slide_builder import Card, SlideData, create_pptx


def test_create_pptx_three_slides():
    slide_data = []
    for index in range(3):
        slide_data.append(
            SlideData(
                title=f"Slide {index + 1}",
                table_columns=["A", "B"],
                table_values=["1", "2"],
                cards=[Card("Delta", "1.00M", "#2ECC71")],
                chart_png=b"\x89PNG\r\n\x1a\n" + b"0" * 2000,
            )
        )
    pptx_bytes = create_pptx(slide_data, filename="test.pptx")
    assert isinstance(pptx_bytes, (bytes, bytearray))
    assert len(pptx_bytes) > 1000
