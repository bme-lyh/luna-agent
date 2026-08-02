# Architecture

## Isolated request path

```text
Codex parent
  -> luna-agent skill
  -> Luna Agent launcher
  -> Python runner
  -> one codex exec process per worker
  -> gpt-5.6-luna with explicit effort and service tier
  -> saved Codex authentication
  -> JSONL events
  -> validated worker result
  -> Codex parent review and consolidation
```

Each `codex exec` process is a separate Codex session. The runner sets
`service_tier = "fast"` for Fast and `service_tier = "default"` for Standard. It also sets the
model and reasoning effort on every launch. Parent speed and sibling speed have no effect on those
values.

## Process boundary

The runner uses `subprocess.run` with an argument array and sends the task through standard input.
It never builds a shell command from task text. Every child launch:

- fixes the model to `gpt-5.6-luna`;
- sets one of the five supported reasoning efforts;
- sets Fast or Standard explicitly;
- disables nested multi-agent tools;
- runs without interactive approvals;
- uses read-only or workspace-write sandboxing;
- ignores unrelated user configuration while retaining Codex authentication;
- removes `OPENAI_API_KEY` and `CODEX_API_KEY` from the child environment;
- uses an ephemeral Codex session rollout.

The target repository remains the child working directory, so its project instructions and files
stay in scope.

## Concurrency

The skill defaults to `agents=auto`. The parent identifies independent bounded objectives and uses
the smallest useful worker count: one for a single or sequential objective, otherwise one per
independent objective up to four. It does not create duplicate work to fill available slots. An
explicit agent count is treated as an upper bound when fewer safe task boundaries exist.

`batch` uses a bounded thread pool to supervise up to four child processes. Results are returned in
manifest or command-line order even when workers finish in a different order. Job IDs must be
unique. The runner starts one child process per supplied task; `max_workers` is a concurrency cap,
not a request to create more tasks.

Parallel read-only work is safe for independent tasks. Workspace-write jobs need non-overlapping
file ownership because separate Codex processes share the same working tree.

## Result handling

Codex emits newline-delimited JSON. The runner extracts:

- the Codex thread ID;
- the last completed agent message;
- token usage;
- failure events;
- process exit code and elapsed time.

A job succeeds only when Codex exits with code zero and returns a final agent message. Timeouts,
missing executables, malformed output, login errors, and model errors return structured failures.
One failed batch job makes the batch command fail after all workers finish.

## Configuration and installation

The repository contains four layers:

1. `.codex/config.toml` supplies the optional `luna` profile and native multi-agent defaults.
2. `.codex/agents/*.toml` defines native compatibility presets for each reasoning effort.
3. `.agents/skills/luna-agent` teaches Codex how to choose isolated or native mode.
4. `src/luna_agent` implements the isolated runner.

The installer copies the profile to `~/.codex/luna.config.toml`, the native presets to
`~/.codex/agents`, the skill to `~/.agents/skills/luna-agent`, and the runner to
`~/.codex/luna-agent`. When upgrading with `-Force` or `--force`, it safely renames the legacy
`delegate-luna-workers` skill directory before installing the new metadata. It stops if both names
already exist, and it never recursively deletes a directory. It also refuses to replace different
managed files without the force option and does not edit the base `~/.codex/config.toml` file.

## Native compatibility path

```text
Codex parent
  -> luna-agent skill with mode=native
  -> native spawn_agent
  -> selected custom Luna preset
  -> inherited parent speed, sandbox, and approvals
  -> native child thread result
```

Native mode preserves first-class child threads. It cannot set speed per child because the native
spawn interface has no service-tier parameter.

## Verification

Offline tests check configuration contracts, command construction, API-key removal, JSONL parsing,
failure handling, parameter validation, result ordering, and CLI defaults. `scripts/check.ps1` and
`scripts/check.sh` inspect the bundled Codex model catalog without sending a model request.

`verify-speeds` runs the same fixed prompt sequentially with Standard and Fast. It succeeds only
when both runs use their configured tiers, exit normally, and return the exact marker. Elapsed time
is recorded but is not a pass condition.
