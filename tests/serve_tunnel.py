# -*- coding: utf-8 -*-
"""프론트(frontend/index.html) 정적 서빙 + /api·/health 를 백엔드(8000)로 프록시.
한 포트만 Cloudflare 터널로 노출하면 폰에서 앱+API 둘 다 같은 출처로 사용 가능.
실행: <venv>\\Scripts\\python.exe tests/serve_tunnel.py [port]
"""
import os
import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib import request as urlreq, error as urlerr

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
BACKEND = "http://localhost:8000"
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=FRONTEND_DIR, **kw)

    def _is_api(self):
        return self.path.startswith("/api") or self.path.startswith("/health")

    def _proxy(self, method):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None
        headers = {}
        for h in ("Content-Type", "Accept"):
            if self.headers.get(h):
                headers[h] = self.headers[h]
        req = urlreq.Request(BACKEND + self.path, data=body, headers=headers, method=method)
        try:
            with urlreq.urlopen(req, timeout=120) as resp:
                data = resp.read()
                self.send_response(resp.status)
                ct = resp.headers.get("Content-Type", "application/json")
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urlerr.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:  # 백엔드 다운 등
            msg = ('{"detail":"백엔드(8000)에 연결할 수 없습니다: %s"}' % e).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def do_GET(self):
        if self._is_api():
            return self._proxy("GET")
        return super().do_GET()

    def do_POST(self):
        if self._is_api():
            return self._proxy("POST")
        self.send_error(404)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    print(f"정적+프록시 서버 시작: http://localhost:{PORT}  (frontend={FRONTEND_DIR}, api->{BACKEND})")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
