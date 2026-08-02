from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MODEL = "gpt-5.6-luna"
EFFORTS = ("low", "medium", "high", "xhigh", "max")
SPEEDS = ("fast", "standard")
SANDBOXES = ("read-only", "workspace-write")
SPEED_TO_SERVICE_TIER = {"fast": "fast", "standard": "default"}
DEFAULT_EFFORT = "max"
DEFAULT_SPEED = "fast"
DEFAULT_SANDBOX = "read-only"
DEFAULT_TIMEOUT_SECONDS = 1800
MAX_WORKERS = 4
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


@dataclass(frozen=True, slots=True)
class JobSpec:
    job_id: str
    task: str
    workspace: Path
    effort: str = DEFAULT_EFFORT
    speed: str = DEFAULT_SPEED
    sandbox: str = DEFAULT_SANDBOX
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    skip_git_repo_check: bool = False

    def __post_init__(self) -> None:
        if not _SAFE_ID.fullmatch(self.job_id):
            raise ValueError(
                "job id must be 1-64 characters using letters, numbers, dot, dash, or underscore"
            )
        task = self.task.strip()
        if not task:
            raise ValueError("task must not be empty")
        if self.effort not in EFFORTS:
            raise ValueError(f"unsupported effort: {self.effort}")
        if self.speed not in SPEEDS:
            raise ValueError(f"unsupported speed: {self.speed}")
        if self.sandbox not in SANDBOXES:
            raise ValueError(f"unsupported sandbox: {self.sandbox}")
        if not 1 <= self.timeout_seconds <= 86400:
            raise ValueError("timeout must be between 1 and 86400 seconds")
        workspace = self.workspace.expanduser().resolve()
        if not workspace.is_dir():
            raise ValueError(f"workspace is not a directory: {workspace}")
        object.__setattr__(self, "task", task)
        object.__setattr__(self, "workspace", workspace)

    @property
    def service_tier(self) -> str:
        return SPEED_TO_SERVICE_TIER[self.speed]


@dataclass(slots=True)
class RunResult:
    job_id: str
    speed: str
    service_tier: str
    effort: str
    sandbox: str
    elapsed_seconds: float
    return_code: int
    final_message: str = ""
    thread_id: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    stderr: str = ""

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0 and self.error is None and bool(self.final_message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.job_id,
            "status": "succeeded" if self.succeeded else "failed",
            "model": MODEL,
            "effort": self.effort,
            "speed": self.speed,
            "service_tier": self.service_tier,
            "sandbox": self.sandbox,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "return_code": self.return_code,
            "thread_id": self.thread_id,
            "usage": self.usage,
            "final_message": self.final_message,
            "error": self.error,
            "stderr": self.stderr,
        }
