"""ATLAS Web UI – Flask application.

Endpoints
---------
GET  /                  – Serve the chat UI
POST /api/chat          – Chat with the LLM (supports tool calls)
GET  /api/chat/stream   – SSE stream for a single chat turn
POST /api/ocr           – Extract text from an uploaded image
GET  /api/fs/list       – List directory contents
GET  /api/fs/read       – Read a file
POST /api/fs/write      – Write a file
POST /api/stt           – Transcribe an uploaded audio file (Whisper)
POST /api/tts           – Synthesise speech from text
GET  /api/tools         – List registered tools
POST /api/tools/call    – Call a tool by name
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

# Allow ``from ultron import …`` when running the app directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from ultron.config import load_config
from ultron.tools import ToolRegistry
from ultron.tools.fs import register_fs_tools
from ultron.tools.ocr import register_ocr_tools
from ultron.tools.shell import register_shell_tools

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("ATLAS_SECRET_KEY", os.urandom(32))

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

registry = ToolRegistry()
register_fs_tools(registry)
register_ocr_tools(registry)
register_shell_tools(registry)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_config: Dict[str, Any] = {}


def get_config() -> Dict[str, Any]:
    global _config
    if not _config:
        _config = load_config()
    return _config


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_BASE = (
    "You are ATLAS, an advanced AI assistant with access to tools.  "
    "Be concise, helpful, and honest.\n\n"
    "To call a tool respond with ONLY valid JSON on a single line:\n"
    '{"tool": "<tool_name>", "args": {<key>: <value>, ...}}\n\n'
    "Otherwise respond in plain text."
)


def _build_system_prompt() -> str:
    tools = registry.list_tools()
    if not tools:
        return _SYSTEM_PROMPT_BASE
    desc = registry.get_tools_description()
    return _SYSTEM_PROMPT_BASE + f"\n\nAvailable tools:\n{desc}"


def _llm_complete(messages: List[Dict[str, Any]], stream: bool = False) -> Any:
    """Send *messages* to the configured LLM and return the response."""
    cfg = get_config()
    llm_cfg = cfg.get("models", {}).get("llm", {})
    model_type = llm_cfg.get("type", "llama_cpp")

    if model_type == "openai_compatible":
        import openai  # type: ignore

        client = openai.OpenAI(
            base_url=llm_cfg.get("base_url", "http://localhost:11434/v1"),
            api_key=llm_cfg.get("api_key", "ollama"),
        )
        resp = client.chat.completions.create(
            model=llm_cfg.get("model", "llama3"),
            messages=messages,
            stream=stream,
        )
        if stream:
            return resp
        return resp.choices[0].message.content

    if model_type == "llama_cpp":
        from ultron.ai.offline import get_llm  # type: ignore

        llm = get_llm()
        if llm is None:
            return "[LLM not loaded.  Configure a model or start the preloader.]"

        # Format messages as a simple prompt string.
        prompt = _format_llama_prompt(messages)
        result = llm(prompt, max_tokens=llm_cfg.get("max_tokens", 512), stream=False)
        return result["choices"][0]["text"]

    return "[Unknown LLM type configured.]"


def _format_llama_prompt(messages: List[Dict[str, Any]]) -> str:
    prompt = ""
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            prompt += f"<|system|>\n{content}\n"
        elif role == "user":
            prompt += f"<|user|>\n{content}\n"
        elif role == "assistant":
            prompt += f"<|assistant|>\n{content}\n"
    prompt += "<|assistant|>\n"
    return prompt


def _run_tool_loop(messages: List[Dict[str, Any]], max_rounds: int = 5) -> Dict[str, Any]:
    """Run the LLM→tool→LLM loop and return the final reply + tool usage log."""
    used_tools: List[Dict[str, Any]] = []

    for _ in range(max_rounds):
        raw = _llm_complete(messages, stream=False)
        if not isinstance(raw, str):
            raw = str(raw)

        # Attempt to parse a tool call.
        tool_call: Optional[Dict[str, Any]] = None
        stripped = raw.strip()
        if stripped.startswith("{"):
            try:
                parsed = json.loads(stripped)
                if "tool" in parsed:
                    tool_call = parsed
            except json.JSONDecodeError:
                pass

        if tool_call is None:
            # Normal text reply – we're done.
            return {"content": raw, "tools_used": used_tools}

        # Execute the tool.
        tool_name = tool_call["tool"]
        tool_args = tool_call.get("args", {})
        try:
            result = registry.call_tool(tool_name, **tool_args)
            result_str = json.dumps(result) if not isinstance(result, str) else result
        except Exception as exc:
            result_str = f"Tool error: {exc}"

        used_tools.append({"tool": tool_name, "args": tool_args, "result": result_str})

        # Feed the result back into the conversation.
        messages = messages + [
            {"role": "assistant", "content": raw},
            {
                "role": "user",
                "content": f"[Tool result for {tool_name}]\n{result_str}",
            },
        ]

    # Max rounds reached – get a final answer.
    raw = _llm_complete(messages, stream=False)
    if not isinstance(raw, str):
        raw = str(raw)
    return {"content": raw, "tools_used": used_tools}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index() -> str:
    tools = registry.list_tools()
    return render_template("index.html", tools=tools)


@app.route("/api/chat", methods=["POST"])
def chat() -> Response:
    data = request.get_json(force=True)
    messages: List[Dict[str, Any]] = data.get("messages", [])
    use_tools: bool = data.get("use_tools", True)

    system_content = _build_system_prompt() if use_tools else _SYSTEM_PROMPT_BASE
    full_messages = [{"role": "system", "content": system_content}] + messages

    result = _run_tool_loop(full_messages)
    return jsonify(result)


@app.route("/api/chat/stream")
def chat_stream() -> Response:
    """SSE endpoint – streams a single LLM response token by token.

    Query parameters:
        messages – JSON-encoded list of message objects.
        use_tools – "true" / "false" (default: "true").
    """
    raw_messages = request.args.get("messages", "[]")
    use_tools = request.args.get("use_tools", "true").lower() != "false"

    try:
        messages: List[Dict[str, Any]] = json.loads(raw_messages)
    except json.JSONDecodeError:
        messages = []

    system_content = _build_system_prompt() if use_tools else _SYSTEM_PROMPT_BASE
    full_messages = [{"role": "system", "content": system_content}] + messages

    cfg = get_config()
    llm_cfg = cfg.get("models", {}).get("llm", {})

    def generate() -> Generator[str, None, None]:
        # Only openai_compatible supports real streaming; others fall back.
        if llm_cfg.get("type") == "openai_compatible":
            try:
                import openai  # type: ignore

                client = openai.OpenAI(
                    base_url=llm_cfg.get("base_url", "http://localhost:11434/v1"),
                    api_key=llm_cfg.get("api_key", "ollama"),
                )
                stream = client.chat.completions.create(
                    model=llm_cfg.get("model", "llama3"),
                    messages=full_messages,
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield f"data: {json.dumps({'content': delta})}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        else:
            # Non-streaming fallback.
            try:
                result = _run_tool_loop(full_messages)
                yield f"data: {json.dumps({'content': result['content'], 'tools_used': result['tools_used']})}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"

        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/ocr", methods=["POST"])
def ocr() -> Response:
    if "image" not in request.files:
        return jsonify({"error": "No image file provided (field name: 'image')"}), 400
    image_bytes = request.files["image"].read()
    try:
        text = registry.call_tool("ocr_extract", image_data=image_bytes)
        return jsonify({"text": text})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/fs/list")
def fs_list() -> Response:
    path = request.args.get("path", ".")
    try:
        result = registry.call_tool("fs_list", path=path)
        return jsonify(result)
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/fs/read")
def fs_read() -> Response:
    path = request.args.get("path", "")
    if not path:
        return jsonify({"error": "path query parameter is required"}), 400
    try:
        content = registry.call_tool("fs_read", path=path)
        return jsonify({"content": content})
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/fs/write", methods=["POST"])
def fs_write() -> Response:
    data = request.get_json(force=True)
    path: str = data.get("path", "")
    content: str = data.get("content", "")
    if not path:
        return jsonify({"error": "path is required"}), 400
    try:
        msg = registry.call_tool("fs_write", path=path, content=content)
        return jsonify({"message": msg})
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/stt", methods=["POST"])
def stt() -> Response:
    """Transcribe an uploaded audio file using Whisper."""
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided (field name: 'audio')"}), 400

    audio_bytes = request.files["audio"].read()
    suffix = Path(request.files["audio"].filename or "audio.wav").suffix or ".wav"

    try:
        import whisper  # type: ignore

        cfg = get_config()
        stt_cfg = cfg.get("models", {}).get("stt", {})
        model_name = stt_cfg.get("model", "base")

        from ultron.ai.offline import get_stt_model  # type: ignore

        model = get_stt_model()
        if model is None:
            model = whisper.load_model(model_name)

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            result = model.transcribe(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        return jsonify({"text": result["text"]})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/tts", methods=["POST"])
def tts() -> Response:
    """Synthesise speech from text.  Returns audio/mpeg or audio/wav bytes."""
    data = request.get_json(force=True)
    text: str = data.get("text", "")
    if not text:
        return jsonify({"error": "text is required"}), 400
    try:
        from ultron.tts import synthesize

        audio_bytes = synthesize(text)
        # Detect format by magic bytes.
        mime = "audio/mpeg" if audio_bytes[:3] == b"\xff\xfb" or audio_bytes[:2] == b"ID" else "audio/wav"
        return Response(audio_bytes, mimetype=mime)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/tools")
def list_tools() -> Response:
    return jsonify({"tools": registry.list_tools()})


@app.route("/api/tools/call", methods=["POST"])
def call_tool() -> Response:
    data = request.get_json(force=True)
    tool_name: str = data.get("tool", "")
    tool_args: Dict[str, Any] = data.get("args", {})
    if not tool_name:
        return jsonify({"error": "tool name is required"}), 400
    try:
        result = registry.call_tool(tool_name, **tool_args)
        return jsonify({"result": result})
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("ATLAS_PORT", 5000))
    debug = os.environ.get("ATLAS_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
