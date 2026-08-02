from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, TypeVar

from . import __version__
from .models import (
    DEFAULT_EFFORT,
    DEFAULT_SANDBOX,
    DEFAULT_SPEED,
    DEFAULT_TIMEOUT_SECONDS,
    EFFORTS,
    MAX_WORKERS,
    SANDBOXES,
    SPEEDS,
    JobSpec,
    RunResult,
)
from .runner import doctor, run_job, run_jobs

_T = TypeVar("_T")
_SPEED_TEST_MARKER = "LUNA_SPEED_TEST_OK"
_SPEED_TEST_TASK = (
    f"Reply with exactly {_SPEED_TEST_MARKER} and nothing else. "
    "Do not use tools and do not add punctuation or Markdown."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="luna-agent",
        description="Run isolated GPT-5.6 Luna workers with per-task speed settings.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run one isolated Luna worker")
    run_parser.add_argument("task", nargs="?", help="bounded task for the worker")
    run_parser.add_argument(
        "--task-file", type=Path, help="read the task from a UTF-8 file"
    )
    run_parser.add_argument("--id", default="worker-1", help="result id")
    _add_job_options(run_parser)
    run_parser.add_argument("--json", action="store_true", help="print structured JSON")
    run_parser.set_defaults(handler=_handle_run)

    batch_parser = subparsers.add_parser(
        "batch", help="run up to four workers concurrently"
    )
    batch_parser.add_argument(
        "--manifest", type=Path, help="JSON manifest containing a jobs array"
    )
    batch_parser.add_argument(
        "--task", action="append", help="worker task; repeat for more workers"
    )
    batch_parser.add_argument(
        "--id", action="append", help="job id; one value or one per task"
    )
    batch_parser.add_argument("--speed", action="append", choices=SPEEDS)
    batch_parser.add_argument("--effort", action="append", choices=EFFORTS)
    batch_parser.add_argument("--sandbox", action="append", choices=SANDBOXES)
    batch_parser.add_argument("--timeout", action="append", type=int, dest="timeouts")
    batch_parser.add_argument("--workspace", type=Path, default=None)
    batch_parser.add_argument("--max-workers", type=int, default=None)
    batch_parser.add_argument("--codex", default="codex")
    batch_parser.add_argument("--skip-git-repo-check", action="store_true")
    batch_parser.add_argument(
        "--json", action="store_true", help="print structured JSON"
    )
    batch_parser.set_defaults(handler=_handle_batch)

    verify_parser = subparsers.add_parser(
        "verify-speeds", help="run the same fixed task once at each speed"
    )
    verify_parser.add_argument("--workspace", type=Path, default=Path.cwd())
    verify_parser.add_argument("--effort", choices=EFFORTS, default=DEFAULT_EFFORT)
    verify_parser.add_argument("--timeout", type=int, default=600)
    verify_parser.add_argument("--codex", default="codex")
    verify_parser.add_argument("--skip-git-repo-check", action="store_true")
    verify_parser.add_argument(
        "--json", action="store_true", help="print structured JSON"
    )
    verify_parser.set_defaults(handler=_handle_verify_speeds)

    doctor_parser = subparsers.add_parser(
        "doctor", help="check Codex login and Luna support"
    )
    doctor_parser.add_argument("--codex", default="codex")
    doctor_parser.add_argument("--skip-login", action="store_true")
    doctor_parser.add_argument(
        "--json", action="store_true", help="print structured JSON"
    )
    doctor_parser.set_defaults(handler=_handle_doctor)
    return parser


def _add_job_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--speed", choices=SPEEDS, default=DEFAULT_SPEED)
    parser.add_argument("--effort", choices=EFFORTS, default=DEFAULT_EFFORT)
    parser.add_argument("--sandbox", choices=SANDBOXES, default=DEFAULT_SANDBOX)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--skip-git-repo-check", action="store_true")


def _read_task(task: str | None, task_file: Path | None) -> str:
    if task and task_file:
        raise ValueError("use either a task argument or --task-file, not both")
    if task_file:
        return task_file.read_text(encoding="utf-8")
    if task:
        return task
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise ValueError("a task argument, --task-file, or piped stdin is required")


def _handle_run(args: argparse.Namespace) -> int:
    task = _read_task(args.task, args.task_file)
    job = JobSpec(
        job_id=args.id,
        task=task,
        workspace=args.workspace,
        effort=args.effort,
        speed=args.speed,
        sandbox=args.sandbox,
        timeout_seconds=args.timeout,
        skip_git_repo_check=args.skip_git_repo_check,
    )
    result = run_job(job, args.codex)
    _print_results([result], args.json)
    return 0 if result.succeeded else 1


def _handle_batch(args: argparse.Namespace) -> int:
    if args.manifest and args.task:
        raise ValueError("use either --manifest or repeated --task arguments, not both")
    if args.manifest:
        ignored_overrides = {
            "--id": args.id,
            "--speed": args.speed,
            "--effort": args.effort,
            "--sandbox": args.sandbox,
            "--timeout": args.timeouts,
        }
        supplied = [name for name, value in ignored_overrides.items() if value]
        if supplied:
            raise ValueError(
                "manifest jobs cannot be combined with per-task options: "
                + ", ".join(supplied)
            )
        jobs, manifest_workers = _jobs_from_manifest(args.manifest, args)
        max_workers = (
            args.max_workers if args.max_workers is not None else manifest_workers
        )
    else:
        jobs = _jobs_from_arguments(args)
        max_workers = args.max_workers if args.max_workers is not None else MAX_WORKERS
    results = run_jobs(jobs, args.codex, max_workers=max_workers)
    _print_results(results, args.json)
    return 0 if all(result.succeeded for result in results) else 1


def _jobs_from_arguments(args: argparse.Namespace) -> list[JobSpec]:
    tasks = args.task or []
    if not tasks:
        raise ValueError("batch requires --manifest or at least one --task")
    count = len(tasks)
    identifiers = _expand(args.id, count, None, "id", lambda value: str(value))
    speeds = _expand(args.speed, count, DEFAULT_SPEED, "speed", str)
    efforts = _expand(args.effort, count, DEFAULT_EFFORT, "effort", str)
    sandboxes = _expand(args.sandbox, count, DEFAULT_SANDBOX, "sandbox", str)
    timeouts = _expand(args.timeouts, count, DEFAULT_TIMEOUT_SECONDS, "timeout", int)
    workspace = args.workspace or Path.cwd()
    return [
        JobSpec(
            job_id=identifiers[index] or f"worker-{index + 1}",
            task=task,
            workspace=workspace,
            speed=speeds[index],
            effort=efforts[index],
            sandbox=sandboxes[index],
            timeout_seconds=timeouts[index],
            skip_git_repo_check=args.skip_git_repo_check,
        )
        for index, task in enumerate(tasks)
    ]


def _jobs_from_manifest(
    path: Path, args: argparse.Namespace
) -> tuple[list[JobSpec], int]:
    manifest_path = path.expanduser().resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        raw_jobs = data
        defaults: dict[str, Any] = {}
    elif isinstance(data, dict):
        raw_jobs = data.get("jobs")
        defaults = data
        allowed_defaults = {
            "jobs",
            "workspace",
            "speed",
            "effort",
            "sandbox",
            "timeout_seconds",
            "max_workers",
        }
        unknown_defaults = set(defaults) - allowed_defaults
        if unknown_defaults:
            raise ValueError(f"manifest has unknown keys: {sorted(unknown_defaults)}")
    else:
        raise TypeError("manifest must be a JSON object or array")
    if not isinstance(raw_jobs, list) or not raw_jobs:
        raise ValueError("manifest must contain a non-empty jobs array")

    default_workspace = args.workspace or _resolve_manifest_workspace(
        defaults.get("workspace"), manifest_path.parent
    )
    default_speed = defaults.get("speed", DEFAULT_SPEED)
    default_effort = defaults.get("effort", DEFAULT_EFFORT)
    default_sandbox = defaults.get("sandbox", DEFAULT_SANDBOX)
    default_timeout = defaults.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    max_workers = int(defaults.get("max_workers", MAX_WORKERS))
    jobs: list[JobSpec] = []
    allowed = {
        "id",
        "task",
        "task_file",
        "workspace",
        "speed",
        "effort",
        "sandbox",
        "timeout_seconds",
        "skip_git_repo_check",
    }
    for index, raw in enumerate(raw_jobs):
        if not isinstance(raw, dict):
            raise TypeError(f"manifest job {index + 1} must be an object")
        unknown = set(raw) - allowed
        if unknown:
            raise ValueError(
                f"manifest job {index + 1} has unknown keys: {sorted(unknown)}"
            )
        task = raw.get("task")
        task_file = raw.get("task_file")
        if task is not None and task_file is not None:
            raise ValueError(
                f"manifest job {index + 1} cannot use task and task_file together"
            )
        if task_file is not None:
            task_path = Path(str(task_file))
            if not task_path.is_absolute():
                task_path = manifest_path.parent / task_path
            task = task_path.read_text(encoding="utf-8")
        if not isinstance(task, str):
            raise TypeError(f"manifest job {index + 1} requires task or task_file")
        workspace_value = raw.get("workspace")
        workspace = (
            _resolve_manifest_workspace(workspace_value, manifest_path.parent)
            if workspace_value is not None
            else default_workspace
        )
        skip_git_repo_check = raw.get("skip_git_repo_check", args.skip_git_repo_check)
        if not isinstance(skip_git_repo_check, bool):
            raise TypeError(
                f"manifest job {index + 1} skip_git_repo_check must be true or false"
            )
        jobs.append(
            JobSpec(
                job_id=str(raw.get("id", f"worker-{index + 1}")),
                task=task,
                workspace=workspace,
                speed=str(raw.get("speed", default_speed)),
                effort=str(raw.get("effort", default_effort)),
                sandbox=str(raw.get("sandbox", default_sandbox)),
                timeout_seconds=int(raw.get("timeout_seconds", default_timeout)),
                skip_git_repo_check=skip_git_repo_check,
            )
        )
    return jobs, max_workers


def _resolve_manifest_workspace(value: Any, base: Path) -> Path:
    if value is None:
        return Path.cwd()
    path = Path(str(value)).expanduser()
    return path if path.is_absolute() else base / path


def _expand(
    values: Sequence[Any] | None,
    count: int,
    default: _T,
    name: str,
    convert: Callable[[Any], _T],
) -> list[_T]:
    if not values:
        return [default for _ in range(count)]
    if len(values) == 1:
        return [convert(values[0]) for _ in range(count)]
    if len(values) != count:
        raise ValueError(f"--{name} must be supplied once or once per task")
    return [convert(value) for value in values]


def _handle_verify_speeds(args: argparse.Namespace) -> int:
    jobs = [
        JobSpec(
            job_id="speed-standard",
            task=_SPEED_TEST_TASK,
            workspace=args.workspace,
            effort=args.effort,
            speed="standard",
            sandbox="read-only",
            timeout_seconds=args.timeout,
            skip_git_repo_check=args.skip_git_repo_check,
        ),
        JobSpec(
            job_id="speed-fast",
            task=_SPEED_TEST_TASK,
            workspace=args.workspace,
            effort=args.effort,
            speed="fast",
            sandbox="read-only",
            timeout_seconds=args.timeout,
            skip_git_repo_check=args.skip_git_repo_check,
        ),
    ]
    results = run_jobs(jobs, args.codex, max_workers=1)
    verified = all(
        result.succeeded and result.final_message.strip() == _SPEED_TEST_MARKER
        for result in results
    )
    if args.json:
        print(
            json.dumps(
                {
                    "verified": verified,
                    "fixed_task": _SPEED_TEST_TASK,
                    "results": [result.to_dict() for result in results],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        _print_results(results, False)
        print(f"Fixed-task speed verification: {'passed' if verified else 'failed'}")
        print("Elapsed time is informational and is not a guaranteed speed ratio.")
    return 0 if verified else 1


def _handle_doctor(args: argparse.Namespace) -> int:
    report = doctor(args.codex, check_login=not args.skip_login)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Codex: {report.get('codex_version', 'not found')}")
        if report.get("logged_in") is not None:
            print(f"Login: {'ready' if report['logged_in'] else 'not logged in'}")
        print(
            f"Model: {report['model']} ({'found' if report['model_found'] else 'missing'})"
        )
        print(f"Reasoning efforts: {', '.join(report['efforts']) or 'none'}")
        print(
            f"Fast mode: {'supported' if report['fast_supported'] else 'unavailable'}"
        )
        print(
            f"Isolated exec flags: "
            f"{'supported' if report.get('exec_flags_ready') else 'unavailable'}"
        )
        print(f"Status: {'ready' if report['ready'] else 'not ready'}")
        if report.get("error"):
            print(f"Error: {report['error']}", file=sys.stderr)
    return 0 if report["ready"] else 1


def _print_results(results: Sequence[RunResult], as_json: bool) -> None:
    if as_json:
        payload: Any = (
            results[0].to_dict()
            if len(results) == 1
            else {
                "status": "succeeded"
                if all(result.succeeded for result in results)
                else "failed",
                "results": [result.to_dict() for result in results],
            }
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for result in results:
        state = "succeeded" if result.succeeded else "failed"
        print(
            f"[{result.job_id}] {state} | model=gpt-5.6-luna | effort={result.effort} "
            f"| speed={result.speed} ({result.service_tier}) "
            f"| elapsed={result.elapsed_seconds:.3f}s"
        )
        if result.final_message:
            print(result.final_message)
        if result.error:
            print(f"Error: {result.error}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 2
