# Repository guidance

- Keep this project on Codex's native custom-agent path. Do not add MCP, API-key, `codex exec`, or SDK fallbacks without an explicit design decision.
- Keep `.codex/config.toml`, every agent preset, the delegation skill, installers, tests, and documentation consistent.
- Preserve the defaults `gpt-5.6-luna`, reasoning effort `max`, speed `fast`, and four concurrent child threads unless a change is explicitly requested.
- Installers must not edit a user's base `config.toml`; install the isolated `luna.config.toml` profile instead.
- Run `python -m unittest discover -s tests -v`, `scripts/check.ps1` on Windows, and `sh -n scripts/install.sh scripts/check.sh` after changes.
- Do not perform bulk deletion. Delete at most one explicit file or empty directory per command.
