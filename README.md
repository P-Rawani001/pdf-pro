<div align="center">

# 📄 PDF Pro

### A local-first, offline PDF suite for Windows

Read, organize, modify, annotate, and **chat with your PDFs** — entirely on your own machine.

[![Download](https://img.shields.io/badge/Download-Windows%20(.zip)-0078D6?logo=windows&logoColor=white)](https://github.com/P-Rawani001/pdf-pro/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)
[![Tests](https://img.shields.io/badge/Tests-pytest-0A9EDC?logo=pytest&logoColor=white)](#-testing)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline-success)](#-privacy--security)

[Download](#-download-for-windows) • [Features](#-features) • [AI Assistant](#-ai-assistant-setup-optional) • [Run from Source](#-run-from-source) • [Testing](#-testing) • [Build](#-build-the-executable) • [License](#-license)

</div>

---

## Overview

**PDF Pro** is a desktop application that brings everyday PDF workflows into one fast, private tool. There are no accounts, no uploads, and no subscriptions. Your documents never leave your computer.

It is built on [PyMuPDF](https://pymupdf.readthedocs.io/) for rendering and editing, [pypdf](https://pypdf.readthedocs.io/) for document structure operations, and [PySide6](https://doc.qt.io/qtforpython-6/) for a native desktop interface. An optional [Ollama](https://ollama.com/) integration lets you ask questions about your documents using a locally running language model, so even the AI features stay offline.

---

## ⬇️ Download for Windows

**No Python. No installer. No extra libraries.**

1. Open the **[latest release](https://github.com/P-Rawani001/pdf-pro/releases/latest)** and download **`PDFPro.zip`**.
2. **Extract the whole ZIP** to any folder (right-click → *Extract All…*).
3. Open the extracted `PDFPro` folder and double-click **`PDFPro.exe`**.

> ⚠️ **Keep the folder together.** `PDFPro.exe` needs the `_internal` folder sitting next to it (it contains Python, Qt, PyMuPDF, and the app icon). Copying `PDFPro.exe` on its own will not work.
>
> ⚠️ **Extract first.** Don't launch the `.exe` from inside the ZIP preview.

**System requirements:** Windows 10 or Windows 11 (64-bit).

### Windows SmartScreen warning

The executable is not signed with a paid code-signing certificate, so Windows may show a blue **"Windows protected your PC"** window the first time you run it. This is expected for unsigned apps.

Click **More info → Run anyway**.

You can verify your download against the published checksum before running it:

```powershell
Get-FileHash .\PDFPro.zip -Algorithm SHA256
```

```text
SHA-256: 13838d5bb1da934b0451d4e2d6469651f534bacdbc5a544862e5811835cd585b
```

> Re-generate this checksum whenever you rebuild and re-upload the ZIP.

---

## ✨ Features

### Works immediately after extracting the ZIP (fully offline)

| Category | What you can do |
|---|---|
| 📖 **Reader & Viewer** | Multiple tabs, thumbnails, zoom, text search, text copy |
| 🗂️ **Page Organization** | Merge, split, rotate, reorder, delete, and extract pages |
| 🛠️ **PDF Utilities** | Compress, watermark, edit metadata, Images ↔ PDF conversion |
| 🖍️ **Annotations** | Highlight, underline, strike-through, sticky notes, text boxes, shapes |

### Requires one extra step

| Feature | Requirement |
|---|---|
| 🤖 **AI Assistant** (chat with your PDF) | [Ollama](https://ollama.com/) installed and running, with a model pulled. See [setup](#-ai-assistant-setup-optional) below. |

If Ollama isn't installed or running, the AI panel simply reports that Ollama isn't available. **Every other tool keeps working normally.**

---

## 🤖 AI Assistant Setup (Optional)

The AI Assistant uses a language model running **on your own computer** through Ollama. Nothing is sent to any server.

### Step-by-step

1. **Install Ollama** for Windows from [ollama.com/download](https://ollama.com/download).
2. **Open a terminal** (PowerShell or Command Prompt) and download a model. A small, fast model that runs on most laptops:
   ```bash
   ollama pull qwen2.5:1.5b
   ```
3. **Make sure Ollama is running.** It normally starts automatically after installation and sits in the system tray. You can verify with:
   ```bash
   ollama list
   ```
   Ollama listens on `http://localhost:11434` by default.
4. **Launch PDF Pro**, open a PDF, and use the AI Assistant panel.

### Troubleshooting

| Problem | Fix |
|---|---|
| Panel says *"Ollama isn't running"* | Start Ollama from the Start menu, then reopen the panel or restart PDF Pro |
| Model not found | Run `ollama pull qwen2.5:1.5b` (or the model name PDF Pro is configured to use) |
| Responses are slow | Use a smaller model, close other heavy apps, or try a machine with more RAM |

> Larger models give better answers but need more RAM and are slower on machines without a GPU.

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
| Packaging | PyInstaller (`--onedir`) |

---

## 🧑‍💻 Run from Source

**Requirements:** Windows 10/11, Python 3.10+

```powershell
git clone https://github.com/P-Rawani001/pdf-pro.git
cd pdf-pro

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python -m app.main
```

> If PowerShell blocks script execution, run this once in the current session:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

---

## 🧪 Testing

```bash
pytest -v
```

---

## 📦 Build the Executable

```powershell
pyinstaller --noconfirm --windowed --name PDFPro --paths . app/main.py
```

The output is created in `dist\PDFPro\`. To share it, **zip the entire `PDFPro` folder** (not just the `.exe`) and publish it as a [GitHub Release](https://github.com/P-Rawani001/pdf-pro/releases) asset.

---

## 🗂️ Project Structure

```text
pdf-pro/
├── app/                 # Application source (entry point: app/main.py)
├── tests/               # pytest test suite
├── requirements.txt     # Python dependencies
├── LICENSE              # GNU AGPL-3.0
└── README.md
```

---

## 🔐 Privacy & Security

- **No cloud processing.** All PDF operations run locally.
- **No accounts, no telemetry.**
- **Offline AI.** When Ollama is used, inference runs on your own hardware.
- **Your files stay yours.** Documents are processed on your machine and never uploaded.

> Found a security issue? Please report it privately via the repository's **Security** tab instead of opening a public issue.

---

## ❓ FAQ

**Can I send just `PDFPro.exe` to a friend?**
No. Send the whole `PDFPro` folder as a ZIP, or point them to the [Releases page](https://github.com/P-Rawani001/pdf-pro/releases/latest).

**Does the other person need Python or any libraries?**
No. Everything is bundled. Only the AI Assistant needs Ollama.

**Why does Windows warn me when I open it?**
The app isn't code-signed. Click *More info → Run anyway*. You can verify the download with the SHA-256 checksum above.

**Does it work on macOS or Linux?**
The packaged app targets Windows 10/11 (64-bit). Running from source on other platforms is untested.

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are welcome.

1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature`
3. Make your changes and add tests under `tests/`
4. Run `pytest -v` and make sure everything passes
5. Commit and open a Pull Request

For larger changes, please open an [issue](https://github.com/P-Rawani001/pdf-pro/issues) first.

---

## 📜 License

PDF Pro is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. See [LICENSE](LICENSE).

This is required because the app bundles [PyMuPDF](https://pymupdf.readthedocs.io/), which is itself AGPL-3.0. If you distribute a compiled build of PDF Pro, you must also make the corresponding source code available under the same license. The source for this project is at [github.com/P-Rawani001/pdf-pro](https://github.com/P-Rawani001/pdf-pro).

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

⭐ If you find this useful, consider giving it a star!

</div>
