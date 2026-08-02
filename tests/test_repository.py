from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / ".codex" / "agents"
SKILL_DIR = ROOT / ".agents" / "skills" / "delegate-luna-workers"


class RepositoryContractTests(unittest.TestCase):
    def test_project_defaults_are_max_and_fast(self) -> None:
        config = tomllib.loads((ROOT / ".codex" / "config.toml").read_text(encoding="utf-8"))
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
        self.assertEqual({path.name for path in AGENT_DIR.glob("*.toml")}, set(expected))
        for filename, (name, effort) in expected.items():
            agent = tomllib.loads((AGENT_DIR / filename).read_text(encoding="utf-8"))
            self.assertEqual(agent["name"], name)
            self.assertEqual(agent["model"], "gpt-5.6-luna")
            self.assertEqual(agent["model_reasoning_effort"], effort)
            self.assertIn(agent["sandbox_mode"], {"read-only", "workspace-write"})
            self.assertTrue(agent["description"].strip())
            self.assertTrue(agent["developer_instructions"].strip())

    def test_skill_is_native_and_maps_every_effort(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        metadata = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        for value in ("low", "medium", "high", "xhigh", "max", "fast", "standard"):
            self.assertIn(f"`{value}`", skill)
        for name in ("luna_low", "luna_medium", "luna_high", "luna_xhigh", "luna_worker"):
            self.assertIn(f"`{name}`", skill)
        self.assertNotIn("dependencies:", metadata)
        self.assertNotIn("lunaAgentWorkers", skill + metadata)
        self.assertIn("$delegate-luna-workers", metadata)

    def test_obsolete_api_runtime_files_are_absent(self) -> None:
        obsolete = [
            ".mcp.json",
            ".env.example",
            "Dockerfile",
            "compose.yaml",
            "pyproject.toml",
            "uv.lock",
            "scripts/register-codex.ps1",
            "scripts/register-codex.sh",
        ]
        for relative_path in obsolete:
            self.assertFalse((ROOT / relative_path).exists(), relative_path)


if __name__ == "__main__":
    unittest.main()
