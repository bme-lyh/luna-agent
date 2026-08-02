# Security policy

## Supported versions

Security fixes are applied to the latest released minor version.

## Reporting

Do not open a public issue containing credentials, private source code, or exploit details. Contact
the repository owner privately after the project is published, then add the preferred security
contact to this file.

## Deployment boundary

This project starts no service and stores no API key. It reuses the authenticated Codex host.

Native Luna agents inherit the parent session's live sandbox and approval policy. Review those
settings before delegation, especially when multiple workers may edit the same repository. Use
read-only permissions for review-only work and assign non-overlapping file ownership for parallel
implementation.

The installer writes only explicitly listed files. It refuses to replace different existing files
unless the user supplies `-Force` or `--force`, and it never edits the user's base
`~/.codex/config.toml`.
