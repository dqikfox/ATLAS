# ATLAS

ATLAS is an AI-powered **computer-using agent** that can see your screen,
move the mouse, type, run commands, and complete complex multi-step tasks –
all orchestrated by a large language model.

## Architecture

```
ATLAS
├── atlas/
│   ├── agent.py          # LangChain tool-calling agent
│   ├── config.py         # Config (model provider, keys, safety settings)
│   ├── models/
│   │   └── factory.py    # OpenAI / Ollama model factory
│   ├── tools/
│   │   ├── computer.py   # PyAutoGUI computer-control tools
│   │   └── mcp_client.py # MCP client – load tools from an MCP server
│   └── mcp/
│       └── server.py     # Native MCP server (exposes ATLAS tools)
└── main.py               # CLI entry point
```

### Key integrations

| Component | Role |
|-----------|------|
| **LangChain** | Agent orchestration, tool routing, prompt management |
| **OpenAI** | Default LLM (GPT-4o) |
| **Ollama** | Optional local LLM (llama3.2, mistral, …) |
| **PyAutoGUI** | Computer control – screenshot, click, type, scroll, hotkeys |
| **MCP (native server)** | Exposes ATLAS tools as an MCP server (stdio transport) |
| **MCP (client)** | Connects to external MCP servers and adds their tools to the agent |

---

## Getting Started

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

At a minimum set your **OpenAI API key** (or configure Ollama – see below):

```
OPENAI_API_KEY=sk-...
```

### 3. Run ATLAS

**Interactive shell** (default):

```bash
python main.py
```

**Single task**:

```bash
python main.py --task "Open a terminal and print the current date"
```

**Verbose mode** (shows LangChain reasoning steps):

```bash
python main.py --verbose
```

---

## Switching model providers

ATLAS defaults to **OpenAI** (`gpt-4o`). Switch to Ollama with environment
variables or the `--provider` / `--model` flags:

### Via environment variables

```bash
# .env
ATLAS_MODEL_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

### Via CLI flags

```bash
python main.py --provider ollama --model llama3.2
python main.py --provider openai  --model gpt-4-turbo
```

### Supported providers

| Provider | `ATLAS_MODEL_PROVIDER` | Required env var |
|----------|------------------------|-----------------|
| OpenAI   | `openai` (default)     | `OPENAI_API_KEY` |
| Ollama   | `ollama`               | Ollama running at `OLLAMA_BASE_URL` |

---

## MCP integration

### Run ATLAS as an MCP server

Expose ATLAS computer-control tools to any MCP-compatible client (e.g. VS
Code GitHub Copilot, Claude Desktop):

```bash
python main.py --mcp-server
```

This starts an **stdio MCP server**. Add it to your MCP client config:

```json
{
  "mcpServers": {
    "atlas": {
      "command": "python",
      "args": ["main.py", "--mcp-server"]
    }
  }
}
```

### Connect ATLAS to an external MCP server

Load tools from a running MCP server and make them available to the agent:

```bash
python main.py --mcp-client ws://localhost:8765
```

---

## Computer-control tools

| Tool | Description |
|------|-------------|
| `take_screenshot` | Capture the screen as base64 PNG |
| `move_mouse` | Move cursor to (x, y) |
| `click` | Left / right / middle click at (x, y) |
| `double_click` | Double-click at (x, y) |
| `scroll` | Scroll up/down at (x, y) |
| `type_text` | Type a string at the cursor |
| `press_key` | Press a key (enter, escape, tab, …) |
| `hotkey` | Press a keyboard shortcut (ctrl+c, …) |
| `run_shell_command` | Execute a shell command |
| `get_screen_size` | Return screen resolution |

---

## Safety

- **`ATLAS_SAFE_MODE=true`** (default) – the agent confirms before destructive
  actions.
- **`PYAUTOGUI_PAUSE`** – injects a configurable delay between GUI actions
  (default 0.5 s) to prevent runaway automation.
- **PyAutoGUI FAILSAFE** – move the mouse to the top-left corner of the screen
  at any time to immediately abort the agent.

---

## Docker

Build and run ATLAS in a container:

```bash
docker build -t atlas .
docker run --env-file .env atlas
```

See `deployment/README.md` for more details.

---

## Development

```bash
# Quick smoke test (no OpenAI key required)
python -c "from atlas.config import load_config; print(load_config())"
```

Pull requests are welcome!
