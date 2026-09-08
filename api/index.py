import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

import urllib.request
import urllib.error


app = FastAPI(title="CSV Parquet Control API")


UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
WORKER_TOKEN = os.getenv("WORKER_TOKEN", "")
DEVICE_ID = os.getenv("DEVICE_ID", "CASE-01")

JOB_NAMES = [
    "CLOSING_STOCK",
    "30D_SALES",
    "STOCK_INTRANSIT",
    "SCCT_RAWDATA_LD_WMP",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def redis_request(command: list[Any]) -> Any:
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        raise RuntimeError(
            "Thiếu UPSTASH_REDIS_REST_URL hoặc "
            "UPSTASH_REDIS_REST_TOKEN."
        )

    payload = json.dumps(command).encode("utf-8")
    request = urllib.request.Request(
        UPSTASH_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {UPSTASH_TOKEN}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Redis HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"Redis connection error: {exc}") from exc

    if "error" in body:
        raise RuntimeError(str(body["error"]))

    return body.get("result")


def redis_pipeline(commands: list[list[Any]]) -> list[Any]:
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        raise RuntimeError("Thiếu Upstash Redis environment variables.")

    payload = json.dumps(commands).encode("utf-8")
    request = urllib.request.Request(
        f"{UPSTASH_URL}/pipeline",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {UPSTASH_TOKEN}",
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        body = json.loads(response.read().decode("utf-8"))

    for item in body:
        if "error" in item:
            raise RuntimeError(str(item["error"]))

    return [item.get("result") for item in body]


def get_json(key: str, default: Any = None) -> Any:
    result = redis_request(["GET", key])
    if result is None:
        return default

    try:
        return json.loads(result)
    except Exception:
        return result


def set_json(key: str, value: Any, ttl_seconds: int | None = None):
    encoded = json.dumps(value, ensure_ascii=False)

    if ttl_seconds:
        return redis_request(["SET", key, encoded, "EX", ttl_seconds])

    return redis_request(["SET", key, encoded])


def require_worker_token(authorization: str | None):
    expected = WORKER_TOKEN

    if not expected:
        raise HTTPException(
            status_code=500,
            detail="WORKER_TOKEN chưa được cấu hình trên Vercel.",
        )

    received = (authorization or "").strip()

    if received.startswith("Bearer "):
        received = received[7:].strip()

    if received != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def validate_job(job: str):
    if job not in JOB_NAMES:
        raise HTTPException(status_code=404, detail="Job không tồn tại.")


def command_key(device: str) -> str:
    return f"csvpa:{device}:commands"


def state_key(device: str) -> str:
    return f"csvpa:{device}:state"


def logs_key(device: str, job: str) -> str:
    return f"csvpa:{device}:logs:{job}"


def save_log(device: str, job: str, message: str):
    item = {
        "id": str(uuid.uuid4()),
        "time": datetime.now().astimezone().strftime("%H:%M:%S"),
        "message": message,
    }

    key = logs_key(device, job)

    # RPUSH + LTRIM keeps only the latest 1000 lines.
    redis_pipeline([
        ["RPUSH", key, json.dumps(item, ensure_ascii=False)],
        ["LTRIM", key, -1000, -1],
        ["EXPIRE", key, 86400],
    ])


def get_logs(device: str, job: str):
    raw = redis_request(["LRANGE", logs_key(device, job), 0, -1])
    result = []

    for item in raw or []:
        try:
            result.append(json.loads(item))
        except Exception:
            result.append({
                "time": "",
                "message": str(item),
            })

    return result


def push_command(device: str, command: str, job: str | None = None):
    payload = {
        "id": str(uuid.uuid4()),
        "command": command,
        "job": job,
        "created_at": now_iso(),
    }

    redis_request([
        "RPUSH",
        command_key(device),
        json.dumps(payload, ensure_ascii=False),
    ])

    return payload


# -------------------------
# Browser API
# -------------------------

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "csv-parquet-control",
        "time": now_iso(),
    }


@app.get("/api/jobs")
def jobs():
    state = get_json(state_key(DEVICE_ID), {
        "device_id": DEVICE_ID,
        "online": False,
        "status": "OFFLINE",
        "current_job": None,
        "jobs": {},
    })

    return state


@app.get("/api/logs/{job}")
def logs(job: str):
    validate_job(job)
    return {
        "job": job,
        "logs": get_logs(DEVICE_ID, job),
    }


@app.post("/api/run/{job}")
def run(job: str):
    validate_job(job)

    state = get_json(state_key(DEVICE_ID), {})

    if state.get("status") == "RUNNING":
        raise HTTPException(
            status_code=409,
            detail=f"Máy B đang chạy {state.get('current_job')}.",
        )

    # Clear old log before starting.
    redis_request(["DEL", logs_key(DEVICE_ID, job)])

    command = push_command(DEVICE_ID, "RUN", job)

    return {
        "ok": True,
        "message": f"Đã gửi RUN {job} tới máy B.",
        "command_id": command["id"],
    }


@app.post("/api/run-all")
def run_all():
    state = get_json(state_key(DEVICE_ID), {})

    if state.get("status") == "RUNNING":
        raise HTTPException(
            status_code=409,
            detail=f"Máy B đang chạy {state.get('current_job')}.",
        )

    for job in JOB_NAMES:
        redis_request(["DEL", logs_key(DEVICE_ID, job)])

    command = push_command(DEVICE_ID, "RUN_ALL")

    return {
        "ok": True,
        "message": "Đã gửi RUN ALL tới máy B.",
        "command_id": command["id"],
    }


@app.post("/api/stop")
def stop():
    state = get_json(state_key(DEVICE_ID), {})

    if state.get("status") != "RUNNING":
        return {
            "ok": True,
            "message": "Máy B hiện không chạy job.",
        }

    command = push_command(DEVICE_ID, "STOP")

    return {
        "ok": True,
        "message": "Đã gửi STOP tới máy B.",
        "command_id": command["id"],
    }


@app.post("/api/shutdown")
def shutdown():
    command = push_command(DEVICE_ID, "SHUTDOWN")

    return {
        "ok": True,
        "message": "Đã gửi SHUTDOWN tới máy B.",
        "command_id": command["id"],
    }


# -------------------------
# Worker API
# -------------------------

@app.get("/api/worker/next")
def worker_next(authorization: str | None = Header(default=None)):
    require_worker_token(authorization)

    raw = redis_request(["LPOP", command_key(DEVICE_ID)])

    if not raw:
        return {"command": None}

    return {"command": json.loads(raw)}


@app.post("/api/worker/status")
def worker_status(
    body: dict,
    authorization: str | None = Header(default=None),
):
    require_worker_token(authorization)

    body["device_id"] = DEVICE_ID
    body["last_seen"] = now_iso()

    set_json(state_key(DEVICE_ID), body, ttl_seconds=120)

    return {"ok": True}


@app.post("/api/worker/log")
def worker_log(
    body: dict,
    authorization: str | None = Header(default=None),
):
    require_worker_token(authorization)

    job = body.get("job")
    message = body.get("message", "")

    if not job:
        raise HTTPException(status_code=400, detail="Thiếu job.")

    validate_job(job)
    save_log(DEVICE_ID, job, message)
