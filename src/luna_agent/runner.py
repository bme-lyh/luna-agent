from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .models import EFFORTS, MAX_WORKERS, MODEL, JobSpec, RunResult

_WORKER_PREAMBLE = """You are an isolated GPT-5.6 Luna worker launched by Luna Agent.
Complete only the bounded task below.
Do not create, invoke, or delegate to any subagent or nested Codex process.
Respect the configured sandbox. Do not broaden scope, hide failures, or claim checks you did not run.
Return a concise result with relevant evidence.

Bounded task:
"""


def resolve_codex(executable: str) -> str:
    resolved = shutil.which(executable)
    if resolved is None:
        raise FileNotFoundError(f"Codex executable was not found: {executable}")
    return resolved


def build_command(job: JobSpec, codex_executable: str = "codex") -> list[str]:
    codex = resolve_codex(codex_executable)
    command = [
        codex,
        "--ask-for-approval",
        "never",
        "--cd",
        str(job.workspace),
        "--model",
        MODEL,
        "--config",
        f'model_reasoning_effort="{job.effort}"',
        "--config",
        f'service_tier="{job.service_tier}"',
        "--config",
        "features.fast_mode=true",
        "--config",
        "features.multi_agent=false",
        "--config",
        "agents.enabled=false",
        "--sandbox",
        job.sandbox,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--json",
        "--color",
        "never",
    ]
    if job.skip_git_repo_check:
        command.append("--skip-git-repo-check")
    command.append("-")
    return command


def sanitized_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ if source is None else source)
    environment.pop("OPENAI_API_KEY", None)
    environment.pop("CODEX_API_KEY", None)
    return environment


def _parse_json_stream(
    stdout: str,
) -> tuple[str | None, dict[str, Any], str, str | None]:
    thread_id: str | None = None
    usage: dict[str, Any] = {}
    messages: list[str] = []
    errors: list[str] = []

    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_type = event.get("type")
        if event_type == "thread.started":
            value = event.get("thread_id")
            if isinstance(value, str):
                thread_id = value
        elif event_type == "item.completed":
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    messages.append(text.strip())
        elif event_type == "turn.completed":
            value = event.get("usage")
            if isinstance(value, dict):
                usage = value
        elif event_type in {"turn.failed", "error"}:
            value = event.get("error") or event.get("message")
            if isinstance(value, dict):
                value = value.get("message") or json.dumps(value, ensure_ascii=False)
            if value:
                errors.append(str(value))

    final_message = messages[-1] if messages else ""
    error = "; ".join(errors) if errors else None
    return thread_id, usage, final_message, error


def run_job(job: JobSpec, codex_executable: str = "codex") -> RunResult:
    started = time.perf_counter()
    service_tier = job.service_tier
    try:
        command = build_command(job, codex_executable)
    except (FileNotFoundError, ValueError) as exc:
        return RunResult(
            job_id=job.job_id,
            speed=job.speed,
            service_tier=service_tier,
            effort=job.effort,
            sandbox=job.sandbox,
            elapsed_seconds=time.perf_counter() - started,
            return_code=127,
            error=str(exc),
        )

    prompt = _WORKER_PREAMBLE + job.task + "\n"
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        completed = subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=sanitized_environment(),
            timeout=job.timeout_seconds,
            check=False,
            creationflags=creation_flags,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = _coerce_text(exc.stdout)
        stderr = _coerce_text(exc.stderr)
        thread_id, usage, final_message, stream_error = _parse_json_stream(stdout)
        error = f"worker timed out after {job.timeout_seconds} seconds"
        if stream_error:
            error = f"{error}; {stream_error}"
        return RunResult(
            job_id=job.job_id,
            speed=job.speed,
            service_tier=service_tier,
            effort=job.effort,
            sandbox=job.sandbox,
            elapsed_seconds=time.perf_counter() - started,
            return_code=124,
            final_message=final_message,
            thread_id=thread_id,
            usage=usage,
            error=error,
            stderr=stderr.strip(),
        )
    except OSError as exc:
        return RunResult(
            job_id=job.job_id,
            speed=job.speed,
            service_tier=service_tier,
            effort=job.effort,
            sandbox=job.sandbox,
            elapsed_seconds=time.perf_counter() - started,
            return_code=126,
            error=f"could not start Codex: {exc}",
        )

    thread_id, usage, final_message, stream_error = _parse_json_stream(completed.stdout)
    error = stream_error
    if completed.returncode != 0 and error is None:
        error = (
            completed.stderr.strip() or f"Codex exited with code {completed.returncode}"
        )
    elif completed.returncode == 0 and not final_message and error is None:
        error = "Codex completed without a final agent message"

    return RunResult(
        job_id=job.job_id,
        speed=job.speed,
        service_tier=service_tier,
        effort=job.effort,
        sandbox=job.sandbox,
        elapsed_seconds=time.perf_counter() - started,
        return_code=completed.returncode,
        final_message=final_message,
        thread_id=thread_id,
        usage=usage,
        error=error,
        stderr=completed.stderr.strip(),
    )


def _coerce_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run_jobs(
    jobs: Iterable[JobSpec],
    codex_executable: str = "codex",
    max_workers: int = MAX_WORKERS,
) -> list[RunResult]:
    job_list = list(jobs)
    if not job_list:
        raise ValueError("at least one job is required")
    if not 1 <= max_workers <= MAX_WORKERS:
        raise ValueError(f"max workers must be between 1 and {MAX_WORKERS}")
    identifiers = [job.job_id for job in job_list]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("job ids must be unique")

    results: list[RunResult | None] = [None] * len(job_list)
    worker_count = min(max_workers, len(job_list))
    with ThreadPoolExecutor(
        max_workers=worker_count, thread_name_prefix="luna-agent"
    ) as pool:
        futures = {
            pool.submit(run_job, job, codex_executable): index
            for index, job in enumerate(job_list)
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return [result for result in results if result is not None]


def doctor(codex_executable: str = "codex", check_login: bool = True) -> dict[str, Any]:
    report: dict[str, Any] = {
        "codex_found": False,
        "logged_in": None,
        "model": MODEL,
        "model_found": False,
        "efforts": [],
        "fast_supported": False,
        "ready": False,
    }
    try:
        codex = resolve_codex(codex_executable)
    except FileNotFoundError as exc:
        report["error"] = str(exc)
        return report
    report["codex_found"] = True

    version = subprocess.run(
        [codex, "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    report["codex_version"] = (version.stdout or version.stderr).strip()

    exec_help = subprocess.run(
        [codex, "exec", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    help_text = exec_help.stdout or exec_help.stderr
    required_flags = ("--ignore-user-config", "--ephemeral", "--json")
    report["exec_flags_ready"] = exec_help.returncode == 0 and all(
        flag in help_text for flag in required_flags
    )
    if not report["exec_flags_ready"]:
        report["error"] = "Codex is too old for isolated workers; update Codex"
        return report

    if check_login:
        login = subprocess.run(
            [codex, "login", "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        report["logged_in"] = login.returncode == 0
        report["login_status"] = (login.stdout or login.stderr).strip()

    catalog = subprocess.run(
        [codex, "debug", "models", "--bundled"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if catalog.returncode != 0:
        report["error"] = (
            catalog.stderr.strip() or "could not read bundled model catalog"
        )
        return report
    try:
        data = json.loads(catalog.stdout)
    except json.JSONDecodeError as exc:
        report["error"] = f"invalid model catalog JSON: {exc}"
        return report

    model = next(
        (item for item in data.get("models", []) if item.get("slug") == MODEL), None
    )
    if model is None:
        report["error"] = f"{MODEL} is missing from the bundled model catalog"
        return report
    report["model_found"] = True
    efforts = [
        item.get("effort")
        for item in model.get("supported_reasoning_levels", [])
        if isinstance(item, dict) and isinstance(item.get("effort"), str)
    ]
    report["efforts"] = efforts
    report["fast_supported"] = "fast" in model.get("additional_speed_tiers", [])
    capabilities_ready = (
        all(effort in efforts for effort in EFFORTS) and report["fast_supported"]
    )
    login_ready = report["logged_in"] is not False
    report["ready"] = bool(
        capabilities_ready and login_ready and report["exec_flags_ready"]
    )
    if not capabilities_ready:
        report["error"] = "Luna does not advertise every required effort and Fast mode"
    elif not login_ready:
        report["error"] = "Codex is not logged in"
    return report
