# Architecture

## Native request path

```text
Codex parent
  -> luna-agent skill
  -> finite labeled task plan
  -> ready native Luna child-agent wave
  -> inherited parent context, tools, permissions, and service tier
  -> parent validation and dependency update
  -> repeat ready waves until DONE or BLOCKED
```

The custom agent preset fixes only `gpt-5.6-luna`, the reasoning effort, and role instructions.
Codex supplies the child thread relationship and inherits all omitted session settings from the
parent. Live parent sandbox and approval overrides remain authoritative.

## Concurrency

The skill defaults to `agents=auto`. `agents` is a per-wave concurrency ceiling, not a cumulative
worker count. The root parent launches the minimum of ready tasks, the requested ceiling, four, and
the currently free native slots. Excess ready tasks remain queued and fill slots as workers finish.
It never creates duplicate work to fill capacity.

The parent owns dependency ordering and launches successors only after prerequisites pass. It may
reuse an idle worker through `followup_task` for the same task lineage; unrelated work gets a new
worker. Results may finish in any order and are correlated by task label before consolidation.

Parallel read-only work is safe for independent tasks. Workspace-write jobs need non-overlapping
file ownership because native child agents share the same working tree.

## Completion and failure

Every task declares an objective, scope, acceptance check, and stop condition. Workers return a
concise `done`, `blocked`, or `failed` result with changed paths, checks, and residual risks. The
parent retries a safe transient pre-start failure at most once. If writes might have started, it
inspects state before any idempotent continuation. Each task gets one initial attempt plus at most
one retry or follow-up. After a bounded wait and one no-progress check, the parent interrupts a
stalled worker and records it as failed. Workers cannot recursively delegate.

After each wave, the parent validates evidence and replans only within the original objective. Each
wave must close or advance a planned task. The parent enters `DONE` after final checks pass and
`BLOCKED` when dependencies fail, no task can progress, or a task budget is exhausted.

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

Offline tests check the profile, native presets, compact Skill contract, multi-wave state machine,
installers, and absence of obsolete runtime files. `scripts/check.ps1` and `scripts/check.sh`
inspect the bundled Codex model catalog without sending a model request. Live forward tests remain
explicit because they send real native model requests.
