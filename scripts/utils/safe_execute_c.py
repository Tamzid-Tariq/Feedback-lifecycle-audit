#!/usr/bin/env python3
"""Execute C programs in a locked-down Docker container and record evidence.

The outer timeout protects the host's interaction with Docker. It is
deliberately independent of ``PROGRAM_TIMEOUT_SECONDS``, which constrains the
student executable. A source state is compiled once in a single ephemeral
container, then each official test is run through ``docker exec`` so every
test retains its own program and host-timeout evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IMAGE = "revground-c-runner:2.0"
TEMP_ROOT = Path(__file__).resolve().parent / ".runner_tmp"
HOST_TIMEOUT_SECONDS = 60
PROGRAM_TIMEOUT_SECONDS = 2
COMPILER = "gcc -std=c11 -O0 -Wall -Wextra -Werror=return-type"


def digest(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize(value: str) -> str:
    return value.replace("\r\n", "\n").rstrip()


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def base_args(image: str = IMAGE) -> list[str]:
    return [
        "docker", "run", "--rm", "-i", "--network", "none", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "64",
        "--memory", "256m", "--memory-swap", "256m", "--cpus", "0.5",
        "--ulimit", "fsize=1048576:1048576",
        "--tmpfs", "/work:rw,exec,nosuid,nodev,size=32m,uid=10001,gid=10001",
        "--user", "10001:10001", image,
    ]


def temporary_directory(prefix: str) -> tempfile.TemporaryDirectory[str]:
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(prefix=prefix, dir=TEMP_ROOT)


def compile_args(source: str | Path, image: str = IMAGE) -> list[str]:
    """Return the one-shot compile command used by the compile-only utility."""
    src = Path(source).resolve()
    return base_args(image)[:-1] + [
        "--mount", f"type=bind,src={src.parent},dst=/input,readonly", image,
        f"{COMPILER} /input/{src.name} -o /work/program && sha256sum /work/program",
    ]


def validate_tests(obj: object) -> None:
    if not isinstance(obj, list) or not obj:
        raise ValueError("tests must be a non-empty list")
    seen: set[str] = set()
    for test in obj:
        if not isinstance(test, dict) or set(test) != {"test_id", "input", "expected_output"}:
            raise ValueError("invalid test record")
        if not all(isinstance(test[key], str) for key in test):
            raise ValueError("invalid test record")
        if not test["test_id"] or test["test_id"] in seen:
            raise ValueError("duplicate/empty test_id")
        seen.add(test["test_id"])


def compiler_result_from_process(process: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "compiler": COMPILER,
        "status": "compile_success" if process.returncode == 0 else "compile_error",
        "exit_code": process.returncode,
        "timed_out": False,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


def infra_timeout_compiler_result(error: subprocess.TimeoutExpired) -> dict[str, Any]:
    return {
        "compiler": COMPILER,
        "status": "infra_timeout",
        "exit_code": None,
        "timed_out": True,
        "stdout": _text(error.stdout),
        "stderr": _text(error.stderr),
    }


def compile_source(source: str | Path, image: str = IMAGE, timeout: int = HOST_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Compile one source file in the locked-down environment.

    This is retained for a compile-only diagnostic. State replay uses
    :func:`run_state`, which compiles once and retains that binary for all
    tests instead of calling this function and recompiling per test.
    """
    source_path = Path(source).resolve()
    with temporary_directory(prefix="feedback-lifecycle-audit_compile_") as directory:
        isolated = Path(directory) / "program.c"
        shutil.copyfile(source_path, isolated)
        command = base_args(image)[:-1] + [
            "--mount", f"type=bind,src={Path(directory).resolve()},dst=/input,readonly", image,
            f"{COMPILER} /input/program.c -o /work/program",
        ]
        try:
            process = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as error:
            return infra_timeout_compiler_result(error)
    return compiler_result_from_process(process)


def _container_args(container_name: str, source_directory: Path, image: str) -> list[str]:
    """Start an ephemeral isolated container that remains alive for test execs."""
    return [
        "docker", "run", "--rm", "-d", "--name", container_name, "--network", "none",
        "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--pids-limit", "64", "--memory", "256m", "--memory-swap", "256m", "--cpus", "0.5",
        "--ulimit", "fsize=1048576:1048576",
        "--tmpfs", "/work:rw,exec,nosuid,nodev,size=32m,uid=10001,gid=10001",
        "--user", "10001:10001",
        "--mount", f"type=bind,src={source_directory.resolve()},dst=/input,readonly",
        image, "while :; do sleep 2147483647; done",
    ]


def _remove_container(container_name: str) -> None:
    # It is a UUID-derived name created by this process; cleanup never targets a
    # user container. Errors are intentionally ignored after a host timeout.
    subprocess.run(
        ["docker", "rm", "-f", container_name], text=True, capture_output=True,
        timeout=HOST_TIMEOUT_SECONDS, check=False,
    )


def not_run_compile_error(test: dict[str, str]) -> dict[str, Any]:
    return {
        "test_id": test["test_id"], "status": "NOT_RUN_COMPILE_ERROR", "returncode": None,
        "stdout": "", "stderr": "", "expected_output": test["expected_output"],
        "exact_match": False, "normalized_match": False, "latency_ms": 0.0,
    }


def test_result_from_process(test: dict[str, str], process: subprocess.CompletedProcess[str], latency_ms: float) -> dict[str, Any]:
    if process.returncode == 0:
        status = "PASS" if normalize(process.stdout) == normalize(test["expected_output"]) else "FAIL"
    elif process.returncode == 124:
        status = "PROGRAM_TIMEOUT"
    else:
        status = "RUNTIME_ERROR"
    return {
        "test_id": test["test_id"], "status": status, "returncode": process.returncode,
        "stdout": process.stdout, "stderr": process.stderr, "expected_output": test["expected_output"],
        "exact_match": process.stdout == test["expected_output"],
        "normalized_match": normalize(process.stdout) == normalize(test["expected_output"]),
        "latency_ms": round(latency_ms, 2),
    }


def infra_timeout_test_result(test: dict[str, str], error: subprocess.TimeoutExpired, latency_ms: float) -> dict[str, Any]:
    return {
        "test_id": test["test_id"], "status": "INFRA_TIMEOUT", "returncode": None,
        "stdout": _text(error.stdout), "stderr": _text(error.stderr), "expected_output": test["expected_output"],
        "exact_match": False, "normalized_match": False, "latency_ms": round(latency_ms, 2),
    }


def run_state(
    source: str | Path, tests: list[dict[str, str]], image: str = IMAGE,
    host_timeout: int = HOST_TIMEOUT_SECONDS, program_timeout: int = PROGRAM_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Compile exactly once, then run every test under an individual inner limit."""
    validate_tests(tests)
    if host_timeout < 1 or program_timeout < 1:
        raise ValueError("timeouts must be positive")
    source_path = Path(source).resolve()
    container_name = f"feedback-lifecycle-audit-state-{uuid.uuid4().hex}"
    started = False
    with temporary_directory(prefix="feedback-lifecycle-audit_state_") as directory:
        isolated = Path(directory) / "program.c"
        shutil.copyfile(source_path, isolated)
        try:
            try:
                start = subprocess.run(
                    _container_args(container_name, Path(directory), image), text=True, capture_output=True,
                    timeout=host_timeout, check=False,
                )
            except subprocess.TimeoutExpired as error:
                return {"compiler_result": infra_timeout_compiler_result(error), "tests": None}
            if start.returncode != 0:
                return {
                    "compiler_result": {
                        "compiler": COMPILER, "status": "infra_timeout", "exit_code": None,
                        "timed_out": True, "stdout": start.stdout, "stderr": start.stderr,
                    },
                    "tests": None,
                }
            started = True
            try:
                compiled = subprocess.run(
                    ["docker", "exec", "--user", "10001:10001", container_name, "sh", "-lc",
                     f"{COMPILER} /input/program.c -o /work/program"],
                    text=True, capture_output=True, timeout=host_timeout, check=False,
                )
            except subprocess.TimeoutExpired as error:
                return {"compiler_result": infra_timeout_compiler_result(error), "tests": None}
            compiler_result = compiler_result_from_process(compiled)
            if compiler_result["status"] == "compile_error":
                return {"compiler_result": compiler_result, "tests": [not_run_compile_error(test) for test in tests]}
            results: list[dict[str, Any]] = []
            for test in tests:
                command = [
                    "docker", "exec", "-i", "--user", "10001:10001", container_name,
                    "timeout", f"{program_timeout}s", "/work/program",
                ]
                started_at = time.perf_counter()
                try:
                    process = subprocess.run(
                        command, input=test["input"], text=True, capture_output=True,
                        timeout=host_timeout, check=False,
                    )
                    results.append(test_result_from_process(test, process, (time.perf_counter() - started_at) * 1000))
                except subprocess.TimeoutExpired as error:
                    results.append(infra_timeout_test_result(test, error, (time.perf_counter() - started_at) * 1000))
            return {"compiler_result": compiler_result, "tests": results}
        finally:
            if started:
                _remove_container(container_name)


def run(
    source: str | Path, tests: list[dict[str, str]], output: str | Path, image: str = IMAGE,
    timeout: int = HOST_TIMEOUT_SECONDS, program_timeout: int = PROGRAM_TIMEOUT_SECONDS,
) -> None:
    """Write one source-state replay result; maintained as the CLI-compatible API."""
    result = run_state(source, tests, image=image, host_timeout=timeout, program_timeout=program_timeout)
    evidence = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "image": image,
        "source_sha256": digest(source),
        "security": {
            "network": "none", "read_only_root": True, "capabilities": "all dropped",
            "no_new_privileges": True, "pids": 64, "memory": "256m", "cpus": "0.5",
        },
        "host_timeout_seconds": timeout, "program_timeout_seconds": program_timeout,
        "compiler_result": result["compiler_result"], "tests": result["tests"],
        "interpretation": "Only FAIL is a completed wrong-answer witness; infrastructure timeouts are not program outcomes.",
    }
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--tests", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--image", default=IMAGE)
    parser.add_argument("--host-timeout", type=int, default=HOST_TIMEOUT_SECONDS)
    parser.add_argument("--program-timeout", type=int, default=PROGRAM_TIMEOUT_SECONDS)
    args = parser.parse_args()
    run(
        args.source, json.loads(Path(args.tests).read_text(encoding="utf-8")), args.output, args.image,
        timeout=args.host_timeout, program_timeout=args.program_timeout,
    )


if __name__ == "__main__":
    main()
