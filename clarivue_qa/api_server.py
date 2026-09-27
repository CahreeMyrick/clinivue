"""Serve the Clarivue UI and forward questions to the research QA backend."""

from __future__ import annotations

import json
import os
import re
import urllib.request
from urllib.error import HTTPError, URLError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = int(os.environ.get("CLARIVUE_PORT", "8000"))
ROOT = Path(__file__).parent
DIST = ROOT / "dist"
RESEARCH_RAG_URL = os.environ.get("CLARIVUE_RAG_URL", "http://127.0.0.1:8010/api/qa").strip()

class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict | str, content_type: str = "application/json") -> None:
        body = payload if isinstance(payload, bytes) else (payload.encode() if isinstance(payload, str) else json.dumps(payload).encode())
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(204, b"")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            self._send(200, {"ok": True, "service": "clarivue-qa", "backend_url": RESEARCH_RAG_URL})
            return
        if path == "/api/evidence":
            self._send(200, {"sources": [], "message": "Submit a question to retrieve evidence."})
            return
        if path == "/" or path == "/index.html":
            self._send(200, (DIST / "index.html").read_bytes(), "text/html")
            return
        asset = DIST / path.lstrip("/")
        if asset.is_file() and asset.parent == DIST:
            content_type = "text/javascript" if asset.suffix == ".js" else "text/css" if asset.suffix == ".css" else "application/octet-stream"
            self._send(200, asset.read_bytes(), content_type)
            return
        self._send(404, {"error": "not_found", "message": "The requested Clarivue route does not exist."})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/qa":
            self._send(404, {"error": "not_found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 32_000:
                raise ValueError("request body must contain 1 to 32000 bytes")
            body = json.loads(self.rfile.read(size) or b"{}")
            if not isinstance(body, dict) or not isinstance(body.get("question"), str):
                raise ValueError("question must be a string")
            question = re.sub(r"\s+", " ", body["question"].strip())
            if not question:
                raise ValueError("question is required")
            if len(question) > 1_500:
                raise ValueError("question must be 1,500 characters or fewer")
            if RESEARCH_RAG_URL:
                request = urllib.request.Request(
                    RESEARCH_RAG_URL,
                    data=json.dumps({"question": question}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=540) as response:
                    try:
                        payload = json.loads(response.read())
                    except (ValueError, UnicodeDecodeError) as exc:
                        raise RuntimeError("Research backend returned invalid JSON") from exc
                    self._send(response.status, payload)
                return
            self._send(503, {"error": "not_configured", "message": "Configure CLARIVUE_RAG_URL to connect the research backend."})
        except HTTPError as exc:
            message = "Research backend returned HTTP " + str(exc.code)
            try:
                detail = json.loads(exc.read()).get("message")
                if isinstance(detail, str):
                    message += ": " + detail
            except (ValueError, AttributeError):
                pass
            self._send(502, {"error": "backend_failed", "message": message})
        except (URLError, OSError) as exc:
            self._send(502, {"error": "backend_unavailable", "message": "Cannot reach the research backend. Start python -m indexer.http_api and check CLARIVUE_RAG_URL."})
        except RuntimeError as exc:
            self._send(502, {"error": "backend_failed", "message": str(exc)})
        except (ValueError, UnicodeDecodeError) as exc:
            self._send(400, {"error": "invalid_request", "message": str(exc)})


if __name__ == "__main__":
    print(f"Clarivue QA API: http://{HOST}:{PORT}")
    print("POST /api/qa with JSON: {\"question\": \"...\"}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
