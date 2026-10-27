/* ──────────────────────────────────────────────────────────────────────────
   ATLAS Web UI – Frontend JavaScript
   ─────────────────────────────────────────────────────────────────────────*/
"use strict";

// ── State ────────────────────────────────────────────────────────────────────
const state = {
  messages: [],          // {role, content} objects sent to /api/chat
  useTools: true,
  voiceEnabled: false,   // TTS readout
  isRecording: false,
  mediaRecorder: null,
  audioChunks: [],
  currentFsPath: ".",
  settings: loadSettings(),
};

function loadSettings() {
  try {
    return JSON.parse(localStorage.getItem("atlas_settings") || "{}");
  } catch {
    return {};
  }
}

function saveSettings() {
  localStorage.setItem("atlas_settings", JSON.stringify(state.settings));
}

// ── DOM refs ─────────────────────────────────────────────────────────────────
/** @param {string} id - Element ID to look up @returns {HTMLElement} */
const $ = (id) => document.getElementById(id);

const chatMessages  = $("chat-messages");
const msgInput      = $("msg-input");
const sendBtn       = $("send-btn");
const voiceBtn      = $("voice-btn");
const attachBtn     = $("attach-btn");
const attachInput   = $("attach-input");
const sidebarEl     = $("sidebar");
const rightPanel    = $("right-panel");
const toolsToggle   = $("tools-toggle");
const voiceToggle   = $("voice-toggle");
const modelBadge    = $("model-badge");
const fsPathInput   = $("fs-path-input");
const fsList        = $("fs-list");
const ocrDropZone   = $("ocr-drop-zone");
const ocrPreview    = $("ocr-preview");
const ocrResultBox  = $("ocr-result-box");
const ocrRunBtn     = $("ocr-run-btn");
const ocrInsertBtn  = $("ocr-insert-btn");
const modalOverlay  = $("modal-overlay");
const modalTitle    = $("modal-title");
const modalBody     = $("modal-body");
const modalClose    = $("modal-close");
const clearChatBtn  = $("clear-chat-btn");
const settingsSave  = $("settings-save");

// ── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  applySettings();
  loadFs(".");
  setupEventListeners();
  addBotMessage("👋 Hello! I'm **ATLAS** – your AI assistant.\n\nI have access to file-system tools, OCR, shell execution, and more. How can I help?");
  fetchTools();
});

// ── Event listeners ───────────────────────────────────────────────────────────
function setupEventListeners() {
  // Send
  sendBtn.addEventListener("click", handleSend);
  msgInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  });
  msgInput.addEventListener("input", () => {
    msgInput.style.height = "auto";
    msgInput.style.height = Math.min(msgInput.scrollHeight, 180) + "px";
  });

  // Voice record
  voiceBtn.addEventListener("click", toggleRecording);

  // File attach (for OCR or FS)
  attachBtn.addEventListener("click", () => attachInput.click());
  attachInput.addEventListener("change", handleAttach);

  // Sidebar tabs
  document.querySelectorAll(".sidebar-tab").forEach((tabElement) => {
    tabElement.addEventListener("click", () => switchSidebarTab(tabElement.dataset.tab));
  });

  // Right panel tabs
  document.querySelectorAll(".right-tab").forEach((tabElement) => {
    tabElement.addEventListener("click", () => switchRightTab(tabElement.dataset.tab));
  });

  // Sidebar / right panel toggle
  $("sidebar-toggle").addEventListener("click", () => sidebarEl.classList.toggle("collapsed"));
  $("right-toggle").addEventListener("click", () => rightPanel.classList.toggle("hidden"));

  // FS navigation
  $("fs-go-btn").addEventListener("click", () => loadFs(fsPathInput.value.trim() || "."));
  fsPathInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") loadFs(fsPathInput.value.trim() || ".");
  });

  // OCR
  setupOcrDrop();
  ocrRunBtn.addEventListener("click", runOcr);
  ocrInsertBtn.addEventListener("click", () => {
    const text = ocrResultBox.textContent.trim();
    if (text) insertIntoInput("[OCR Result]\n" + text);
  });

  // Toggles
  toolsToggle.addEventListener("change", () => { state.useTools = toolsToggle.checked; });
  voiceToggle.addEventListener("change", () => { state.voiceEnabled = voiceToggle.checked; });

  // Clear chat
  clearChatBtn.addEventListener("click", () => {
    state.messages = [];
    chatMessages.innerHTML = "";
    addBotMessage("Chat cleared. How can I help?");
  });

  // Modal
  modalClose.addEventListener("click", closeModal);
  modalOverlay.addEventListener("click", (e) => { if (e.target === modalOverlay) closeModal(); });

  // Settings save
  settingsSave.addEventListener("click", () => {
    state.settings.modelType   = $("setting-model-type").value;
    state.settings.baseUrl     = $("setting-base-url").value.trim();
    state.settings.modelName   = $("setting-model-name").value.trim();
    state.settings.apiKey      = $("setting-api-key").value.trim();
    saveSettings();
    showToast("Settings saved (apply via /api/config – restart to take effect)");
  });
}

// ── Chat ──────────────────────────────────────────────────────────────────────
async function handleSend() {
  const text = msgInput.value.trim();
  if (!text) return;

  addUserMessage(text);
  state.messages.push({ role: "user", content: text });
  msgInput.value = "";
  msgInput.style.height = "auto";

  const typingId = addTyping();
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: state.messages, use_tools: state.useTools }),
    });
    const data = await res.json();
    removeTyping(typingId);

    if (data.error) {
      addBotMessage(`⚠️ Error: ${data.error}`, "error");
      return;
    }

    const reply = data.content || "";
    state.messages.push({ role: "assistant", content: reply });
    addBotMessage(reply, null, data.tools_used || []);

    if (state.voiceEnabled && reply) {
      speakText(reply);
    }
  } catch (err) {
    removeTyping(typingId);
    addBotMessage(`⚠️ Network error: ${err.message}`, "error");
  }
}

// ── Message rendering ─────────────────────────────────────────────────────────
function addUserMessage(text) {
  const row = createMessageRow("user", text);
  chatMessages.appendChild(row);
  scrollToBottom();
}

function addBotMessage(text, cls, toolsUsed) {
  const row = createMessageRow("bot", text, toolsUsed);
  if (cls) row.querySelector(".bubble").classList.add(cls);
  chatMessages.appendChild(row);
  scrollToBottom();
}

function createMessageRow(role, text, toolsUsed) {
  const row = document.createElement("div");
  row.className = "message-row";

  const avatar = document.createElement("div");
  avatar.className = `avatar ${role}-avatar`;
  avatar.textContent = role === "user" ? "U" : "A";

  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}-bubble`;
  bubble.innerHTML = renderMarkdown(text);

  if (toolsUsed && toolsUsed.length > 0) {
    const toolsDiv = document.createElement("div");
    toolsDiv.style.marginTop = "8px";
    toolsUsed.forEach((t) => {
      const badge = document.createElement("span");
      badge.className = "tool-badge";
      badge.textContent = `⚙ ${t.tool}`;
      badge.title = JSON.stringify(t.args, null, 2);
      toolsDiv.appendChild(badge);
    });
    bubble.appendChild(toolsDiv);
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  return row;
}

function addTyping() {
  const id = "typing-" + Date.now();
  const row = document.createElement("div");
  row.className = "message-row";
  row.id = id;

  const avatar = document.createElement("div");
  avatar.className = "avatar bot-avatar";
  avatar.textContent = "A";

  const bubble = document.createElement("div");
  bubble.className = "bubble bot-bubble";
  bubble.innerHTML = '<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>';

  row.appendChild(avatar);
  row.appendChild(bubble);
  chatMessages.appendChild(row);
  scrollToBottom();
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ── Minimal Markdown renderer ──────────────────────────────────────────────────
function renderMarkdown(text) {
  if (!text) return "";
  // Escape HTML first
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Code blocks
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code class="language-${lang}">${code}</code></pre>`;
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Italic
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

  // Headers
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm,  "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm,   "<h1>$1</h1>");

  // Lists
  html = html.replace(/^\- (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);

  // Newlines
  html = html.replace(/\n/g, "<br>");

  return html;
}

// ── Voice input (STT) ─────────────────────────────────────────────────────────
async function toggleRecording() {
  if (state.isRecording) {
    stopRecording();
    return;
  }

  // Try browser Web Speech API first
  if ("SpeechRecognition" in window || "webkitSpeechRecognition" in window) {
    startBrowserSTT();
  } else {
    // Fall back to MediaRecorder + server-side Whisper
    startMediaRecorder();
  }
}

function startBrowserSTT() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SR();
  recognition.lang = "en-US";
  recognition.interimResults = false;

  recognition.onstart = () => {
    state.isRecording = true;
    voiceBtn.classList.add("recording");
    voiceBtn.title = "Listening… click to stop";
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    insertIntoInput(transcript);
  };

  recognition.onerror = (e) => {
    showToast("Speech recognition error: " + e.error);
  };

  recognition.onend = () => {
    state.isRecording = false;
    voiceBtn.classList.remove("recording");
    voiceBtn.title = "Voice input";
  };

  state._recognition = recognition;
  recognition.start();
}

function stopRecording() {
  if (state._recognition) {
    state._recognition.stop();
    state._recognition = null;
  }
  if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
    state.mediaRecorder.stop();
  }
  state.isRecording = false;
  voiceBtn.classList.remove("recording");
}

async function startMediaRecorder() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.audioChunks = [];
    state.mediaRecorder = new MediaRecorder(stream);

    state.mediaRecorder.ondataavailable = (e) => state.audioChunks.push(e.data);
    state.mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(state.audioChunks, { type: "audio/webm" });
      await transcribeAudio(blob);
    };

    state.mediaRecorder.start();
    state.isRecording = true;
    voiceBtn.classList.add("recording");
    voiceBtn.title = "Recording… click to stop";
  } catch (err) {
    showToast("Microphone access denied: " + err.message);
  }
}

async function transcribeAudio(blob) {
  const form = new FormData();
  form.append("audio", blob, "recording.webm");
  try {
    const res = await fetch("/api/stt", { method: "POST", body: form });
    const data = await res.json();
    if (data.text) insertIntoInput(data.text);
    else showToast("STT error: " + (data.error || "Unknown error"));
  } catch (err) {
    showToast("STT request failed: " + err.message);
  }
}

// ── Voice output (TTS) ────────────────────────────────────────────────────────
function speakText(text) {
  // Strip markdown characters, then use DOMParser to safely extract plain text
  // (avoids regex-based HTML sanitization which can leave partial tags intact).
  const noMarkdown = text.replace(/[*_`#\[\]]/g, "");
  const doc = new DOMParser().parseFromString(noMarkdown, "text/html");
  const plain = doc.body.textContent || "";

  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(plain);
    utt.lang = "en-US";
    utt.rate = 1.05;
    window.speechSynthesis.speak(utt);
  } else {
    // Server-side TTS fallback
    fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: plain }),
    })
      .then((ttsResponse) => ttsResponse.blob())
      .then((audioBlob) => {
        const url = URL.createObjectURL(audioBlob);
        const audio = new Audio(url);
        audio.onended = () => URL.revokeObjectURL(url);
        audio.play();
      })
      .catch(() => {});
  }
}

// ── File attachment / OCR trigger ─────────────────────────────────────────────
function handleAttach(e) {
  const file = e.target.files[0];
  if (!file) return;
  if (file.type.startsWith("image/")) {
    // Auto-open OCR panel
    switchRightTab("ocr");
    loadImageIntoOcr(file);
    rightPanel.classList.remove("hidden");
  } else {
    // For non-images read as text and insert path into input
    insertIntoInput(`[Attached: ${file.name}]`);
  }
  // Reset input so same file can be selected again
  e.target.value = "";
}

// ── File System panel ─────────────────────────────────────────────────────────
async function loadFs(path) {
  fsPathInput.value = path;
  state.currentFsPath = path;
  fsList.innerHTML = "<div class='muted' style='padding:10px'>Loading…</div>";
  try {
    const res = await fetch("/api/fs/list?path=" + encodeURIComponent(path));
    const data = await res.json();
    if (data.error) {
      fsList.innerHTML = `<div class='error-text' style='padding:10px'>${data.error}</div>`;
      return;
    }
    renderFsList(data.entries || [], data.path || path);
  } catch (err) {
    fsList.innerHTML = `<div class='error-text' style='padding:10px'>Network error</div>`;
  }
}

function renderFsList(entries, currentPath) {
  fsList.innerHTML = "";

  // Back button if not root
  if (currentPath !== "/" && state.currentFsPath !== ".") {
    const back = makeFsEntry("📁", "..", true);
    back.addEventListener("click", () => {
      const parent = currentPath.split("/").slice(0, -1).join("/") || "/";
      loadFs(parent);
    });
    fsList.appendChild(back);
  }

  entries.forEach((entry) => {
    const icon = entry.type === "directory" ? "📁" : getFileIcon(entry.name);
    const el = makeFsEntry(icon, entry.name, entry.type === "directory", entry.size);
    if (entry.type === "directory") {
      el.addEventListener("click", () => loadFs(`${currentPath}/${entry.name}`.replace("//", "/")));
    } else {
      el.addEventListener("click", () => openFileModal(currentPath, entry.name));
    }
    fsList.appendChild(el);
  });

  if (entries.length === 0) {
    fsList.innerHTML = "<div class='muted' style='padding:10px'>Empty directory</div>";
  }
}

function makeFsEntry(icon, name, isDir, size) {
  const el = document.createElement("div");
  el.className = "fs-entry" + (isDir ? " is-dir" : "");
  el.innerHTML = `
    <span class="fs-icon">${icon}</span>
    <span class="fs-name">${escapeHtml(name)}</span>
    ${size != null ? `<span class="fs-size">${formatSize(size)}</span>` : ""}
  `;
  return el;
}

async function openFileModal(dir, filename) {
  const path = `${dir}/${filename}`.replace("//", "/");
  openModal(`📄 ${filename}`, "<div class='muted'>Loading…</div>");

  const res = await fetch("/api/fs/read?path=" + encodeURIComponent(path));
  const data = await res.json();

  if (data.error) {
    modalBody.innerHTML = `<div class='error-text'>${data.error}</div>`;
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = data.content;
  textarea.rows = 20;

  const actions = document.createElement("div");
  actions.className = "modal-actions";

  const insertBtn = document.createElement("button");
  insertBtn.className = "panel-btn";
  insertBtn.textContent = "Insert into chat";
  insertBtn.addEventListener("click", () => {
    insertIntoInput(`[File: ${path}]\n${textarea.value}`);
    closeModal();
  });

  const saveBtn = document.createElement("button");
  saveBtn.className = "panel-btn primary";
  saveBtn.textContent = "Save";
  saveBtn.addEventListener("click", async () => {
    const saveResponse = await fetch("/api/fs/write", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, content: textarea.value }),
    });
    const saveResponseData = await saveResponse.json();
    showToast(saveResponseData.message || saveResponseData.error || "Saved");
    closeModal();
  });

  actions.appendChild(insertBtn);
  actions.appendChild(saveBtn);

  modalBody.innerHTML = "";
  modalBody.appendChild(textarea);
  modalBody.appendChild(actions);
}

// ── OCR panel ────────────────────────────────────────────────────────────────
let _ocrImageBytes = null;

function setupOcrDrop() {
  ocrDropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    ocrDropZone.classList.add("drag-over");
  });
  ocrDropZone.addEventListener("dragleave", () => ocrDropZone.classList.remove("drag-over"));
  ocrDropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    ocrDropZone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) loadImageIntoOcr(file);
  });
  ocrDropZone.addEventListener("click", () => {
    const filePickerInput = document.createElement("input");
    filePickerInput.type = "file";
    filePickerInput.accept = "image/*";
    filePickerInput.onchange = (e) => {
      if (e.target.files[0]) loadImageIntoOcr(e.target.files[0]);
    };
    filePickerInput.click();
  });
}

function loadImageIntoOcr(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    ocrPreview.src = e.target.result;
    ocrPreview.style.display = "block";
    ocrDropZone.style.display = "none";
  };
  reader.readAsDataURL(file);
  _ocrImageBytes = file;
  ocrResultBox.textContent = "Image loaded. Click 'Extract Text' to run OCR.";
}

async function runOcr() {
  if (!_ocrImageBytes) { showToast("Please upload an image first"); return; }
  ocrResultBox.textContent = "Running OCR…";
  const form = new FormData();
  form.append("image", _ocrImageBytes);
  try {
    const res = await fetch("/api/ocr", { method: "POST", body: form });
    const data = await res.json();
    if (data.error) {
      ocrResultBox.textContent = "Error: " + data.error;
    } else {
      ocrResultBox.textContent = data.text || "(no text found)";
    }
  } catch (err) {
    ocrResultBox.textContent = "Network error: " + err.message;
  }
}

// ── Tools list ────────────────────────────────────────────────────────────────
async function fetchTools() {
  try {
    const res = await fetch("/api/tools");
    const data = await res.json();
    renderToolsList(data.tools || []);
    if (modelBadge && data.tools) {
      modelBadge.textContent = `${data.tools.length} tools ready`;
    }
  } catch {}
}

function renderToolsList(tools) {
  const list = $("tools-list");
  if (!list) return;
  list.innerHTML = "";
  tools.forEach((tool) => {
    const card = document.createElement("div");
    card.className = "tool-card";
    card.innerHTML = `
      <div class="tool-name">⚙ ${escapeHtml(tool.name)}</div>
      <div class="tool-desc">${escapeHtml(tool.description)}</div>
    `;
    card.addEventListener("click", () => {
      insertIntoInput(`Please use the ${tool.name} tool`);
    });
    list.appendChild(card);
  });
}

// ── Settings ──────────────────────────────────────────────────────────────────
function applySettings() {
  if (state.settings.modelType)   $("setting-model-type").value = state.settings.modelType;
  if (state.settings.baseUrl)     $("setting-base-url").value   = state.settings.baseUrl;
  if (state.settings.modelName)   $("setting-model-name").value = state.settings.modelName;
  if (state.settings.apiKey)      $("setting-api-key").value    = state.settings.apiKey;
}

// ── Tab switching ─────────────────────────────────────────────────────────────
function switchSidebarTab(tab) {
  document.querySelectorAll(".sidebar-tab").forEach((tabElement) => tabElement.classList.toggle("active", tabElement.dataset.tab === tab));
  document.querySelectorAll(".sidebar-panel").forEach((p) => p.classList.toggle("active", p.id === `panel-${tab}`));
}

function switchRightTab(tab) {
  document.querySelectorAll(".right-tab").forEach((tabElement) => tabElement.classList.toggle("active", tabElement.dataset.tab === tab));
  document.querySelectorAll(".right-panel-body").forEach((p) => p.classList.toggle("active", p.id === `rpanel-${tab}`));
}

// ── Modal ─────────────────────────────────────────────────────────────────────
function openModal(title, htmlContent) {
  modalTitle.textContent = title;
  if (typeof htmlContent === "string") {
    modalBody.innerHTML = htmlContent;
  } else {
    modalBody.innerHTML = "";
    modalBody.appendChild(htmlContent);
  }
  modalOverlay.classList.add("open");
}

function closeModal() {
  modalOverlay.classList.remove("open");
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function insertIntoInput(text) {
  const current = msgInput.value;
  msgInput.value = current ? current + "\n" + text : text;
  msgInput.dispatchEvent(new Event("input"));
  msgInput.focus();
}

function showToast(msg) {
  const toast = document.createElement("div");
  toast.style.cssText = `
    position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%);
    background: #1e2330; border: 1px solid #2a3040; border-radius: 8px;
    padding: 10px 20px; color: #e2e8f0; font-size: .82rem; z-index: 200;
    box-shadow: 0 4px 20px rgba(0,0,0,.4); pointer-events: none;
  `;
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function escapeHtml(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function formatSize(bytes) {
  if (bytes == null) return "";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(1) + " MB";
}

function getFileIcon(name) {
  const ext = name.split(".").pop().toLowerCase();
  const icons = {
    py: "🐍", js: "📜", ts: "📘", json: "📋", md: "📝",
    txt: "📄", html: "🌐", css: "🎨", sh: "⚡", yml: "⚙",
    yaml: "⚙", png: "🖼", jpg: "🖼", jpeg: "🖼", gif: "🖼",
    svg: "🖼", pdf: "📕", zip: "📦", tar: "📦", gz: "📦",
    mp3: "🎵", wav: "🎵", mp4: "🎬", csv: "📊", xml: "📋",
  };
  return icons[ext] || "📄";
}
