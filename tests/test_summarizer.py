import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from prompts import ANALYSIS, CHUNK_SUMMARY, COMBINE, QUOTES, STYLES
from summarizer import PDFSummarizer


def prompt_text(prompt_value) -> str:
    return "\n".join(str(m.content) for m in prompt_value.to_messages())


def llm_returning(text: str) -> RunnableLambda:
    return RunnableLambda(lambda _: AIMessage(content=text))


def llm_failing_on(marker: str, text: str = "ok") -> RunnableLambda:
    def call(prompt_value):
        if marker in prompt_text(prompt_value):
            raise RuntimeError(f"boom: {marker}")
        return AIMessage(content=text)

    return RunnableLambda(call)


def test_prompt_templates_have_expected_styles():
    assert set(STYLES) == {"brief", "detailed", "bullet_points", "executive"}
    for prompt in (CHUNK_SUMMARY, COMBINE, ANALYSIS, QUOTES):
        assert prompt.input_variables


def test_summarize_text_uses_style():
    summarizer = PDFSummarizer(llm=llm_returning("short summary"))
    assert summarizer.summarize_text("Some document", "brief") == "short summary"


def test_summarize_chunks_success():
    summarizer = PDFSummarizer(llm=llm_returning("chunk summary"))
    result = summarizer.summarize_chunks(["alpha", "beta", "gamma"], "detailed")

    assert result["total_chunks"] == 3
    assert result["summary_type"] == "detailed"
    assert all(item["ok"] for item in result["individual_summaries"])
    assert result["combined_summary"] == "chunk summary"
    assert [item["chunk_number"] for item in result["individual_summaries"]] == [1, 2, 3]


def test_summarize_chunks_tolerates_failed_chunk():
    summarizer = PDFSummarizer(llm=llm_failing_on("FAILME", text="good summary"))
    result = summarizer.summarize_chunks(["fine text", "FAILME text"], "brief")

    ok_flags = [item["ok"] for item in result["individual_summaries"]]
    assert ok_flags == [True, False]
    # Only one valid summary remains, so it is returned without a combine call.
    assert result["combined_summary"] == "good summary"


def test_combine_failure_falls_back_to_sections():
    summarizer = PDFSummarizer(llm=llm_failing_on("Merge them", text="chunk summary"))
    result = summarizer.summarize_chunks(["one", "two"], "brief")

    assert all(item["ok"] for item in result["individual_summaries"])
    assert result["combined_summary"].startswith("Combined Summary:")
    assert "Section 1: chunk summary" in result["combined_summary"]


def test_all_chunks_fail_returns_placeholder():
    summarizer = PDFSummarizer(llm=llm_failing_on("FAILME"))
    result = summarizer.summarize_chunks(["FAILME one", "FAILME two"], "brief")

    assert not any(item["ok"] for item in result["individual_summaries"])
    assert result["combined_summary"] == "No valid summaries were generated."


def test_analyze_document_structure_success():
    summarizer = PDFSummarizer(llm=llm_returning("analysis text"))
    assert summarizer.analyze_document_structure("doc") == {
        "analysis": "analysis text",
        "status": "success",
    }


def test_analyze_document_structure_failure():
    summarizer = PDFSummarizer(llm=llm_failing_on("Analyze the structure"))
    result = summarizer.analyze_document_structure("doc")
    assert result["status"] == "error"
    assert "Error analyzing document" in result["analysis"]


def test_extract_key_quotes_strips_numbering_and_quotes():
    reply = '1. "First quote"\n- Second quote\n• Third quote\n\n'
    summarizer = PDFSummarizer(llm=llm_returning(reply))
    assert summarizer.extract_key_quotes("doc") == ["First quote", "Second quote", "Third quote"]


def test_extract_key_quotes_caps_at_ten():
    reply = "\n".join(f"quote {i}" for i in range(15))
    summarizer = PDFSummarizer(llm=llm_returning(reply))
    assert len(summarizer.extract_key_quotes("doc")) == 10


def test_missing_api_key_still_constructs(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x" * 30)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    summarizer = PDFSummarizer()
    assert summarizer.model == "gemini-test"
    assert summarizer.llm.max_retries == 4


@pytest.mark.parametrize("summary_type", ["brief", "detailed", "bullet_points", "executive", "unknown"])
def test_summarize_chunks_accepts_every_style(summary_type):
    summarizer = PDFSummarizer(llm=llm_returning("ok"))
    result = summarizer.summarize_chunks(["text"], summary_type)
    assert result["individual_summaries"][0]["ok"]
