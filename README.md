# ATLAS – AI Assistant

ATLAS is a Python-based AI assistant with a full-featured **web UI** for chatting with local or API-backed language models.  It ships with built-in tools (file system, OCR, shell execution) accessible through a clean dark-themed interface with voice input/output support.

## Features

| Capability | Details |
|---|---|
| 💬 **Chat** | Streams responses from any llama.cpp model or OpenAI-compatible API (Ollama, LM Studio, etc.) |
| 🔍 **OCR** | Drag-and-drop image → extracted text via pytesseract / easyocr, insertable into chat |
| 📁 **File browser** | Browse, read, and write files within a sandboxed root directory |
| 🎤 **Voice input (STT)** | Browser Web Speech API (Chrome/Edge) or server-side Whisper transcription |
| 🔊 **Voice output (TTS)** | Browser `speechSynthesis` API; falls back to pyttsx3 / gTTS on the server |
| ⚙ **Tools / MCP** | Tool registry that the model can call (fs_list, fs_read, fs_write, shell_run, python_eval, ocr_extract) |
| 🖥 **Shell / Code eval** | Model can run shell commands and evaluate Python snippets with built-in safety guard-list |

## Quick start

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Start the web server

```bash
python web/app.py
```

Then open **http://localhost:5000** in your browser.

> Optional environment variables:
> | Variable | Default | Description |
> |---|---|---|
> | `ATLAS_PORT` | `5000` | Port the server listens on |
> | `ATLAS_DEBUG` | `0` | Set to `1` for Flask debug mode |
> | `ATLAS_SECRET_KEY` | random | Flask session secret key |
> | `ATLAS_SHELL_UNRESTRICTED` | `0` | Set to `1` to disable shell command block-list |

### Configure the model backend

Edit `ultron_config.json`.  The file is base64-encoded JSON:

**Local llama.cpp model** (default):
```json
{
  "offline_mode": true,
  "models": {
    "llm": { "type": "llama_cpp", "path": "models/llama-7b.Q4_K_M.gguf" },
    "stt": { "type": "whisper", "model": "base" }
  }
}
```

**OpenAI-compatible API (e.g. Ollama)**:
```json
{
  "offline_mode": false,
  "models": {
    "llm": {
      "type": "openai_compatible",
      "base_url": "http://localhost:11434/v1",
      "model": "llama3",
      "api_key": "ollama"
    },
    "stt": { "type": "whisper", "model": "base" }
  }
}
```

Re-encode with:
```bash
python3 -c "import base64, json, pathlib; \
  cfg = json.load(open('my_config.json')); \
  pathlib.Path('ultron_config.json').write_text(base64.b64encode(json.dumps(cfg).encode()).decode())"
```

## UI Layout

```
┌──────────────────────────────────────────────────────┐
│  ☰  [ATLAS]  8 tools ready        [🗑 Clear] [⊞]    │  ← Topbar
├─────────────┬───────────────────────────┬────────────┤
│  📁 Files   │                           │  🔍 OCR    │
│  ⚙ Tools   │   Chat messages           │  ⚙ Config  │
│             │                           │            │
│  [sidebar]  │   ┌─ bot bubble ──────┐   │  [panels]  │
│             │   │ Hello! I'm ATLAS… │   │            │
│  fs browser │   └───────────────────┘   │  drop zone │
│  tool cards │                           │  OCR text  │
│             │   [📎] [textarea] [🎤][➤] │            │
└─────────────┴───────────────────────────┴────────────┘
```

## REST API

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Web UI |
| `POST` | `/api/chat` | Chat (supports tool calls) |
| `GET` | `/api/chat/stream` | SSE streaming chat |
| `POST` | `/api/ocr` | OCR image → text |
| `GET` | `/api/fs/list?path=…` | List directory |
| `GET` | `/api/fs/read?path=…` | Read file |
| `POST` | `/api/fs/write` | Write file |
| `POST` | `/api/stt` | Speech-to-text (audio file) |
| `POST` | `/api/tts` | Text-to-speech |
| `GET` | `/api/tools` | List available tools |
| `POST` | `/api/tools/call` | Call a tool by name |

## Project structure

```
web/
  app.py               Flask application
  templates/index.html Chat UI
  static/css/style.css Dark-themed stylesheet
  static/js/app.js     Frontend JavaScript

ultron/
  ai/offline.py        Local model loader (llama.cpp / Whisper)
  config.py            Config loader
  tts.py               Server-side TTS helper
  tools/
    __init__.py        MCP-style tool registry
    fs.py              File-system tools
    ocr.py             OCR tool
    shell.py           Shell / Python execution tool

tests/
  test_web_ui.py       Test suite for web UI + tools

requirements.txt       Python dependencies
ultron_config.json     Base64-encoded model configuration
```

## Running tests

```bash
pip install pytest
pytest tests/ -v
```

## Docker

```bash
docker build -t atlas .
docker run -p 5000:5000 atlas
```

## Contributing

Pull requests are welcome! If you find issues or have suggestions for improvements, feel free to open an issue or submit a pull request.
