from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / ".codex" / "agents"
SKILL_DIR = ROOT / ".agents" / "skills" / "delegate-luna-workers"
SOURCE_DIR = ROOT / "src" / "luna_agent"


class RepositoryContractTests(unittest.TestCase):
    def test_project_defaults_are_max_and_fast(self) -> None:
        config = tomllib.loads(
            (ROOT / ".codex" / "config.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(config["service_tier"], "fast")
        self.assertTrue(config["features"]["fast_mode"])
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
            self.assertIn(agent["sandbox_mode"], {"read-only", "workspace-write"})
            self.assertTrue(agent["description"].strip())
            self.assertTrue(agent["developer_instructions"].strip())

    def test_skill_supports_isolated_and_native_modes(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        metadata = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        for value in ("low", "medium", "high", "xhigh", "max", "fast", "standard"):
            self.assertIn(f"`{value}`", skill)
        for name in (
            "luna_low",
            "luna_medium",
            "luna_high",
            "luna_xhigh",
            "luna_worker",
        ):
            self.assertIn(f"`{name}`", skill)
        self.assertIn("`isolated`", skill)
        self.assertIn("`native`", skill)
        self.assertIn("codex exec", skill)
        self.assertNotIn("dependencies:", metadata)
        self.assertNotIn("lunaAgentWorkers", skill + metadata)
        self.assertIn("$delegate-luna-workers", metadata)
        self.assertIn("default to `auto`", skill)
        self.assertIn("agents=auto", metadata)

    def test_documentation_explains_auto_agent_selection(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
        self.assertIn("| Agents | `auto`, 1 to 4 | `auto` |", readme)
        self.assertIn("defaults to `agents=auto`", architecture)
        self.assertIn("up to four", architecture)

    def test_isolated_runner_is_dependency_free(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(project["project"]["dependencies"], [])
        self.assertEqual(project["project"]["requires-python"], ">=3.11")
        self.assertEqual(
            project["project"]["scripts"]["luna-agent"], "luna_agent.cli:main"
        )
        for filename in (
            "__init__.py",
            "__main__.py",
            "cli.py",
            "models.py",
            "runner.py",
        ):
            self.assertTrue((SOURCE_DIR / filename).is_file(), filename)

    def test_obsolete_api_and_mcp_files_are_absent(self) -> None:
        obsolete = [
            ".mcp.json",
            ".env.example",
            "Dockerfile",
            "compose.yaml",
            "uv.lock",
            "scripts/register-codex.ps1",
            "scripts/register-codex.sh",
        ]
        for relative_path in obsolete:
            self.assertFalse((ROOT / relative_path).exists(), relative_path)


if __name__ == "__main__":
    unittest.main()
