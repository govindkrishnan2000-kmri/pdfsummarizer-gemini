# Walkthrough

A quick tour of the request path, from upload to downloadable summary.

## 1. Settings and key check

`app.py` calls `validate_api_key()` from `utils.py` before rendering the uploader. It checks that `GEMINI_API_KEY` exists and looks complete, then shows a quiet sidebar caption. No key means the app stops with setup instructions instead of failing mid-run.

The sidebar controls model, summary type, max tokens per chunk, and whether to run analysis and quote extraction.

## 2. PDF metadata

`PDFProcessor.get_pdf_metadata()` reads the page count plus `/Title`, `/Author` and `/Subject`. Missing fields render as `Unknown`; a broken file returns `{'error': ...}` instead of raising.

## 3. Extraction and cleaning

`extract_text_from_pdf()` seeks to the start, walks the pages and skips any page that fails to extract, logging a warning. `clean_text()` removes control characters, collapses runs of spaces and blank lines, and keeps paragraph breaks.

## 4. Chunking

`chunk_text()` splits on sentence boundaries, hard-splitting any single sentence longer than `max_tokens`. It packs sentences into chunks while tracking an approximate token count (the `+1` per sentence accounts for the joining space). Empty text raises `ValueError`, which the UI turns into a "scanned PDF" hint.

## 5. Map step

`PDFSummarizer.summarize_chunks()` builds one prompt input per chunk and calls `chunk_chain.batch(..., max_concurrency=4, return_exceptions=True)`. Failures are recorded per chunk rather than aborting the run; each result carries `ok`, `original_length` and `summary_length`.

The chain is `CHUNK_SUMMARY | llm | parser`. The parser is a `RunnableLambda` that returns `str(message.text)` so multi-block Gemini 3 responses come back as plain text.

## 6. Reduce step

`combine_summaries()` labels the surviving summaries `Section 1..N`, sends them through `COMBINE`, and falls back to concatenating the sections if the merge call itself fails. With a single valid summary it returns it unchanged; with none it returns a placeholder.

## 7. Analysis and quotes

Analysis sends the first 3000 characters through `ANALYSIS` and returns `{analysis, status}` so the UI can warn without hiding the summary. Quote extraction sends the first 5000 characters through `QUOTES`, strips numbering, bullets and surrounding quotes, and caps the list at ten.

## 8. Results and exports

Results are stored in `st.session_state['results']` so download buttons and reruns don't recompute. `format_summary_display()` renders metrics and per-chunk summaries; `export_summary_to_text()` builds the report; `create_summary_dataframe()` produces the CSV with a compression ratio per chunk.

## 9. Failure behavior

- Bad key: blocked up front.
- Scanned PDF: `ValueError` with a clear message.
- One chunk fails: the rest still summarize, the failed row is marked in the CSV.
- Combine fails: sections are concatenated.
- Rate limits: `ChatGoogleGenerativeAI(max_retries=4)` backs off before giving up.
