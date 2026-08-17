from pathlib import Path
import sys
import threading
import queue
import traceback
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import uvicorn

# Allow importing the converter from this folder.
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import closing_stock_duckdb_optimized as converter


app = FastAPI(title="CSV → Parquet Automation")

JOB_CONFIG = {
    item["name"]: item
    for item in converter.FILE_TYPES
}

state_lock = threading.Lock()
jobs = {
    name: {
        "status": "IDLE",
        "started_at": None,
        "finished_at": None,
        "input": None,
        "output": None,
        "error": None,
        "logs": [],
    }
    for name in JOB_CONFIG
}

current_job = None
running_thread = None


class TeeOutput:
    """Send print() output to terminal and the web log."""
    def __init__(self, job_name, original):
        self.job_name = job_name
        self.original = original

    def write(self, text):
        if text:
            self.original.write(text)
            self.original.flush()

            # Split immediately so the browser gets useful live lines.
            for line in text.splitlines():
                line = line.strip()
                if line:
                    add_log(self.job_name, line)

    def flush(self):
        self.original.flush()


def add_log(job_name, message):
    with state_lock:
        job = jobs[job_name]
        job["logs"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message,
        })

        # Keep browser memory bounded.
        if len(job["logs"]) > 2000:
            job["logs"] = job["logs"][-2000:]


def reset_job(job_name):
    with state_lock:
        jobs[job_name] = {
            "status": "IDLE",
            "started_at": None,
            "finished_at": None,
            "input": None,
            "output": None,
            "error": None,
            "logs": [],
        }


def run_one(job_name):
    global current_job

    config = JOB_CONFIG[job_name]

    with state_lock:
        current_job = job_name
        jobs[job_name]["status"] = "RUNNING"
        jobs[job_name]["started_at"] = datetime.now().isoformat(timespec="seconds")

    original_stdout = sys.stdout

    try:
        sys.stdout = TeeOutput(job_name, original_stdout)

        add_log(job_name, f"START: {job_name}")

        input_file = converter.find_latest_file(
            prefix=config["prefix"],
            file_type=config["type"],
            folder=config["folder"],
        )

        if input_file is None:
            raise RuntimeError("Không tìm thấy file input phù hợp.")

        with state_lock:
            jobs[job_name]["input"] = str(input_file)

        output_file = converter.convert_csv_to_parquet(
            input_file=input_file,
            prefix=config["prefix"],
        )

        with state_lock:
            jobs[job_name]["output"] = str(output_file)
            jobs[job_name]["status"] = "SUCCESS"
            jobs[job_name]["finished_at"] = datetime.now().isoformat(timespec="seconds")

        add_log(job_name, "✓ JOB SUCCESS")

    except Exception as exc:
        error_text = str(exc)

        with state_lock:
            jobs[job_name]["status"] = "ERROR"
            jobs[job_name]["error"] = error_text
            jobs[job_name]["finished_at"] = datetime.now().isoformat(timespec="seconds")

        add_log(job_name, f"!!! ERROR: {error_text}")
        traceback.print_exc()

    finally:
        sys.stdout = original_stdout

        with state_lock:
            current_job = None


def run_all_background():
    global running_thread

    def worker():
        for name in JOB_CONFIG:
            run_one(name)

    running_thread = threading.Thread(target=worker, daemon=True)
    running_thread.start()


def run_one_background(job_name):
    global running_thread

    running_thread = threading.Thread(
        target=run_one,
        args=(job_name,),
        daemon=True,
    )
    running_thread.start()


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


@app.get("/api/status")
def api_status():
    with state_lock:
        return {
            "current_job": current_job,
            "jobs": jobs,
        }


@app.post("/api/run/{job_name}")
def api_run(job_name: str):
    global running_thread

    if job_name not in JOB_CONFIG:
        raise HTTPException(status_code=404, detail="Job không tồn tại.")

    if running_thread is not None and running_thread.is_alive():
        raise HTTPException(
            status_code=409,
            detail=f"Đang chạy {current_job}. Hãy chờ job hiện tại hoàn tất.",
        )

    reset_job(job_name)
    run_one_background(job_name)

    return {"ok": True, "message": f"Đã bắt đầu {job_name}"}


@app.post("/api/run-all")
def api_run_all():
    global running_thread

    if running_thread is not None and running_thread.is_alive():
        raise HTTPException(
            status_code=409,
            detail=f"Đang chạy {current_job}.",
        )

    for name in JOB_CONFIG:
        reset_job(name)

    run_all_background()

    return {"ok": True, "message": "Đã bắt đầu RUN ALL"}


HTML = r"""
<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CSV → Parquet Automation</title>

<style>
* { box-sizing: border-box; }

body {
    margin: 0;
    background: #0b1020;
    color: #e8edf7;
    font-family: Segoe UI, Arial, sans-serif;
}

.container {
    max-width: 1450px;
    margin: 0 auto;
    padding: 24px;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 22px;
}

h1 {
    margin: 0;
    font-size: 28px;
}

.subtitle {
    color: #8d99ad;
    margin-top: 5px;
}

.card {
    background: #121a2d;
    border: 1px solid #25304a;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 18px;
}

.jobs {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
}

.job {
    background: #0e1527;
    border: 1px solid #28334d;
    border-radius: 12px;
    padding: 16px;
}

.job-name {
    font-weight: 700;
    font-size: 15px;
    min-height: 42px;
}

.status {
    display: inline-block;
    margin: 12px 0;
    padding: 5px 9px;
    border-radius: 999px;
    font-size: 12px;
    background: #293247;
}

.status.RUNNING { background: #6b4e00; color: #ffd86b; }
.status.SUCCESS { background: #124c36; color: #6ff0b5; }
.status.ERROR { background: #5c1f2a; color: #ff9aaa; }
.status.IDLE { color: #9ba7bb; }

button {
    border: 0;
    border-radius: 8px;
    padding: 9px 13px;
    cursor: pointer;
    font-weight: 700;
}

.run {
    background: #2878ff;
    color: white;
    width: 100%;
}

.run:hover { background: #4a8cff; }

.runall {
    background: #18a673;
    color: white;
    padding: 12px 22px;
}

button:disabled {
    opacity: .45;
    cursor: not-allowed;
}

.current {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 15px;
}

.metric {
    background: #0e1527;
    padding: 14px;
    border-radius: 10px;
}

.metric-label {
    color: #8995a9;
    font-size: 12px;
}

.metric-value {
    margin-top: 6px;
    font-weight: 700;
    word-break: break-all;
}

.log-box {
    height: 500px;
    overflow-y: auto;
    background: #070b14;
    border: 1px solid #202b41;
    border-radius: 10px;
    padding: 12px;
    font-family: Consolas, monospace;
    font-size: 13px;
}

.log-line {
    margin-bottom: 5px;
    white-space: pre-wrap;
}

.log-time {
    color: #6f829e;
}

.log-message {
    color: #d8e0ef;
}

.empty {
    color: #69758a;
}

@media (max-width: 1000px) {
    .jobs { grid-template-columns: repeat(2, 1fr); }
    .current { grid-template-columns: 1fr; }
}

@media (max-width: 600px) {
    .jobs { grid-template-columns: 1fr; }
    .container { padding: 12px; }
}
</style>
</head>

<body>
<div class="container">

    <div class="header">
        <div>
            <h1>CSV → Parquet Automation</h1>
            <div class="subtitle">DuckDB • Live Log • Network Output</div>
        </div>
        <button class="runall" onclick="runAll()">▶ RUN ALL</button>
    </div>

    <div class="card">
        <h3>Jobs</h3>
        <div id="jobs" class="jobs"></div>
    </div>

    <div class="card">
        <h3>Current Job</h3>
        <div class="current">
            <div class="metric">
                <div class="metric-label">JOB</div>
                <div id="currentJob" class="metric-value">—</div>
            </div>

            <div class="metric">
                <div class="metric-label">INPUT</div>
                <div id="inputFile" class="metric-value">—</div>
            </div>

            <div class="metric">
                <div class="metric-label">OUTPUT</div>
                <div id="outputFile" class="metric-value">—</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h3>Live Log</h3>
        <div id="logs" class="log-box">
            <div class="empty">Chưa có log.</div>
        </div>
    </div>

</div>

<script>
let selectedJob = null;

function escapeHtml(text) {
    return String(text ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

async function runJob(name) {
    try {
        const response = await fetch(
            "/api/run/" + encodeURIComponent(name),
            { method: "POST" }
        );

        const data = await response.json();

        if (!response.ok) {
            alert(data.detail || "Không thể chạy job.");
            return;
        }

        selectedJob = name;
        refresh();
    } catch (e) {
        alert("Không kết nối được server.");
    }
}

async function runAll() {
    try {
        const response = await fetch(
            "/api/run-all",
            { method: "POST" }
        );

        const data = await response.json();

        if (!response.ok) {
            alert(data.detail || "Không thể RUN ALL.");
            return;
        }

        selectedJob = null;
        refresh();
    } catch (e) {
        alert("Không kết nối được server.");
    }
}

function render(data) {
    const jobs = data.jobs;
    const current = data.current_job;

    document.getElementById("currentJob").textContent = current || "—";

    let html = "";

    for (const [name, job] of Object.entries(jobs)) {
        const disabled =
            current !== null &&
            current !== name &&
            job.status === "RUNNING";

        html += `
            <div class="job">
                <div class="job-name">${escapeHtml(name)}</div>
                <span class="status ${escapeHtml(job.status)}">
                    ${escapeHtml(job.status)}
                </span>
                <button
                    class="run"
                    onclick="runJob('${escapeHtml(name)}')"
                    ${disabled ? "disabled" : ""}
                >
                    ▶ RUN
                </button>
            </div>
        `;
    }

    document.getElementById("jobs").innerHTML = html;

    let logJob = selectedJob || current;

    if (!logJob) {
        for (const [name, job] of Object.entries(jobs)) {
            if (job.logs.length) {
                logJob = name;
                break;
            }
        }
    }

    if (logJob && jobs[logJob]) {
        const job = jobs[logJob];

        document.getElementById("inputFile").textContent =
            job.input || "—";

        document.getElementById("outputFile").textContent =
            job.output || "—";

        const logBox = document.getElementById("logs");

        if (!job.logs.length) {
            logBox.innerHTML =
                '<div class="empty">Chưa có log.</div>';
        } else {
            logBox.innerHTML = job.logs.map(item => `
                <div class="log-line">
                    <span class="log-time">[${escapeHtml(item.time)}]</span>
                    <span class="log-message">
                        ${escapeHtml(item.message)}
                    </span>
                </div>
            `).join("");

            logBox.scrollTop = logBox.scrollHeight;
        }
    }
}

async function refresh() {
    try {
        const response = await fetch("/api/status");
        const data = await response.json();
        render(data);
    } catch (e) {
        // Server temporarily unavailable.
    }
}

refresh();
setInterval(refresh, 1000);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    print("==============================================")
    print("CSV → PARQUET WEB SERVER")
    print("==============================================")
    print("Open: http://127.0.0.1:8000")
    print("For LAN: http://<IP-MAY-B>:8000")
    print("==============================================")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )