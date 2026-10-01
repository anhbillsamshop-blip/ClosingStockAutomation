from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PIPELINE = PROJECT_ROOT / "app" / "run_All.py"

Log = Callable[[str], None]


def run_all(logger: Log = print) -> dict:
    """Run the production pipeline while streaming its logs to the UI.

    The frontend and its API stay unchanged. Only the implementation behind
    the Run All action is delegated to app/run_All.py.
    """

    if not PIPELINE.is_file():
        raise FileNotFoundError(f"Không tìm thấy pipeline: {PIPELINE}")

    process = subprocess.Popen(
        [sys.executable, "-u", str(PIPELINE)],
        cwd=str(PIPELINE.parent),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    # run_All.py forwards Enter to child scripts when they display their
    # error prompt. Supplying it here prevents the UI worker from hanging.
    if process.stdin is not None:
        process.stdin.write("\n")
        process.stdin.close()

    logs: list[str] = []
    if process.stdout is not None:
        for line in process.stdout:
            message = line.rstrip("\r\n")
            if message:
                logs.append(message)
                logger(message)

    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(
            f"Pipeline chạy không thành công. Return code = {return_code}"
        )

    return {
        "success": True,
        "returncode": return_code,
        "logs": logs,
    }


if __name__ == "__main__":
    run_all()
