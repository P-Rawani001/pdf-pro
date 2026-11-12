"""Grounded local PDF Q&A, summarization, explanation, and entity extraction."""

from __future__ import annotations

from dataclasses import dataclass
import pymupdf

from app.ai.document_parser import extract_relevant_context
from app.ai.ollama_client import OllamaClient

SYSTEM_PROMPT = (
    "You are PDF Pro's local document assistant. Answer strictly using ONLY the provided PDF excerpts. "
    "Rules:\n"
    "1. Cite page numbers in square brackets like [Page 2] for every fact you state.\n"
    "2. If the provided excerpts do not contain enough evidence to answer, respond clearly: "
    "'The provided document pages do not contain enough information to answer this.'\n"
    "3. Never invent facts, names, dates, or citations not present in the text."
)


@dataclass(frozen=True)
class AssistantResponse:
    """Structured reply returned by the local AI assistant."""

    answer: str
    referenced_pages: list[int]


class PdfAiAssistant:
    """Orchestrates grounded prompts against a PyMuPDF document using Ollama."""

    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client or OllamaClient()

    def ask_question(
        self,
        doc: pymupdf.Document,
        model: str,
        question: str,
        current_page_0based: int = 0,
    ) -> AssistantResponse:
        context, pages = extract_relevant_context(
            doc, query=question, current_page_0based=current_page_0based
        )
        if not context:
            return AssistantResponse(
                answer="No selectable text was found in this PDF (it may be a scanned image PDF).",
                referenced_pages=[],
            )
        prompt = (
            f"DOCUMENT EXCERPTS:\n{context}\n\n"
            f"USER QUESTION: {question.strip()}\n"
            f"Answer concisely with [Page X] citations:"
        )
        reply = self.client.chat(model=model, system_prompt=SYSTEM_PROMPT, user_prompt=prompt)
        return AssistantResponse(answer=reply, referenced_pages=pages)

    def summarize_document(
        self,
        doc: pymupdf.Document,
        model: str,
        current_page_0based: int = 0,
    ) -> AssistantResponse:
        context, pages = extract_relevant_context(
            doc, query="", current_page_0based=current_page_0based
        )
        if not context:
            return AssistantResponse(
                answer="No selectable text was found in this PDF to summarize.",
                referenced_pages=[],
            )
        prompt = (
            f"DOCUMENT EXCERPTS:\n{context}\n\n"
            "Provide a clear, structured summary of the key points in these excerpts. "
            "Include [Page X] citations for each point."
        )
        reply = self.client.chat(model=model, system_prompt=SYSTEM_PROMPT, user_prompt=prompt)
        return AssistantResponse(answer=reply, referenced_pages=pages)

    def extract_entities(
        self,
        doc: pymupdf.Document,
        model: str,
        current_page_0based: int = 0,
    ) -> AssistantResponse:
        context, pages = extract_relevant_context(
            doc, query="date year name person organization", current_page_0based=current_page_0based
        )
        if not context:
            return AssistantResponse(
                answer="No selectable text was found in this PDF.",
                referenced_pages=[],
            )
        prompt = (
            f"DOCUMENT EXCERPTS:\n{context}\n\n"
            "Extract key dates, names of people/organizations, and important figures found in the text. "
            "Cite [Page X] beside each item."
        )
        reply = self.client.chat(model=model, system_prompt=SYSTEM_PROMPT, user_prompt=prompt)
        return AssistantResponse(answer=reply, referenced_pages=pages)

    def explain_selection(
        self,
        selected_text: str,
        page_1based: int,
        model: str,
    ) -> AssistantResponse:
        cleaned = selected_text.strip()
        if not cleaned:
            return AssistantResponse(
                answer="Select text on the PDF page first (in Reader mode, drag over text) before clicking Explain Selection.",
                referenced_pages=[],
            )
        prompt = (
            f"EXCERPT FROM [Page {page_1based}]:\n{cleaned[:4000]}\n\n"
            f"Explain this passage clearly in plain language and cite [Page {page_1based}]."
        )
        reply = self.client.chat(model=model, system_prompt=SYSTEM_PROMPT, user_prompt=prompt)
        return AssistantResponse(answer=reply, referenced_pages=[page_1based])
