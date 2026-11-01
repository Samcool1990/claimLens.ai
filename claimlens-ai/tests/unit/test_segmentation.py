from app.services.pdf_ingestion import ExtractedPage, segment_page


def test_deterministic_page_segmentation():
    text = "1. Definitions\nCoverage begins here.\n\n2. Exclusions\nClaims are excluded."
    clauses = segment_page(ExtractedPage(0, 1, text))
    assert clauses
    assert clauses[0].text in text
    assert all(c.end_offset > c.start_offset for c in clauses)
