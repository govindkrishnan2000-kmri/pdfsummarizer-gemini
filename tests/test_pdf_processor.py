import io
from pathlib import Path

import pytest

from pdf_processor import PDFProcessor

SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "sample.pdf"


@pytest.fixture(scope="module")
def processor() -> PDFProcessor:
    return PDFProcessor()


def test_extract_text_from_sample(processor):
    with SAMPLE.open("rb") as fh:
        text = processor.extract_text_from_pdf(fh)
    assert "Acme Analytics" in text
    assert "quarter" in text.lower()


def test_extract_invalid_pdf_raises(processor):
    with pytest.raises(RuntimeError):
        processor.extract_text_from_pdf(io.BytesIO(b"this is not a pdf"))


def test_clean_text_normalises_whitespace_and_control_chars(processor):
    raw = "  Hello\x00   world \t again \n\n\n\nNext   line.  "
    cleaned = processor.clean_text(raw)
    assert "\x00" not in cleaned
    assert "  " not in cleaned
    assert "\n\n\n" not in cleaned
    assert cleaned == "Hello world again\n\nNext line."


def test_count_tokens_positive(processor):
    assert processor.count_tokens("hello world") > 0
    assert processor.count_tokens("") == 0


def test_chunk_text_respects_limit(processor):
    text = " ".join(f"Sentence number {i} has a few words." for i in range(200))
    chunks = processor.chunk_text(text, max_tokens=60)
    assert len(chunks) > 1
    assert all(processor.count_tokens(c) <= 65 for c in chunks)
    assert " ".join(chunks) == text


def test_chunk_text_rejects_empty(processor):
    with pytest.raises(ValueError, match="No extractable text"):
        processor.chunk_text("   \n  ")


def test_chunk_text_rejects_bad_limit(processor):
    with pytest.raises(ValueError, match="positive"):
        processor.chunk_text("Some text.", max_tokens=0)


def test_metadata(processor):
    with SAMPLE.open("rb") as fh:
        meta = processor.get_pdf_metadata(fh)
    assert meta["num_pages"] >= 1
    assert meta["title"] == "Quarterly Operations Review"
    assert meta["author"] == "Acme Analytics"


def test_metadata_error_is_returned(processor):
    meta = processor.get_pdf_metadata(io.BytesIO(b"broken"))
    assert "error" in meta
