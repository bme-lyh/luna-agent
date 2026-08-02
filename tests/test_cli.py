from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from luna_agent.cli import main
from luna_agent.models import RunResult


def successful_result(job_id: str, speed: str, message: str = "ok") -> RunResult:
    return RunResult(
        job_id=job_id,
        speed=speed,
        service_tier="fast" if speed == "fast" else "default",
        effort="max",
        sandbox="read-only",
        elapsed_seconds=0.1,
        return_code=0,
        final_message=message,
    )


class CliTests(unittest.TestCase):
    @patch("luna_agent.cli.run_job")
    def test_run_defaults_to_max_and_fast(self, run_mock) -> None:
        run_mock.return_value = successful_result("worker-1", "fast")
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(["run", "task", "--workspace", str(ROOT)])
        self.assertEqual(exit_code, 0)
        job = run_mock.call_args.args[0]
        self.assertEqual(job.effort, "max")
        self.assertEqual(job.speed, "fast")

    @patch("luna_agent.cli.run_jobs")
    def test_batch_accepts_one_speed_per_task(self, run_jobs_mock) -> None:
        run_jobs_mock.return_value = [
            successful_result("worker-1", "fast"),
            successful_result("worker-2", "standard"),
        ]
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(
                [
                    "batch",
                    "--task",
                    "first",
                    "--task",
                    "second",
                    "--speed",
                    "fast",
                    "--speed",
                    "standard",
                    "--workspace",
                    str(ROOT),
                ]
            )
        self.assertEqual(exit_code, 0)
        jobs = run_jobs_mock.call_args.args[0]
        self.assertEqual([job.speed for job in jobs], ["fast", "standard"])

    @patch("luna_agent.cli.run_jobs")
    def test_batch_loads_manifest_with_independent_speeds(self, run_jobs_mock) -> None:
        run_jobs_mock.return_value = [
            successful_result("fast-job", "fast"),
            successful_result("standard-job", "standard"),
        ]
        manifest = ROOT / "tests" / "fixtures" / "jobs.json"
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(["batch", "--manifest", str(manifest)])
        self.assertEqual(exit_code, 0)
        jobs = run_jobs_mock.call_args.args[0]
        self.assertEqual([job.speed for job in jobs], ["fast", "standard"])
        self.assertTrue(all(job.workspace == ROOT for job in jobs))

    @patch("luna_agent.cli.run_jobs")
    def test_verify_speeds_uses_identical_fixed_task(self, run_jobs_mock) -> None:
        run_jobs_mock.return_value = [
            successful_result("speed-standard", "standard", "LUNA_SPEED_TEST_OK"),
            successful_result("speed-fast", "fast", "LUNA_SPEED_TEST_OK"),
        ]
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(["verify-speeds", "--workspace", str(ROOT)])
        self.assertEqual(exit_code, 0)
        jobs = run_jobs_mock.call_args.args[0]
        self.assertEqual(jobs[0].task, jobs[1].task)
        self.assertEqual([job.speed for job in jobs], ["standard", "fast"])
        self.assertEqual([job.service_tier for job in jobs], ["default", "fast"])


if __name__ == "__main__":
    unittest.main()
