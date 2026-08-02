# Security policy

## Supported versions

Security fixes are applied to the latest released minor version.

## Reporting

Do not open a public issue containing credentials, private source code, or exploit details. Contact
the repository owner privately after the project is published, then add the preferred security
contact to this file.

## Deployment boundary

This project starts no background service, stores no API key, and launches no external worker
process. It configures Codex's native subagents to use GPT-5.6 Luna at a selected reasoning effort.

Native Luna agents inherit the parent session's live sandbox, approval policy, configuration,
tools, context, and service tier. Review the parent settings before delegation and assign
non-overlapping file ownership to concurrent write workers.

The installer writes only explicitly listed files. It refuses to replace different existing files
unless the user supplies `-Force` or `--force`, and it never edits the user's base
`~/.codex/config.toml`.

The target repository's instructions and content remain untrusted input to every native worker.
