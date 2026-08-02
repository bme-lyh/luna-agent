# Repository guidance

- Keep the default path on the isolated `codex exec` runner so each worker can select its own speed. Preserve native custom agents as an explicit compatibility mode.
- Do not add MCP, OpenAI Platform API, API-key, or SDK fallbacks.
- Keep `.codex/config.toml`, every agent preset, the delegation skill, installers, tests, and documentation consistent.
- Preserve the defaults `gpt-5.6-luna`, reasoning effort `max`, speed `fast`, read-only isolated workers, automatic worker selection, and four concurrent workers unless a change is explicitly requested.
- Isolated worker commands must ignore unrelated user config while retaining Codex authentication, disable nested multi-agent execution, remove API-key environment variables, use argument arrays rather than a shell, and pass prompts over stdin.
- Installers must not edit a user's base `config.toml`; install the isolated `luna.config.toml` profile instead.
- Run `python -m unittest discover -s tests -v`, `scripts/check.ps1` on Windows, and `sh -n scripts/install.sh scripts/check.sh scripts/luna-agent.sh` after changes.
- Do not perform bulk deletion. Delete at most one explicit file or empty directory per command.
