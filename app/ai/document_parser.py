"""Page-indexed text extraction and keyword-ranked context selection for large PDFs."""

from __future__ import annotations

import re
import pymupdf

from app.config import AI_MAX_CONTEXT_CHARS


def extract_relevant_context(
    doc: pymupdf.Document,
    query: str = "",
    current_page_0based: int = 0,
    max_chars: int = AI_MAX_CONTEXT_CHARS,
) -> tuple[str, list[int]]:
    """Extract page-tagged text blocks most relevant to query within RAM/context limits."""
    total_pages = len(doc)
    if total_pages == 0:
        return "", []

    keywords = {
        w.lower()
        for w in re.findall(r"[A-Za-z0-9\u0900-\u097F]{3,}", query)
        if w.lower() not in {"the", "and", "for", "with", "what", "when", "where", "how", "this", "that", "from", "about", "summarize", "explain"}
    }

    scored_pages: list[tuple[int, int, str]] = []
    for idx in range(total_pages):
        raw_text = doc.load_page(idx).get_text("text").strip()
        if not raw_text:
            continue
        cleaned = re.sub(r"\n{3,}", "\n\n", raw_text)
        score = 0
        if idx == current_page_0based:
            score += 3
        if keywords:
            lower_txt = cleaned.lower()
            score += sum(lower_txt.count(kw) * 2 for kw in keywords)
        else:
            # For summaries / general extraction, favor early pages + current page
            score += max(0, 10 - idx)
        scored_pages.append((score, idx, cleaned))

    if not scored_pages:
        return "", []

    # Sort by relevance score descending, then page order ascending
    scored_pages.sort(key=lambda item: (-item[0], item[1]))

    selected_blocks: list[tuple[int, str]] = []
    used_chars = 0
    for _, idx, text in scored_pages:
        snippet = text[:2400]
        tagged = f"--- [Page {idx + 1}] ---\n{snippet}\n"
        if used_chars + len(tagged) > max_chars and selected_blocks:
            continue
        selected_blocks.append((idx + 1, tagged))
        used_chars += len(tagged)
        if used_chars >= max_chars:
            break

    # Present selected excerpts in natural reading order
    selected_blocks.sort(key=lambda item: item[0])
    pages_included = [p for p, _ in selected_blocks]
    combined = "\n".join(block for _, block in selected_blocks)
    return combined, pages_included
