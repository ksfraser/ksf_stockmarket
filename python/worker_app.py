"""Thin FastAPI worker for stock market task execution."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="KSF Stock Market Python Worker")

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_SCRIPT = SCRIPT_DIR / "fetch_prices.py"


class RefreshRequest(BaseModel):
    symbol: Optional[str] = None
    full_history: bool = False
    days: Optional[int] = None


@app.get("/health")
def health() -> dict:
    return {"service": "ksf-python-worker", "status": "ok"}


@app.post("/worker/refresh_prices")
def refresh_prices(req: RefreshRequest) -> dict:
    cmd = [sys.executable, str(PYTHON_SCRIPT)]
    if req.symbol:
        cmd.extend(["--symbols", req.symbol.strip().upper()])
    if req.full_history:
        cmd.append("--full-history")
    if req.days and req.days > 0:
        cmd.extend(["--days", str(req.days)])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,
            cwd=str(SCRIPT_DIR),
        )
        if proc.returncode != 0:
            return {
                "status": "error",
                "returncode": proc.returncode,
                "stderr": proc.stderr[-1000:],
                "stdout": proc.stdout[-1000:],
            }
        return {
            "status": "queued",
            "stdout": proc.stdout[-1000:],
        }
    except Exception as e:  # pragma: no cover
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("WORKER_PORT", 8000)))
