# PDF Pro - Local-First Windows PDF Suite

Offline Windows desktop application for reading, organizing, modifying, annotating, and querying PDFs locally via PyMuPDF, pypdf, PySide6, and optional Ollama.

## Run
1. python -m venv .venv
2. .\.venv\Scripts\Activate.ps1
3. pip install -r requirements.txt
4. python -m app.main

## Test
pytest -v

## Package
pyinstaller --noconfirm --windowed --name PDFPro --paths . app/main.py
