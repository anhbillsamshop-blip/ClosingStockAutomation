import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
APP_DIR = PROJECT_ROOT / "app"
RUN_ALL = APP_DIR / "run_all.py"
INDEX = ROOT / "index.html"

HOST = "127.0.0.1"
PORT = 3010

running = False
last_result = None
logs = []
lock = threading.Lock()
process = None


def run_pipeline():
    global running, last_result, process

    with lock:
        running = True
        last_result = None
        logs.clear()
        logs.append("BẮT ĐẦU CHẠY TOÀN BỘ 4 AUTOMATION...")

    try:
        if not RUN_ALL.exists():
            raise FileNotFoundError(f"Không tìm thấy: {RUN_ALL}")

        process = subprocess.Popen(
            [sys.executable, str(RUN_ALL)],
            cwd=str(APP_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        for line in process.stdout:
            line = line.rstrip()
            if line:
                with lock:
                    logs.append(line)

        code = process.wait()

        with lock:
            last_result = {"success": code == 0, "returncode": code}
            logs.append(
                "✓ HOÀN TẤT TOÀN BỘ."
                if code == 0
                else f"✗ CHẠY LỖI. Return code: {code}"
            )

    except Exception as exc:
        with lock:
            last_result = {"success": False, "error": str(exc)}
            logs.append(f"ERROR: {exc}")

    finally:
        with lock:
            running = False
            process = None


def json_response(handler, status, payload):
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(raw)


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/run-all":
            with lock:
                if running:
                    return json_response(
                        self, 409,
                        {"success": False, "message": "Automation đang chạy."}
                    )
            threading.Thread(target=run_pipeline, daemon=True).start()
            return json_response(
                self, 202,
                {"success": True, "message": "Đã bắt đầu chạy."}
            )

        if self.path == "/api/files/scan":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n) or b"{}")
                directory = body.get("directory")
                if not directory:
                    return json_response(
                        self, 400, {"message": "Directory is required"}
                    )

                p = Path(directory)
                if not p.exists():
                    return json_response(
                        self, 404,
                        {"message": f"Không tìm thấy thư mục: {directory}"}
                    )

                result = []
                for x in p.iterdir():
                    try:
                        st = x.stat()
                        result.append({
                            "id": str(x),
                            "name": x.name,
                            "path": str(x),
                            "type": "folder" if x.is_dir() else "file",
                            "extension": x.suffix.lower() if x.is_file() else None,
                            "size": st.st_size if x.is_file() else None,
                            "rows": None,
                            "columns": None,
                            "status": "pending",
                            "progress": 0,
                            "log": [],
                            "selected": False,
                        })
                    except OSError:
                        pass

                return json_response(
                    self, 200,
                    {
                        "success": True,
                        "directory": directory,
                        "count": len(result),
                        "files": result,
                    }
                )
            except Exception as exc:
                return json_response(
                    self, 500, {"success": False, "message": str(exc)}
                )

        return json_response(self, 404, {"message": "Not found"})

    def do_GET(self):
        if self.path == "/api/status":
            with lock:
                return json_response(
                    self, 200,
                    {
                        "running": running,
                        "result": last_result,
                        "logs": logs[-500:],
                    }
                )

        if self.path == "/api/health":
            return json_response(self, 200, {"success": True})

        if self.path in ("/", "/index.html"):
            if not INDEX.exists():
                return json_response(
                    self, 500,
                    {"message": f"Không tìm thấy giao diện: {INDEX}"}
                )

            data = INDEX.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        return json_response(self, 404, {"message": "Not found"})

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    print("=" * 60)
    print("CLOSING STOCK AUTOMATION")
    print("=" * 60)
    print()
    print(f"Frontend: http://{HOST}:{PORT}")
    print(f"Backend:  http://{HOST}:{PORT}/api/health")
    print(f"Run All:  {RUN_ALL}")
    print()

    if not INDEX.exists():
        print(f"WARNING: Không tìm thấy {INDEX}")
    if not RUN_ALL.exists():
        print(f"WARNING: Không tìm thấy {RUN_ALL}")

    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
