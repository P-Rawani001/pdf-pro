<div align="center">

# 📄 PDF Pro

### A local-first, offline PDF suite for Windows

Read, organize, modify, annotate, and **chat with your PDFs** — entirely on your own machine.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](#requirements)
[![UI](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)
[![Tests](https://img.shields.io/badge/Tests-pytest-0A9EDC?logo=pytest&logoColor=white)](#testing)
[![License](https://img.shields.io/github/license/P-Rawani001/pdf-pro)](LICENSE)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline-success)](#privacy--security)

[Features](#-features) • [Quick Start](#-quick-start) • [AI Assistant](#-optional-local-ai-with-ollama) • [Testing](#-testing) • [Packaging](#-packaging-a-windows-executable) • [Roadmap](#-roadmap) • [Contributing](#-contributing)

</div>

---

## Overview

**PDF Pro** is a desktop application that brings everyday PDF workflows into one fast, private tool. There are no accounts, no uploads, and no subscriptions. Your documents never leave your computer.

It is built on proven libraries — [PyMuPDF](https://pymupdf.readthedocs.io/) for rendering and editing, [pypdf](https://pypdf.readthedocs.io/) for document structure operations, and [PySide6](https://doc.qt.io/qtforpython-6/) for a native desktop interface. An optional integration with [Ollama](https://ollama.com/) lets you query your documents with a locally running language model, so even the AI features stay offline.

> **Why PDF Pro?**
> Most PDF tools are either paid, cloud-based, or both. PDF Pro keeps sensitive documents — contracts, medical records, research papers, financial statements — on your machine.

---

## ✨ Features

| Capability | Description |
|---|---|
| 📖 **Read** | Fast, accurate PDF rendering powered by PyMuPDF |
| 🗂️ **Organize** | Manage and restructure document pages |
| ✏️ **Modify** | Edit PDF documents locally with pypdf and PyMuPDF |
| 🖍️ **Annotate** | Mark up documents with annotations |
| 🤖 **Query** | Ask questions about your PDFs using a local LLM via Ollama *(optional)* |
| 🔒 **Local-first** | Works fully offline; no data leaves your device |

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Language | Python |
| GUI | PySide6 (Qt for Python) |
| PDF rendering & editing | PyMuPDF |
| PDF structure operations | pypdf |
| Local AI *(optional)* | Ollama |
| Testing | pytest |
| Packaging | PyInstaller |

---

## 📋 Requirements

- **OS:** Windows 10 or later
- **Python:** 3.10+ recommended
- **Optional:** [Ollama](https://ollama.com/download) for the AI document-query features

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/P-Rawani001/pdf-pro.git
cd pdf-pro
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> If PowerShell blocks script execution, run this once in the current session:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Launch the app

```powershell
python -m app.main
```

---

## 🤖 Optional: Local AI with Ollama

PDF Pro can use a locally hosted language model to answer questions about your documents. Nothing is sent to external servers.

1. Install Ollama from [ollama.com/download](https://ollama.com/download).
2. Pull a model, for example:
   ```bash
   ollama pull llama3
   ```
3. Make sure the Ollama service is running (it listens on `http://localhost:11434` by default).
4. Launch PDF Pro and use the document-query feature.

> The app works fully without Ollama; only the AI query features require it.

---

## 🧪 Testing

Run the full test suite from the project root with the virtual environment active:

```bash
pytest -v
```

---

## 📦 Packaging a Windows Executable

Build a standalone, windowed `.exe` with PyInstaller:

```powershell
pyinstaller --noconfirm --windowed --name PDFPro --paths . app/main.py
```

The output is written to `dist/PDFPro/`. Distribute that folder, or wrap it in an installer such as [Inno Setup](https://jrsoftware.org/isinfo.php).

---

## 🗂️ Project Structure

```text
pdf-pro/
├── app/                 # Application source (entry point: app/main.py)
├── tests/               # pytest test suite
├── requirements.txt     # Python dependencies
├── LICENSE              # License terms
└── README.md
```

---

## 🔐 Privacy & Security

- **No cloud processing.** All PDF operations run locally.
- **No telemetry.** The app does not phone home.
- **Offline AI.** When Ollama is used, inference runs on your own hardware.
- **Your files stay yours.** Documents are processed in place and never uploaded.

> Found a security issue? Please open a private report via the repository's **Security** tab rather than a public issue.

---

## 🛣️ Roadmap

- [ ] Screenshots and demo GIF in this README
- [ ] Prebuilt Windows installer via GitHub Releases
- [ ] Continuous integration with GitHub Actions (lint + tests)
- [ ] Merge, split, and reorder workflows with drag-and-drop
- [ ] OCR support for scanned documents
- [ ] Configurable Ollama model selection in the UI
- [ ] Dark / light theme toggle

*Items above are suggestions; adjust to match your actual plans.*

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are welcome.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and add tests under `tests/`
4. Run `pytest -v` and make sure everything passes
5. Commit with a clear message: `git commit -m "Add your feature"`
6. Push and open a Pull Request

Please open an [issue](https://github.com/P-Rawani001/pdf-pro/issues) first for larger changes so we can discuss the approach.

---

## 📜 License

Distributed under the terms of the license in the [LICENSE](LICENSE) file.

---

## 🙏 Acknowledgements

- [PyMuPDF](https://pymupdf.readthedocs.io/) — PDF rendering and manipulation
- [pypdf](https://pypdf.readthedocs.io/) — PDF structure operations
- [PySide6 / Qt](https://doc.qt.io/qtforpython-6/) — desktop UI framework
- [Ollama](https://ollama.com/) — local LLM runtime
- [PyInstaller](https://pyinstaller.org/) — Windows packaging

---

<div align="center">

**Built by [@P-Rawani001](https://github.com/P-Rawani001)**

⭐ If you find this project useful, consider giving it a star!

</div>
