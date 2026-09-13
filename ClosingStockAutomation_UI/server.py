import json
import sys
import threading
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys._MEIPASS)
    ROOT = PROJECT_ROOT / "ClosingStockAutomation_UI"
else:
    ROOT = Path(__file__).resolve().parent
    PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.converter_core import DEFAULT_OUTPUT_FOLDER, convert_file, get_profile, inspect_conversion, profiles_for_date
from app.output_delivery import publish_to_network
from app_run_all import run_all


DIST_DIR = ROOT / "dataflow" / "dist"

jobs = {}
jobs_lock = threading.Lock()


def log_for(job_id, message, file_id=None):
    with jobs_lock:
        job = jobs[job_id]
        job["logs"].append(message)
        if file_id is not None:
            job["files"][file_id]["log"].append(message)


def run_conversion_job(job_id, selected_files, output_folder, network_output):
    try:
        for item in selected_files:
            file_id = item["id"]
            path = Path(item["path"])
            with jobs_lock:
                if jobs[job_id].get("cancelled"):
                    jobs[job_id]["files"][file_id]["status"] = "stopped"
                    continue
                jobs[job_id]["files"][file_id]["status"] = "converting"
                jobs[job_id]["files"][file_id]["progress"] = 10
            log_for(job_id, f"Bắt đầu convert {path.name}", file_id)
            result = convert_file(
                path,
                output_folder,
                logger=lambda message, current=file_id: log_for(job_id, message, current),
                clean_old=True,
            )
            network_file = publish_to_network(
                Path(result["output"]),
                result["profile"],
                logger=lambda message, current=file_id: log_for(job_id, message, current),
                network_output=network_output,
            )
            result["network_output"] = str(network_file)
            with jobs_lock:
                jobs[job_id]["files"][file_id].update(
                    status="completed",
                    progress=100,
                    output=result["output"],
                    rows=result["rows"],
                    columns=result["columns"],
                    check=result,
                )
        with jobs_lock:
            jobs[job_id]["result"] = {"success": True}
    except Exception as exc:
        with jobs_lock:
            for file_state in jobs[job_id]["files"].values():
                if file_state["status"] == "converting":
                    file_state["status"] = "error"
                    file_state["log"].append(str(exc))
            jobs[job_id]["result"] = {"success": False, "error": str(exc)}
    finally:
        with jobs_lock:
            jobs[job_id]["running"] = False


def run_all_job(job_id):
    try:
        run_all(lambda message: log_for(job_id, message))
        with jobs_lock:
            jobs[job_id]["result"] = {"success": True}
    except Exception as exc:
        with jobs_lock:
            jobs[job_id]["result"] = {"success": False, "error": str(exc)}
    finally:
        with jobs_lock:
            jobs[job_id]["running"] = False


class Handler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        size = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(size) or b"{}")

    def _select_directory(self):
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(title="Select CSV source folder")
        root.destroy()
        return selected

    def do_POST(self):
        if self.path == "/api/dialog/select-directory":
            try:
                return self._json(200, {"success": True, "directory": self._select_directory()})
            except Exception as exc:
                return self._json(500, {"success": False, "message": str(exc)})

        if self.path == "/api/files/scan":
            try:
                directory = self._body().get("directory")
                folder = Path(directory or "")
                if not folder.is_dir():
                    return self._json(404, {"message": f"Không tìm thấy thư mục: {directory}"})
                files = []
                found_count = 0
                today = datetime.now()
                for profile, date_text in profiles_for_date(today):
                    pattern = f"{profile.prefix}{date_text}*.csv"
                    candidates = [path for path in folder.glob(pattern) if path.is_file()]
                    if profile.timestamp_format == "%Y%m%d":
                        candidates = [path for path in candidates if path.stem == f"{profile.prefix}{date_text}"]
                    path = max(candidates, key=lambda item: item.stat().st_mtime) if candidates else None
                    if path is None:
                        files.append({
                            "id": f"missing:{profile.key}", "name": f"{profile.prefix}{date_text}*.csv",
                            "path": "", "type": "file", "extension": ".csv", "size": 0,
                            "size_label": "-", "date_modified": "-", "rows": None, "columns": None,
                            "profile": profile.key, "status": "missing", "progress": 0, "log": [], "selected": False,
                        })
                        continue
                    found_count += 1
                    files.append({
                        "id": str(path), "name": path.name, "path": str(path),
                        "type": "file", "extension": ".csv", "size": path.stat().st_size,
                        "size_label": f"{path.stat().st_size / 1024 / 1024:.1f} MB",
                        "date_modified": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        "rows": None, "columns": None, "profile": profile.key,
                        "status": "pending", "progress": 0, "log": [], "selected": False,
                    })
                return self._json(200, {"success": True, "directory": str(folder), "count": found_count, "found_count": found_count, "files": files})
            except Exception as exc:
                return self._json(500, {"success": False, "message": str(exc)})

        if self.path == "/api/convert":
            try:
                body = self._body()
                selected = body.get("files", [])
                if not selected:
                    return self._json(400, {"message": "Chưa chọn file CSV."})
                job_id = str(uuid.uuid4())
                with jobs_lock:
                    jobs[job_id] = {
                        "running": True, "result": None, "logs": [],
                        "cancelled": False,
                        "files": {
                            item["id"]: {
                                "status": "pending", "progress": 0, "log": [],
                            }
                            for item in selected
                        },
                    }
                output_folder = Path(body.get("output_folder") or DEFAULT_OUTPUT_FOLDER)
                network_output = Path(body.get("source_directory") or "")
                if not network_output.is_dir():
                    return self._json(400, {"message": "Shared Drive Directory không tồn tại hoặc chưa được chọn."})
                threading.Thread(
                    target=run_conversion_job,
                    args=(job_id, selected, output_folder, network_output),
                    daemon=True,
                ).start()
                return self._json(202, {"success": True, "job_id": job_id})
            except Exception as exc:
                return self._json(500, {"success": False, "message": str(exc)})

        if self.path == "/api/check":
            try:
                body = self._body()
                input_file = Path(body.get("input_file", ""))
                output_file = Path(body.get("output_file", ""))
                profile = body.get("profile", "")
                if not input_file.is_file() or not output_file.is_file():
                    return self._json(404, {"message": "Không tìm thấy CSV hoặc Parquet để kiểm tra."})
                return self._json(200, {"success": True, "check": inspect_conversion(input_file, output_file, profile)})
            except Exception as exc:
                return self._json(500, {"success": False, "message": str(exc)})

        if self.path == "/api/run-all":
            with jobs_lock:
                running = any(job["running"] for job in jobs.values())
            if running:
                return self._json(409, {"success": False, "message": "Automation đang chạy."})
            job_id = str(uuid.uuid4())
            with jobs_lock:
                jobs[job_id] = {"running": True, "result": None, "logs": [], "files": {}, "cancelled": False}
            threading.Thread(target=run_all_job, args=(job_id,), daemon=True).start()
            return self._json(202, {"success": True, "job_id": job_id})

        if self.path == "/api/stop":
            job_id = self._body().get("job_id")
            with jobs_lock:
                if job_id in jobs:
                    jobs[job_id]["cancelled"] = True
            return self._json(200, {"success": True})

        self._json(404, {"message": "Not found"})

    def do_GET(self):
        if self.path == "/api/status" or self.path.startswith("/api/status/"):
            job_id = self.path.rsplit("/", 1)[-1] if self.path != "/api/status" else None
            with jobs_lock:
                if job_id and job_id in jobs:
                    job = jobs[job_id]
                    return self._json(200, job)
                latest = next(reversed(jobs.values()), {"running": False, "result": None, "logs": [], "files": {}})
            return self._json(200, latest)

        if self.path == "/api/health":
            return self._json(200, {"success": True})

        if DIST_DIR.exists():
            rel = self.path.split("?", 1)[0].lstrip("/") or "index.html"
            target = (DIST_DIR / rel).resolve()
            if DIST_DIR.resolve() in target.parents and target.is_file():
                data = target.read_bytes()
                content_type = {
                    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                    ".css": "text/css", ".svg": "image/svg+xml",
                }.get(target.suffix, "application/octet-stream")
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

        self._json(404, {"message": "Frontend chưa được build. Hãy build dataflow/dist."})

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 3001
    print(f"Python backend: http://127.0.0.1:{port}")
    print(f"LAN access: http://<HOST-PC-IP>:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
