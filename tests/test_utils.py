import pandas as pd
import pytest

from utils import (
    create_summary_dataframe,
    estimate_processing_time,
    export_summary_to_text,
    validate_api_key,
)

SUMMARY = {
    "total_chunks": 2,
    "summary_type": "bullet_points",
    "combined_summary": "Final combined text.",
    "individual_summaries": [
        {"chunk_number": 1, "summary": "First.", "ok": True, "original_length": 100, "summary_length": 40},
        {"chunk_number": 2, "summary": "Error processing chunk: boom", "ok": False,
         "original_length": 200, "summary_length": 0},
    ],
}


def test_export_contains_header_and_chunks():
    text = export_summary_to_text(SUMMARY, "report.pdf")
    assert "File: report.pdf" in text
    assert "Summary Type: Bullet Points" in text
    assert "Final combined text." in text
    assert "Chunk 2 (FAILED):" in text
    assert "Generated on:" in text


def test_export_without_filename_omits_line():
    assert "File:" not in export_summary_to_text(SUMMARY)


def test_dataframe_shape_and_values():
    df = create_summary_dataframe(SUMMARY)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == [
        "Chunk", "Original Length", "Summary Length", "Compression Ratio", "Status"
    ]
    assert df.loc[0, "Compression Ratio"] == 0.4
    assert df.loc[1, "Status"] == "Error"


def test_dataframe_handles_zero_length():
    data = {
        "total_chunks": 1,
        "summary_type": "brief",
        "combined_summary": "x",
        "individual_summaries": [
            {"chunk_number": 1, "summary": "", "ok": True, "original_length": 0, "summary_length": 0}
        ],
    }
    assert create_summary_dataframe(data).loc[0, "Compression Ratio"] == 0


@pytest.mark.parametrize(
    ("chunks", "expected"),
    [(1, "~5 seconds"), (4, "~8 seconds"), (80, "~1 min 5s")],
)
def test_estimate_processing_time(chunks, expected):
    assert estimate_processing_time(chunks) == expected


def test_validate_api_key_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert validate_api_key() is False


def test_validate_api_key_too_short(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "short")
    assert validate_api_key() is False


def test_validate_api_key_placeholder(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "your_gemini_api_key_here")
    assert validate_api_key() is False
