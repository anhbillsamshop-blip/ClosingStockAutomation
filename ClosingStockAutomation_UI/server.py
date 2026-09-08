import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT
RUN_ALL = APP_DIR / "app_run_all.py"
DIST_DIR = ROOT / "dataflow" / "dist"

running = False
last_result = None
logs = []
lock = threading.Lock()


def run_pipeline():
    global running, last_result
    with lock:
        running = True
        last_result = None
        logs.clear()
        logs.append("Bắt đầu chạy toàn bộ 4 automation...")

    try:
        p = subprocess.Popen(
            [sys.executable, str(RUN_ALL)],
            cwd=str(APP_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        for line in p.stdout:
            line = line.rstrip()
            if line:
                with lock:
                    logs.append(line)
        code = p.wait()
        with lock:
            last_result = {"success": code == 0, "returncode": code}
            logs.append("HOÀN TẤT." if code == 0 else f"CHẠY LỖI. Return code: {code}")
    except Exception as exc:
        with lock:
            last_result = {"success": False, "error": str(exc)}
            logs.append(f"ERROR: {exc}")
    finally:
        with lock:
            running = False


class Handler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        if self.path == "/api/run-all":
            with lock:
                if running:
                    return self._json(409, {"success": False, "message": "Automation đang chạy."})
            threading.Thread(target=run_pipeline, daemon=True).start()
            return self._json(202, {"success": True, "message": "Đã bắt đầu chạy."})

        if self.path == "/api/files/scan":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n) or b"{}")
                directory = body.get("directory")
                if not directory:
                    return self._json(400, {"message": "Directory is required"})
                p = Path(directory)
                if not p.exists():
                    return self._json(404, {"message": f"Không tìm thấy thư mục: {directory}"})
                result = []
                for x in p.iterdir():
                    try:
                        st = x.stat()
                        result.append({
                            "id": str(x), "name": x.name, "path": str(x),
                            "type": "folder" if x.is_dir() else "file",
                            "extension": x.suffix.lower() if x.is_file() else None,
                            "size": st.st_size if x.is_file() else None,
                            "rows": None, "columns": None,
                            "status": "pending", "progress": 0,
                            "log": [], "selected": False,
                        })
                    except OSError:
                        pass
                return self._json(200, {"success": True, "directory": directory, "count": len(result), "files": result})
            except Exception as exc:
                return self._json(500, {"success": False, "message": str(exc)})

        self._json(404, {"message": "Not found"})

    def do_GET(self):
        if self.path == "/api/status":
            with lock:
                return self._json(200, {"running": running, "result": last_result, "logs": logs[-500:]})

        if self.path == "/api/health":
            return self._json(200, {"success": True})

        # Serve built React files if they exist.
        if DIST_DIR.exists():
            rel = self.path.split("?", 1)[0].lstrip("/") or "index.html"
            target = (DIST_DIR / rel).resolve()
            if DIST_DIR.resolve() in target.parents and target.is_file():
                data = target.read_bytes()
                ctype = "text/html; charset=utf-8"
                if target.suffix == ".js": ctype = "text/javascript; charset=utf-8"
                elif target.suffix == ".css": ctype = "text/css; charset=utf-8"
                elif target.suffix == ".svg": ctype = "image/svg+xml"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

        self._json(404, {"message": "Frontend chưa được build. Hãy build dist trên máy có Node.js rồi chép dist vào dataflow/."})

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    print("Python backend: http://127.0.0.1:3001")
    print("API: POST /api/run-all")
    ThreadingHTTPServer(("127.0.0.1", 3001), Handler).serve_forever()
