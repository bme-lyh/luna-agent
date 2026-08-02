# Security policy

## Supported versions

Security fixes are applied to the latest released minor version.

## Reporting

Do not open a public issue containing credentials, private source code, or exploit details. Contact
the repository owner privately after the project is published, then add the preferred security
contact to this file.

## Deployment boundary

This project starts no background service and stores no API key. Isolated workers reuse the saved
Codex CLI login. The runner removes `OPENAI_API_KEY` and `CODEX_API_KEY` from every child process so
an inherited API key cannot silently change the billing path.

Task text is sent to `codex exec` through standard input. The runner passes command arguments as a
list and does not interpolate task text into a shell command. Nested multi-agent execution is
disabled in each child.

Isolated workers use read-only access by default. `workspace-write` allows a child to edit the
selected repository without interactive approval. Review the task before granting that access and
assign non-overlapping file ownership to concurrent workers.

Native Luna agents still inherit the parent session's live sandbox, approval policy, and speed.
Review those settings before native delegation.

The installer writes only explicitly listed files. It refuses to replace different existing files
unless the user supplies `-Force` or `--force`, and it never edits the user's base
`~/.codex/config.toml`.

The isolated runner ignores the user's regular Codex configuration so unrelated MCP servers, hooks,
and stale settings cannot affect a child. Codex authentication remains available. The target
repository's own instructions and content are still untrusted input to the worker.
