"""Right-panel / workspace UI for the optional local Ollama AI PDF Assistant."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ai.assistant import AssistantResponse, PdfAiAssistant
from app.ai.ollama_client import OllamaClient, OllamaUnavailableError
from app.core.document_manager import PdfDocumentSession
from app.services.file_service import FileService


class _AiWorkerThread(QThread):
    """Runs local Ollama inference off the UI thread so the window stays responsive."""

    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, task_fn) -> None:
        super().__init__()
        self._task_fn = task_fn

    def run(self) -> None:
        try:
            res = self._task_fn()
            self.finished_ok.emit(res)
        except OllamaUnavailableError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"Unexpected AI error: {exc}")


class AiAssistantPanel(QWidget):
    """Interactive local Ollama panel supporting Q&A, summary, entity extraction, and explanation."""

    status_message = Signal(str)

    def __init__(self, file_service: FileService, parent=None) -> None:
        super().__init__(parent)
        self.file_service = file_service
        self.settings = self.file_service.load_settings()
        self.client = OllamaClient()
        self.assistant = PdfAiAssistant(self.client)
        self._session: PdfDocumentSession | None = None
        self._selected_snippet: str = ""
        self._worker: _AiWorkerThread | None = None
        self._build_ui()
        self.refresh_ollama_status()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        self.status_label = QLabel("Checking local Ollama...")
        self.status_label.setProperty("class", "muted")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        model_row = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setFixedWidth(68)
        btn_refresh.clicked.connect(self.refresh_ollama_status)
        model_row.addWidget(self.model_combo, stretch=1)
        model_row.addWidget(btn_refresh)
        layout.addLayout(model_row)

        # Quick Action Buttons
        self.btn_summarize = QPushButton("Summarize PDF")
        self.btn_summarize.clicked.connect(self._run_summarize)
        layout.addWidget(self.btn_summarize)

        self.btn_entities = QPushButton("Extract Dates & Names")
        self.btn_entities.clicked.connect(self._run_entities)
        layout.addWidget(self.btn_entities)

        self.btn_explain = QPushButton("Explain Selected Text")
        self.btn_explain.clicked.connect(self._run_explain_selection)
        layout.addWidget(self.btn_explain)

        # Chat / Output Transcript
        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText(
            "Ask a question about the open PDF or click Summarize PDF above. "
            "All processing stays 100% local via Ollama."
        )
        layout.addWidget(self.transcript, stretch=1)

        # Question Input
        ask_row = QHBoxLayout()
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("Ask about this PDF...")
        self.question_input.returnPressed.connect(self._run_question)
        self.btn_ask = QPushButton("Ask")
        self.btn_ask.setObjectName("PrimaryBtn")
        self.btn_ask.setFixedWidth(56)
        self.btn_ask.clicked.connect(self._run_question)
        ask_row.addWidget(self.question_input, stretch=1)
        ask_row.addWidget(self.btn_ask)
        layout.addLayout(ask_row)

    def bind_session(self, session: PdfDocumentSession | None) -> None:
        self._session = session

    def set_selected_text(self, text: str) -> None:
        self._selected_snippet = text

    def refresh_ollama_status(self) -> None:
        status = self.client.check_status()
        self.status_label.setText(status.message)
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        if status.models:
            self.model_combo.addItems(status.models)
            saved_model = self.settings.get("ollama_model", "")
            if saved_model in status.models:
                self.model_combo.setCurrentText(saved_model)
            elif "qwen2.5:1.5b" in status.models:
                self.model_combo.setCurrentText("qwen2.5:1.5b")
        else:
            self.model_combo.addItem("(No local models)")
        self.model_combo.blockSignals(False)

        has_models = bool(status.available and status.models)
        self._set_inputs_enabled(has_models)

    def _set_inputs_enabled(self, enabled: bool) -> None:
        for w in (
            self.btn_summarize,
            self.btn_entities,
            self.btn_explain,
            self.question_input,
            self.btn_ask,
        ):
            w.setEnabled(enabled)

    def _on_model_changed(self, model_name: str) -> None:
        if model_name and not model_name.startswith("("):
            self.settings["ollama_model"] = model_name
            self.file_service.save_settings(self.settings)

    def _start_ai_task(self, label: str, fn) -> None:
        if self._session is None:
            self.transcript.append("<b>Notice:</b> Open a PDF document first.\n")
            return
        if self._worker is not None and self._worker.isRunning():
            return

        self._set_inputs_enabled(False)
        self.transcript.append(f"<b>You:</b> {label}")
        self.transcript.append("<i>Thinking locally via Ollama...</i>")
        self.status_message.emit("Running local Ollama inference...")

        self._worker = _AiWorkerThread(fn)
        self._worker.finished_ok.connect(self._on_ai_success)
        self._worker.failed.connect(self._on_ai_error)
        self._worker.start()

    def _on_ai_success(self, response: AssistantResponse) -> None:
        self._set_inputs_enabled(True)
        pages_note = (
            f" (Context scanned: Pages {', '.join(map(str, response.referenced_pages))})"
            if response.referenced_pages
            else ""
        )
        self.transcript.append(f"<b>PDF Pro AI{pages_note}:</b>\n{response.answer}\n")
        self.status_message.emit("Local AI response ready.")

    def _on_ai_error(self, err_msg: str) -> None:
        self._set_inputs_enabled(True)
        self.transcript.append(f"<b>Error:</b> {err_msg}\n")
        self.status_message.emit("Ollama error — see AI panel.")

    def _run_summarize(self) -> None:
        if self._session is None:
            return
        doc = self._session.doc
        page = self._session.current_page
        model = self.model_combo.currentText()
        self._start_ai_task(
            "Summarize this document",
            lambda: self.assistant.summarize_document(doc, model, current_page_0based=page),
        )

    def _run_entities(self) -> None:
        if self._session is None:
            return
        doc = self._session.doc
        page = self._session.current_page
        model = self.model_combo.currentText()
        self._start_ai_task(
            "Extract key dates and names",
            lambda: self.assistant.extract_entities(doc, model, current_page_0based=page),
        )

    def _run_explain_selection(self) -> None:
        if self._session is None:
            return
        snippet = self._selected_snippet
        page_1 = self._session.current_page + 1
        model = self.model_combo.currentText()
        self._start_ai_task(
            "Explain selected text",
            lambda: self.assistant.explain_selection(snippet, page_1, model),
        )

    def _run_question(self) -> None:
        q = self.question_input.text().strip()
        if not q or self._session is None:
            return
        self.question_input.clear()
        doc = self._session.doc
        page = self._session.current_page
        model = self.model_combo.currentText()
        self._start_ai_task(
            q,
            lambda: self.assistant.ask_question(doc, model, q, current_page_0based=page),
        )
