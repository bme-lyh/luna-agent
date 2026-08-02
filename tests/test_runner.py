from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from luna_agent.models import JobSpec, RunResult
from luna_agent.runner import (
    _parse_json_stream,
    build_command,
    doctor,
    run_job,
    run_jobs,
    sanitized_environment,
)


class RunnerTests(unittest.TestCase):
    def test_fast_and_standard_build_distinct_explicit_tiers(self) -> None:
        with patch("luna_agent.runner.shutil.which", return_value="codex"):
            fast = build_command(JobSpec("fast", "task", ROOT, speed="fast"))
            standard = build_command(
                JobSpec("standard", "task", ROOT, speed="standard")
            )
        self.assertIn('service_tier="fast"', fast)
        self.assertIn('service_tier="default"', standard)
        self.assertIn('model_reasoning_effort="max"', fast)
        self.assertIn("features.multi_agent=false", fast)
        self.assertIn("agents.enabled=false", fast)
        self.assertIn("--ignore-user-config", fast)
        self.assertNotIn("--strict-config", fast)
        self.assertEqual(fast[-1], "-")

    def test_environment_removes_api_keys(self) -> None:
        environment = sanitized_environment(
            {"OPENAI_API_KEY": "secret", "CODEX_API_KEY": "secret", "KEEP": "yes"}
        )
        self.assertNotIn("OPENAI_API_KEY", environment)
        self.assertNotIn("CODEX_API_KEY", environment)
        self.assertEqual(environment["KEEP"], "yes")

    def test_json_stream_extracts_final_message_usage_and_thread(self) -> None:
        stream = "\n".join(
            [
                json.dumps({"type": "thread.started", "thread_id": "thread-1"}),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "done"},
                    }
                ),
                json.dumps({"type": "turn.completed", "usage": {"output_tokens": 2}}),
            ]
        )
        thread_id, usage, final_message, error = _parse_json_stream(stream)
        self.assertEqual(thread_id, "thread-1")
        self.assertEqual(usage, {"output_tokens": 2})
        self.assertEqual(final_message, "done")
        self.assertIsNone(error)

    @patch("luna_agent.runner.build_command", return_value=["codex", "exec", "-"])
    @patch("luna_agent.runner.subprocess.run")
    def test_run_job_sends_prompt_on_stdin(self, run_mock, _build_mock) -> None:
        stdout = "\n".join(
            [
                json.dumps({"type": "thread.started", "thread_id": "thread-2"}),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "result"},
                    }
                ),
                json.dumps({"type": "turn.completed", "usage": {}}),
            ]
        )
        run_mock.return_value = subprocess.CompletedProcess(
            [], 0, stdout=stdout, stderr=""
        )
        result = run_job(JobSpec("job", "bounded task", ROOT))
        self.assertTrue(result.succeeded)
        self.assertEqual(result.final_message, "result")
        sent_prompt = run_mock.call_args.kwargs["input"]
        self.assertIn("bounded task", sent_prompt)
        self.assertIn("Do not create, invoke, or delegate", sent_prompt)

    @patch("luna_agent.runner.build_command", return_value=["codex", "exec", "-"])
    @patch("luna_agent.runner.subprocess.run")
    def test_run_job_reports_timeout(self, run_mock, _build_mock) -> None:
        run_mock.side_effect = subprocess.TimeoutExpired(
            cmd=["codex"], timeout=5, output="", stderr="timeout detail"
        )
        result = run_job(JobSpec("job", "task", ROOT, timeout_seconds=5))
        self.assertFalse(result.succeeded)
        self.assertEqual(result.return_code, 124)
        self.assertIn("timed out", result.error or "")

    @patch("luna_agent.runner.resolve_codex", return_value="codex")
    @patch("luna_agent.runner.subprocess.run")
    def test_doctor_checks_login_flags_and_catalog(
        self, run_mock, _resolve_mock
    ) -> None:
        catalog = {
            "models": [
                {
                    "slug": "gpt-5.6-luna",
                    "supported_reasoning_levels": [
                        {"effort": effort}
                        for effort in ("low", "medium", "high", "xhigh", "max")
                    ],
                    "additional_speed_tiers": ["fast"],
                }
            ]
        }
        run_mock.side_effect = [
            subprocess.CompletedProcess([], 0, stdout="codex-cli 0.145.0", stderr=""),
            subprocess.CompletedProcess(
                [], 0, stdout="--ignore-user-config --ephemeral --json", stderr=""
            ),
            subprocess.CompletedProcess(
                [], 0, stdout="Logged in using ChatGPT", stderr=""
            ),
            subprocess.CompletedProcess([], 0, stdout=json.dumps(catalog), stderr=""),
        ]
        report = doctor()
        self.assertTrue(report["ready"])
        self.assertTrue(report["exec_flags_ready"])

    @patch("luna_agent.runner.run_job")
    def test_batch_preserves_input_order(self, run_mock) -> None:
        def fake_run(job: JobSpec, _codex: str) -> RunResult:
            return RunResult(
                job_id=job.job_id,
                speed=job.speed,
                service_tier=job.service_tier,
                effort=job.effort,
                sandbox=job.sandbox,
                elapsed_seconds=0.1,
                return_code=0,
                final_message=job.job_id,
            )

        run_mock.side_effect = fake_run
        jobs = [JobSpec("one", "task", ROOT), JobSpec("two", "task", ROOT)]
        results = run_jobs(jobs, max_workers=2)
        self.assertEqual([result.job_id for result in results], ["one", "two"])

    def test_job_rejects_invalid_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported speed"):
            JobSpec("job", "task", ROOT, speed="turbo")
        with self.assertRaisesRegex(ValueError, "job id"):
            JobSpec("not valid", "task", ROOT)


if __name__ == "__main__":
    unittest.main()
