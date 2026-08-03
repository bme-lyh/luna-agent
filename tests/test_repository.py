from __future__ import annotations

import unittest
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / ".codex" / "agents"
SKILL_DIR = ROOT / ".agents" / "skills" / "luna-agent"


class RepositoryContractTests(unittest.TestCase):
    def test_project_defaults_are_native_and_do_not_override_service_tier(self) -> None:
        config = tomllib.loads(
            (ROOT / ".codex" / "config.toml").read_text(encoding="utf-8")
        )
        self.assertNotIn("service_tier", config)
        self.assertNotIn("fast_mode", config["features"])
        self.assertTrue(config["features"]["multi_agent"])
        self.assertTrue(config["agents"]["enabled"])
        self.assertEqual(config["agents"]["default_subagent_model"], "gpt-5.6-luna")
        self.assertEqual(config["agents"]["default_subagent_reasoning_effort"], "max")
        self.assertEqual(config["agents"]["max_concurrent_threads_per_session"], 4)

    def test_every_effort_has_a_native_luna_agent(self) -> None:
        expected = {
            "luna-low.toml": ("luna_low", "low"),
            "luna-medium.toml": ("luna_medium", "medium"),
            "luna-high.toml": ("luna_high", "high"),
            "luna-xhigh.toml": ("luna_xhigh", "xhigh"),
            "luna-worker.toml": ("luna_worker", "max"),
        }
        self.assertEqual(
            {path.name for path in AGENT_DIR.glob("*.toml")}, set(expected)
        )
        for filename, (name, effort) in expected.items():
            agent = tomllib.loads((AGENT_DIR / filename).read_text(encoding="utf-8"))
            self.assertEqual(agent["name"], name)
            self.assertEqual(agent["model"], "gpt-5.6-luna")
            self.assertEqual(agent["model_reasoning_effort"], effort)
            self.assertNotIn("service_tier", agent)
            self.assertNotIn("sandbox_mode", agent)
            self.assertTrue(agent["description"].strip())
            instructions = agent["developer_instructions"]
            self.assertTrue(instructions.strip())
            self.assertIn("Do not spawn or delegate to other agents", instructions)
            self.assertIn("status=done|blocked|failed", instructions)
            self.assertIn("omit raw logs", instructions)

    def test_skill_uses_only_native_subagents(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        metadata = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        for value in ("low", "medium", "high", "xhigh", "max"):
            self.assertIn(f"`{value}`", skill)
        for name in (
            "luna_low",
            "luna_medium",
            "luna_high",
            "luna_xhigh",
            "luna_worker",
        ):
            self.assertIn(f"`{name}`", skill)
        self.assertIn("spawn_agent", skill)
        self.assertIn("followup_task", skill)
        self.assertIn("list_agents", skill)
        self.assertNotIn("codex exec", skill)
        self.assertNotIn("service_tier =", skill)
        self.assertIn("name: luna-agent", skill)
        self.assertNotIn("dependencies:", metadata)
        self.assertNotIn("lunaAgentWorkers", skill + metadata)
        self.assertIn("$luna-agent", metadata)
        self.assertNotIn("$delegate-luna-workers", skill + metadata)
        self.assertIn('display_name: "Luna Agent"', metadata)
        self.assertIn("default to `auto`", skill)
        self.assertIn("agents=auto", metadata)
        self.assertIn("allow_implicit_invocation: true", metadata)
        description = skill.split("---", 2)[1]
        for trigger in (
            "current complex objective",
            "at least two ready independent workstreams",
            "parallel workers materially help",
            "Do not use implicitly for trivial, sequential, or non-parallelizable work",
            "incidental or quoted Luna/model discussion",
            "setup or capability questions",
            "when the user asks not to use agents",
        ):
            self.assertIn(trigger, description)
        self.assertNotIn("Use only when the user explicitly invokes", skill)
        self.assertIn("Reject invalid or mixed per-task values", skill)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("appear as **Luna Agent**", readme)
        self.assertIn("`$luna-agent`", readme)
        self.assertNotIn("$delegate-luna-workers", readme)

    def test_documentation_explains_auto_agent_selection(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
        self.assertIn("| Agents per wave | `auto`, `1` to `4` | `auto` |", readme)
        self.assertIn("invoke Luna Agent automatically", readme)
        self.assertIn("does not trigger for simple or sequential tasks", readme)
        self.assertIn("defaults to `agents=auto`", architecture)
        self.assertIn("per-wave concurrency ceiling", architecture)
        self.assertIn("currently free native slots", architecture)

    def test_skill_defines_a_bounded_multi_wave_state_machine(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        normalized_skill = " ".join(skill.split())
        required_contracts = (
            "finite labeled task plan",
            "unique, concise `snake_case` `task_name`",
            "pass it to `spawn_agent`",
            "keep it stable for lineage/result correlation",
            "never reuse it for another objective",
            "task lineage",
            "Workers must not spawn or delegate",
            "done`, `blocked`, or `failed",
            "another wave",
            "one initial attempt plus at most one retry or follow-up",
            "after one no-progress check",
            "every wave must close or advance a planned task",
            "at most once",
            "never blindly retry writes",
            "Set parent state `DONE`",
            "Set parent state `BLOCKED`",
        )
        for contract in required_contracts:
            self.assertIn(contract, normalized_skill)

        architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
        self.assertIn("unique, concise `snake_case` `task_name`", architecture)
        self.assertIn("passes it to `spawn_agent`", architecture)

    def test_skill_stays_context_efficient(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(skill.splitlines()), 75)
        self.assertLessEqual(len(skill.split()), 450)

    def test_obsolete_runtime_api_and_mcp_files_are_absent(self) -> None:
        obsolete = [
            ".mcp.json",
            ".env.example",
            "Dockerfile",
            "compose.yaml",
            "uv.lock",
            "scripts/register-codex.ps1",
            "scripts/register-codex.sh",
            "scripts/luna-agent.ps1",
            "scripts/luna-agent.sh",
            "src/luna_agent/__init__.py",
            "src/luna_agent/__main__.py",
            "src/luna_agent/cli.py",
            "src/luna_agent/models.py",
            "src/luna_agent/runner.py",
            "pyproject.toml",
            "tests/test_cli.py",
            "tests/test_runner.py",
            "tests/fixtures/jobs.json",
        ]
        for relative_path in obsolete:
            self.assertFalse((ROOT / relative_path).exists(), relative_path)
        self.assertFalse(
            (ROOT / ".agents" / "skills" / "delegate-luna-workers").exists()
        )

    def test_installers_migrate_the_legacy_skill_name(self) -> None:
        for relative_path in ("scripts/install.ps1", "scripts/install.sh"):
            installer = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("delegate-luna-workers", installer)
            self.assertIn("luna-agent", installer)
            self.assertIn("Both legacy and current skill directories exist", installer)
            self.assertNotIn("runtime-path", installer)
            self.assertNotIn("RuntimePath", installer)
            self.assertNotIn("service_tier", installer)


if __name__ == "__main__":
    unittest.main()
