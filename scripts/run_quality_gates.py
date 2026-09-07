"""Local quality gate runner executing the full mandatory CI validation suite (DEV-005)."""

import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

GATES: list[tuple[str, list[str]]] = [
    (
        "Stage 1: Ruff Lint Check",
        [sys.executable, "-m", "ruff", "check", "app", "tests", "simulators", "alembic", "scripts"],
    ),
    (
        "Stage 2: Ruff Formatting Check",
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--check",
            "app",
            "tests",
            "simulators",
            "alembic",
            "scripts",
        ],
    ),
    (
        "Stage 3: Mypy Static Type Check",
        [sys.executable, "-m", "mypy", "app", "simulators", "tests", "scripts"],
    ),
    (
        "Stage 4: Secret and Privacy Scan",
        [sys.executable, "scripts/scan_secrets.py"],
    ),
    (
        "Stage 5: Schema Drift Verification",
        [sys.executable, "scripts/export_schemas.py", "--check"],
    ),
    (
        "Stage 6: Application Boot & Smoke Checks",
        [sys.executable, "scripts/smoke_check.py"],
    ),
    (
        "Stage 7: Database Migration Cycle Tests",
        [sys.executable, "-m", "pytest", "tests/migration", "-v"],
    ),
    (
        "Stage 8: Contract & Architecture Guard Tests",
        [sys.executable, "-m", "pytest", "tests/contract", "tests/provider_contract", "-v"],
    ),
    (
        "Stage 9: Unit & Integration Test Suite",
        [sys.executable, "-m", "pytest", "tests/unit", "tests/integration", "-q"],
    ),
]


def run_all_gates() -> int:
    print("=" * 70)
    print("TOKI QUALITY GATES RUNNER — Mandatory Pre-Merge Verification (DEV-005)")
    print("=" * 70)

    total_start = time.perf_counter()
    timings: list[tuple[str, float, bool]] = []
    overall_success = True

    for name, cmd in GATES:
        print(f"\n[RUNNING] {name}...")
        stage_start = time.perf_counter()
        res = subprocess.run(cmd, cwd=REPO_ROOT)
        stage_duration = time.perf_counter() - stage_start

        if res.returncode == 0:
            print(f"[PASS] {name} completed in {stage_duration:.2f}s")
            timings.append((name, stage_duration, True))
        else:
            print(f"[FAIL] {name} failed with exit code {res.returncode} in {stage_duration:.2f}s")
            timings.append((name, stage_duration, False))
            overall_success = False
            break

    total_duration = time.perf_counter() - total_start
    print("\n" + "=" * 70)
    print("QUALITY GATES SUMMARY")
    print("=" * 70)
    for name, dur, success in timings:
        status = "PASS" if success else "FAIL"
        print(f"  [{status:4s}] {name:48s} : {dur:6.2f}s")

    print("-" * 70)
    print(f"Total Duration: {total_duration:.2f}s")

    if overall_success:
        print("\nALL MANDATORY QUALITY GATES PASSED! Repository is healthy and merge-ready.")
        return 0

    print("\nERROR: Quality gates failed. Fix the issues above before merging or handing off.")
    return 1


if __name__ == "__main__":
    sys.exit(run_all_gates())
