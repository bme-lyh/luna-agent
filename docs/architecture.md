# Architecture

## Native request path

```text
Codex parent
  -> luna-agent skill
  -> native spawn_agent
  -> selected Luna effort preset
  -> native child thread
  -> inherited parent context, tools, permissions, and service tier
  -> Codex parent review and consolidation
```

The custom agent preset fixes only `gpt-5.6-luna`, the reasoning effort, and role instructions.
Codex supplies the child thread relationship and inherits all omitted session settings from the
parent. Live parent sandbox and approval overrides remain authoritative.

## Concurrency

The skill defaults to `agents=auto`. The parent identifies independent bounded objectives and uses
the smallest useful worker count: one for a single or sequential objective, otherwise one per
independent objective up to four. It does not create duplicate work to fill available slots. An
explicit agent count is treated as an upper bound when fewer safe task boundaries exist.

Codex's native multi-agent runtime supervises up to four child threads. Results may finish in any
order; the parent waits for the requested workers and consolidates their findings.

Parallel read-only work is safe for independent tasks. Workspace-write jobs need non-overlapping
file ownership because native child agents share the same working tree.

## Configuration and installation

The repository contains three layers:

1. `.codex/config.toml` supplies the optional `luna` profile and multi-agent defaults.
2. `.codex/agents/*.toml` defines one native Luna preset for each reasoning effort.
3. `.agents/skills/luna-agent` teaches Codex how to select and coordinate those presets.

The installer copies the profile to `~/.codex/luna.config.toml`, the presets to
`~/.codex/agents`, and the Skill to `~/.agents/skills/luna-agent`. When upgrading with `-Force` or
`--force`, it safely renames the legacy
`delegate-luna-workers` skill directory before installing the new metadata. It stops if both names
already exist, and it never recursively deletes a directory. It also refuses to replace different
managed files without the force option and does not edit the base `~/.codex/config.toml` file.

## Verification

Offline tests check the profile, native presets, Skill contract, installers, and absence of obsolete
runtime files. `scripts/check.ps1` and `scripts/check.sh` inspect the bundled Codex model catalog
without sending a model request.
