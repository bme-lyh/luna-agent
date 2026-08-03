# Repository guidance

- Keep Luna Agent native-only. Delegate through Codex's `spawn_agent` workflow; do not add a
  `codex exec`, MCP, API-key, SDK, or background-service runner.
- Never set or override `service_tier`. Native Luna workers inherit it from the parent conversation.
- Keep `.codex/config.toml`, every agent preset, the Skill, installers, tests, and documentation
  consistent.
- Preserve the defaults `gpt-5.6-luna`, reasoning effort `max`, automatic worker selection, and a
  maximum of four concurrent workers unless a change is explicitly requested.
- Keep orchestration finite and parent-owned: dependency-ordered waves, live-slot backpressure,
  same-lineage worker reuse, explicit DONE/BLOCKED termination, and no child delegation.
- Native workers must inherit the parent session's sandbox, approvals, configuration, tools, and
  context. Agent presets should set only their role, model, reasoning effort, and instructions.
- Keep the injected Skill concise: at most 90 lines and 500 whitespace-delimited words. Put
  installation and architecture details in repository documentation instead.
- Installers must not edit a user's base `config.toml`; install `luna.config.toml` separately.
- Run `python -m unittest discover -s tests -v`, `scripts/check.ps1` on Windows, and
  `sh -n scripts/install.sh scripts/check.sh` after changes.
- Do not perform bulk deletion. Delete at most one explicit file or empty directory per command.
