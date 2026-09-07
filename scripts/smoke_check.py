"""Smoke check script verifying application boot, profile loading, and health endpoints."""

import asyncio
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from app.main import app


async def run_smoke_checks() -> None:
    print("Running TOKI Backend startup smoke checks...")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        # Check root endpoint
        root_res = await client.get("/")
        if root_res.status_code != 200:
            print(f"FAILED: Root returned status {root_res.status_code}")
            sys.exit(1)
        print(f"OK: Root endpoint operational: {root_res.json()}")

        # Check /health/live
        live_res = await client.get("/health/live")
        if live_res.status_code != 200 or live_res.json().get("status") != "LIVE":
            print(f"FAILED: /health/live returned {live_res.status_code}: {live_res.text}")
            sys.exit(1)
        print(f"OK: /health/live returned LIVE: {live_res.json()}")

        # Check /health/demo
        demo_res = await client.get("/health/demo")
        if demo_res.status_code != 200:
            print(f"FAILED: /health/demo returned {demo_res.status_code}: {demo_res.text}")
            sys.exit(1)
        print(f"OK: /health/demo returned status: {demo_res.json().get('status')}")

    print("ALL SMOKE CHECKS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(run_smoke_checks())
