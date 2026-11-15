import logging
import os
import re

from dotenv import load_dotenv
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI

from prompts import ANALYSIS, CHUNK_SUMMARY, COMBINE, QUOTES, STYLES

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3.1-flash-lite"


def _text_of(message) -> str:
    """Gemini 3 returns a list of content blocks; .text joins them."""
    return str(message.text)


class PDFSummarizer:
    """Map-reduce summarizer built on LangChain prompt chains.

    ``llm`` can be injected for tests; otherwise a Gemini chat model is created
    with retries enabled so transient 429/5xx responses back off automatically.
    """

    def __init__(self, model: str | None = None, llm: Runnable | None = None):
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self.llm = llm if llm is not None else ChatGoogleGenerativeAI(
            model=self.model,
            temperature=0.3,
            google_api_key=os.getenv("GEMINI_API_KEY"),
            max_retries=4,
            timeout=120,
        )
        # str(m.text) keeps the text content and drops the TextAccessor type
        parser = RunnableLambda(_text_of)
        self.chunk_chain = CHUNK_SUMMARY | self.llm | parser
        self.combine_chain = COMBINE | self.llm | parser
        self.analysis_chain = ANALYSIS | self.llm | parser
        self.quotes_chain = QUOTES | self.llm | parser

    def summarize_text(self, text: str, summary_type: str = "detailed") -> str:
        style = STYLES.get(summary_type, STYLES["detailed"])
        return self.chunk_chain.invoke({"style": style, "text": text})

    def summarize_chunks(self, chunks: list[str], summary_type: str = "detailed") -> dict:
        """Summarize each chunk (map) and merge the results (reduce)."""
        style = STYLES.get(summary_type, STYLES["detailed"])
        inputs = [{"style": style, "text": c} for c in chunks]
        results = self.chunk_chain.batch(
            inputs, config={"max_concurrency": 4}, return_exceptions=True
        )

        summaries = []
        for i, (chunk, res) in enumerate(zip(chunks, results, strict=False), start=1):
            ok = not isinstance(res, Exception)
            if not ok:
                logger.warning("Chunk %d failed: %s", i, res)
            summary = res if ok else f"Error processing chunk: {res}"
            summaries.append({
                "chunk_number": i,
                "summary": summary,
                "ok": ok,
                "original_length": len(chunk),
                "summary_length": len(summary) if ok else 0,
            })

        return {
            "individual_summaries": summaries,
            "combined_summary": self.combine_summaries(summaries, summary_type),
            "total_chunks": len(chunks),
            "summary_type": summary_type,
        }

    def combine_summaries(self, chunk_summaries: list[dict], summary_type: str) -> str:
        valid = [cs["summary"] for cs in chunk_summaries if cs.get("ok")]
        if not valid:
            return "No valid summaries were generated."
        if len(valid) == 1:
            return valid[0]

        sections = "\n\n".join(f"Section {i}: {s}" for i, s in enumerate(valid, start=1))
        style = STYLES.get(summary_type, STYLES["detailed"])
        try:
            return self.combine_chain.invoke({"style": style, "summaries": sections})
        except Exception as e:  # noqa: BLE001
            logger.warning("Combine step failed, returning concatenated sections: %s", e)
            return f"Combined Summary:\n\n{sections}"

    def analyze_document_structure(self, text: str) -> dict:
        try:
            analysis = self.analysis_chain.invoke({"text": text[:3000]})
            return {"analysis": analysis, "status": "success"}
        except Exception as e:  # noqa: BLE001
            logger.warning("Document analysis failed: %s", e)
            return {"analysis": f"Error analyzing document: {e}", "status": "error"}

    def extract_key_quotes(self, text: str) -> list[str]:
        response = self.quotes_chain.invoke({"text": text})
        lines = (
            re.sub(r"^\s*(\d+[.)]|[-*•])\s*", "", ln).strip(' "“”')
            for ln in response.splitlines()
        )
        return [ln for ln in lines if ln][:10]
