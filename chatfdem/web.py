from __future__ import annotations

import argparse
import json
import mimetypes
import socket
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

from .nl import PromptError
from .workflow import run_prompt_workflow


DEFAULT_PROMPT = "Create a 2D rectangular rock specimen 100 mm wide and 50 mm high with a centered 10 mm diameter circular hole. Use finer mesh near the hole and tag the outer boundaries as left, right, top, and bottom."

INDEX_HTML = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>chatFDEM</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #eceff3;
      --panel: #ffffff;
      --panel-soft: #f8fafc;
      --ink: #1e252c;
      --muted: #66717f;
      --line: #cfd6df;
      --accent: #1f6f5b;
      --accent-strong: #155344;
      --accent-soft: #e5f2ee;
      --amber: #94610f;
      --error: #b3261e;
      --shadow: 0 1px 2px rgba(24, 32, 40, 0.08);
    }
    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    .app {
      display: grid;
      grid-template-columns: minmax(360px, 460px) minmax(0, 1fr);
      height: 100vh;
      min-height: 680px;
    }
    .left, .right { min-height: 0; }
    .left {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr) auto minmax(150px, 0.36fr);
      gap: 12px;
      padding: 14px;
      border-right: 1px solid var(--line);
      background: var(--panel);
    }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      min-height: 38px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 12px;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      line-height: 1.2;
      font-weight: 680;
      letter-spacing: 0;
    }
    .status {
      min-width: 92px;
      text-align: right;
      font-size: 12px;
      color: var(--muted);
    }
    .chat {
      min-height: 0;
      overflow: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding-right: 2px;
    }
    .message {
      display: grid;
      gap: 5px;
      max-width: 94%;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-soft);
      box-shadow: var(--shadow);
      font-size: 13px;
      line-height: 1.45;
    }
    .message.user {
      margin-left: auto;
      border-color: #bdd8cf;
      background: var(--accent-soft);
    }
    .message.assistant { margin-right: auto; }
    .message.error {
      color: var(--error);
      border-color: #e0b2ae;
      background: #fff7f6;
      white-space: pre-wrap;
    }
    .message .role {
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .message .text { white-space: pre-wrap; overflow-wrap: anywhere; }
    .composer {
      display: grid;
      gap: 10px;
      padding-top: 2px;
    }
    textarea {
      width: 100%;
      min-height: 120px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 11px 12px;
      font: inherit;
      line-height: 1.45;
      color: var(--ink);
      background: #fbfcfd;
    }
    textarea:focus, select:focus, input:focus {
      outline: 2px solid rgba(31, 111, 91, 0.22);
      border-color: var(--accent);
    }
    .composer-row, .settings-row {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }
    .composer-row { justify-content: space-between; }
    .settings-row { flex-wrap: wrap; }
    label {
      display: grid;
      gap: 4px;
      color: var(--muted);
      font-size: 11px;
      min-width: 112px;
    }
    select, input {
      height: 34px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fff;
      color: var(--ink);
      padding: 0 9px;
      font: inherit;
      font-size: 13px;
    }
    input { width: 150px; }
    button {
      height: 36px;
      border: 1px solid var(--accent-strong);
      border-radius: 7px;
      background: var(--accent);
      color: #fff;
      padding: 0 14px;
      font: inherit;
      font-weight: 650;
      cursor: pointer;
      white-space: nowrap;
    }
    button.secondary {
      background: #fff;
      color: var(--ink);
      border-color: var(--line);
      font-weight: 520;
    }
    button:disabled { opacity: 0.58; cursor: not-allowed; }
    .examples {
      display: flex;
      gap: 7px;
      flex-wrap: wrap;
      min-width: 0;
    }
    .examples button {
      height: 28px;
      padding: 0 9px;
      border-color: #d6dbe2;
      background: #fff;
      color: var(--muted);
      font-size: 12px;
      font-weight: 520;
    }
    .details {
      min-height: 0;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-soft);
      padding: 10px;
      font-size: 12px;
      line-height: 1.45;
    }
    .details h2 {
      margin: 0 0 8px;
      font-size: 13px;
      letter-spacing: 0;
    }
    .details dl {
      display: grid;
      grid-template-columns: 90px minmax(0, 1fr);
      gap: 5px 8px;
      margin: 0;
    }
    .details dt { color: var(--muted); }
    .details dd { margin: 0; overflow-wrap: anywhere; }
    .right {
      display: grid;
      grid-template-rows: 42px minmax(0, 1fr);
      background: #dfe5ec;
    }
    .viewer-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 0 14px;
      border-bottom: 1px solid var(--line);
      background: #f8fafc;
      color: var(--muted);
      font-size: 13px;
    }
    .viewer-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--ink);
      font-weight: 590;
    }
    .links {
      display: flex;
      gap: 10px;
      overflow: hidden;
      align-items: center;
    }
    .links a {
      color: var(--accent-strong);
      text-decoration: none;
      white-space: nowrap;
    }
    .links a:hover { text-decoration: underline; }
    iframe {
      width: 100%;
      height: 100%;
      border: 0;
      background: #fff;
    }
    [hidden] { display: none !important; }
    .empty {
      display: grid;
      place-items: center;
      height: 100%;
      color: var(--muted);
      background: #f7f9fb;
      font-size: 14px;
    }
    @media (max-width: 920px) {
      .app {
        grid-template-columns: 1fr;
        grid-template-rows: minmax(520px, 52vh) minmax(420px, 48vh);
        height: auto;
        min-height: 100vh;
      }
      .left { border-right: 0; border-bottom: 1px solid var(--line); }
    }
  </style>
</head>
<body>
  <main class="app">
    <section class="left" aria-label="chatFDEM controls">
      <div class="topbar">
        <h1>chatFDEM</h1>
        <div id="status" class="status">Ready</div>
      </div>
      <section id="chat" class="chat" aria-live="polite"></section>
      <form id="composer" class="composer">
        <textarea id="prompt" spellcheck="true"></textarea>
        <div class="settings-row">
          <label>Provider
            <select id="provider">
              <option value="agent">Agent-owned</option>
              <option value="command">Standalone Command</option>
              <option value="fixture">Fixture</option>
            </select>
          </label>
          <label>Model
            <input id="model" type="text" autocomplete="off" placeholder="default">
          </label>
        </div>
        <div class="composer-row">
          <div class="examples" aria-label="example prompts">
            <button type="button" data-example="rect-hole">Rect Hole</button>
            <button type="button" data-example="notched-disc">Notched Disc</button>
          </div>
          <div class="actions">
            <button id="reset" class="secondary" type="button">Reset</button>
            <button id="generate" type="submit">Generate Mesh</button>
          </div>
        </div>
      </form>
      <section class="details" aria-live="polite">
        <h2>Run Details</h2>
        <div id="details">No mesh generated yet.</div>
      </section>
    </section>
    <section class="right" aria-label="geometry preview">
      <div class="viewer-bar">
        <span id="viewer-title" class="viewer-name">Geometry Preview</span>
        <nav id="links" class="links"></nav>
      </div>
      <div id="viewer-empty" class="empty">Generated geometry will appear here.</div>
      <iframe id="viewer" title="Generated geometry preview" hidden></iframe>
    </section>
  </main>
  <script>
    const defaultPrompt = __DEFAULT_PROMPT__;
    const examples = {
      'rect-hole': defaultPrompt,
      'notched-disc': 'Create a 2D circular rock disk with radius 40 mm, a 6 mm wide vertical notch from the top edge to the center, and physical curves named outer, notch_left, notch_right, and notch_tip. Use smaller elements around the notch tip.'
    };

    const promptEl = document.getElementById('prompt');
    const providerEl = document.getElementById('provider');
    const modelEl = document.getElementById('model');
    const statusEl = document.getElementById('status');
    const detailsEl = document.getElementById('details');
    const viewerEl = document.getElementById('viewer');
    const emptyEl = document.getElementById('viewer-empty');
    const linksEl = document.getElementById('links');
    const titleEl = document.getElementById('viewer-title');
    const generateBtn = document.getElementById('generate');
    const resetBtn = document.getElementById('reset');
    const composerEl = document.getElementById('composer');
    const chatEl = document.getElementById('chat');

    promptEl.value = defaultPrompt;
    addMessage('assistant', 'Ready.');

    function setBusy(isBusy) {
      generateBtn.disabled = isBusy;
      resetBtn.disabled = isBusy;
      providerEl.disabled = isBusy;
      modelEl.disabled = isBusy;
      statusEl.textContent = isBusy ? 'Running' : 'Ready';
    }

    function artifactLink(label, url) {
      const a = document.createElement('a');
      a.textContent = label;
      a.href = url;
      a.target = '_blank';
      a.rel = 'noreferrer';
      return a;
    }

    function addMessage(role, text, options = {}) {
      const message = document.createElement('article');
      message.className = `message ${role}${options.error ? ' error' : ''}`;
      const roleEl = document.createElement('div');
      roleEl.className = 'role';
      roleEl.textContent = role === 'user' ? 'You' : 'chatFDEM';
      const textEl = document.createElement('div');
      textEl.className = 'text';
      textEl.textContent = text;
      message.append(roleEl, textEl);
      chatEl.appendChild(message);
      chatEl.scrollTop = chatEl.scrollHeight;
      return textEl;
    }

    function formatNodeSets(nodeSets) {
      const entries = Object.entries(nodeSets || {});
      return entries.length ? entries.map(([k, v]) => `${k}=${v}`).join(', ') : '-';
    }

    function showDetails(data) {
      const brief = data.brief || {};
      const mesh = data.mesh || {};
      const inp = data.inp || {};
      const paths = data.paths || {};
      const llm = data.llm || {};
      const nodeSets = inp.node_sets || {};
      detailsEl.innerHTML = '';
      const dl = document.createElement('dl');
      const rows = [
        ['Provider', [llm.provider, llm.model].filter(Boolean).join('/') || '-'],
        ['Kind', brief.kind || brief.summary || '-'],
        ['Size', brief.width && brief.height ? `${brief.width} x ${brief.height} ${brief.units || ''}`.trim() : '-'],
        ['Hole', brief.hole_diameter ? `${brief.hole_diameter} ${brief.units || ''} diameter` : '-'],
        ['Nodes', mesh.nodes || '0'],
        ['Elements', mesh.elements || '0'],
        ['NSETs', formatNodeSets(nodeSets)],
        ['Run', paths.run_dir || '-']
      ];
      for (const [key, value] of rows) {
        const dt = document.createElement('dt');
        dt.textContent = key;
        const dd = document.createElement('dd');
        dd.textContent = String(value || '-');
        dl.append(dt, dd);
      }
      detailsEl.appendChild(dl);
    }

    function showError(message) {
      detailsEl.innerHTML = '';
      const div = document.createElement('div');
      div.className = 'message error';
      div.textContent = message;
      detailsEl.appendChild(div);
    }

    function assistantSummary(data) {
      const mesh = data.mesh || {};
      const inp = data.inp || {};
      const llm = data.llm || {};
      const sets = Object.keys(inp.node_sets || {});
      const provider = [llm.provider, llm.model].filter(Boolean).join('/');
      const parts = [
        `Generated ${data.name || 'mesh'}.`,
        `Nodes: ${mesh.nodes || 0}. Elements: ${mesh.elements || 0}.`
      ];
      if (sets.length) {
        parts.push(`Node sets: ${sets.join(', ')}.`);
      }
      if (provider) {
        parts.push(`LLM: ${provider}.`);
      }
      return parts.join('\\n');
    }

    async function generate() {
      const prompt = promptEl.value.trim();
      if (!prompt) {
        addMessage('assistant', 'Enter a geometry request before generating a mesh.', { error: true });
        return;
      }
      setBusy(true);
      linksEl.innerHTML = '';
      addMessage('user', prompt);
      const pending = addMessage('assistant', 'Generating .geo, running Gmsh, and preparing preview...');
      try {
        const response = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            prompt,
            llm_provider: providerEl.value || null,
            model: modelEl.value.trim() || null
          })
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || `Request failed with ${response.status}`);
        }
        const data = payload.run;
        showDetails(data);
        const urls = payload.urls || {};
        viewerEl.src = urls.preview;
        viewerEl.hidden = false;
        emptyEl.hidden = true;
        titleEl.textContent = data.name || 'Geometry Preview';
        for (const [label, url] of Object.entries(urls)) {
          linksEl.appendChild(artifactLink(label.toUpperCase(), url));
        }
        pending.textContent = assistantSummary(data);
      } catch (error) {
        const message = error.message || String(error);
        pending.textContent = message;
        pending.parentElement.classList.add('error');
        showError(message);
        statusEl.textContent = 'Error';
      } finally {
        setBusy(false);
      }
    }

    composerEl.addEventListener('submit', (event) => {
      event.preventDefault();
      generate();
    });
    resetBtn.addEventListener('click', () => {
      promptEl.value = defaultPrompt;
      promptEl.focus();
    });
    document.querySelectorAll('[data-example]').forEach((button) => {
      button.addEventListener('click', () => {
        const value = examples[button.dataset.example] || defaultPrompt;
        promptEl.value = value;
        promptEl.focus();
      });
    });
  </script>
</body>
</html>
'''

class ChatFdemHandler(SimpleHTTPRequestHandler):
    server_version = "chatFDEM/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(INDEX_HTML.replace("__DEFAULT_PROMPT__", json.dumps(DEFAULT_PROMPT)))
            return
        if parsed.path.startswith("/runs/"):
            self._send_run_file(parsed.path[len("/runs/") :])
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/generate":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        try:
            body = self.rfile.read(_content_length(self.headers.get("content-length")))
            payload = json.loads(body.decode("utf-8") or "{}")
            prompt = str(payload.get("prompt") or "").strip()
            llm_provider = str(payload.get("llm_provider") or "").strip() or None
            llm_model = str(payload.get("model") or "").strip() or None
            run = run_prompt_workflow(
                prompt,
                runs_root=self.server.runs_root,
                llm_provider=llm_provider,
                llm_model=llm_model,
            )
            summary = run.summary(base_dir=self.server.runs_root)
            urls = {
                "preview": _run_url(self.server.runs_root, run.preview_path),
                "geo": _run_url(self.server.runs_root, run.geo_path),
                "msh": _run_url(self.server.runs_root, run.msh_path),
                "inp": _run_url(self.server.runs_root, run.inp_path),
                "report": _run_url(self.server.runs_root, run.report_path),
            }
            self._send_json({"ok": True, "run": summary, "urls": urls})
        except (PromptError, ValueError, OSError, RuntimeError) as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json({"ok": False, "error": "Request body must be valid JSON."}, status=HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: object) -> None:
        if getattr(self.server, "quiet", False):
            return
        super().log_message(format, *args)

    def _send_html(self, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, object], *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_run_file(self, relative_ref: str) -> None:
        relative = unquote(relative_ref).replace("\\", "/").lstrip("/")
        target = (self.server.runs_root / relative).resolve()
        if not _inside(target, self.server.runs_root) or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Artifact not found")
            return
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if target.suffix.lower() in {".geo", ".msh", ".inp"}:
            content_type = "text/plain; charset=utf-8"
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", content_type)
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(host: str = "127.0.0.1", port: int = 8765, *, runs_root: str | Path = "runs", quiet: bool = False) -> str:
    root = Path(runs_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    try:
        server = ThreadingHTTPServer((host, port), ChatFdemHandler)
    except OSError as exc:
        fallback_port = available_port(host, port + 1 if port > 0 else 8765)
        print(f"Port {port} is unavailable ({exc}); using {fallback_port} instead.", flush=True)
        server = ThreadingHTTPServer((host, fallback_port), ChatFdemHandler)
    server.runs_root = root  # type: ignore[attr-defined]
    server.quiet = quiet  # type: ignore[attr-defined]
    url = f"http://{host}:{server.server_port}/"
    print(f"chatFDEM web interface: {url}", flush=True)
    print(f"runs: {root}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return url


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start the chatFDEM web interface.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--runs-root", default="runs")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    serve(args.host, args.port, runs_root=args.runs_root, quiet=args.quiet)
    return 0


def _content_length(value: str | None) -> int:
    try:
        length = int(value or "0")
    except ValueError:
        return 0
    return max(0, min(length, 256 * 1024))


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _run_url(root: Path, path: Path) -> str:
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    return "/runs/" + "/".join(quote(part) for part in relative.split("/"))


def available_port(host: str = "127.0.0.1", preferred: int = 8765) -> int:
    for port in range(preferred, preferred + 64):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise OSError(f"No available port found from {preferred} to {preferred + 63}")


if __name__ == "__main__":
    raise SystemExit(main())
