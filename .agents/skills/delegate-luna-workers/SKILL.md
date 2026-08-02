---
name: delegate-luna-workers
description: Delegate one or more bounded tasks to GPT-5.6 Luna workers with explicit per-task reasoning effort and speed. Use when a user asks Codex to use Luna, Luna subagents, parallel Luna workers, a specific Luna effort (low, medium, high, xhigh, or max), or a specific speed (fast or standard).
---

# Delegate Luna Workers

Use the Luna Agent runner for independently configurable worker speed. It launches isolated
`codex exec` processes with the existing Codex login. Do not call an MCP server or the OpenAI
Platform API.

## Parameters

- Read `mode` as `isolated` or `native`; default to `isolated`.
- Read `effort` as `low`, `medium`, `high`, `xhigh`, or `max`; default to `max`.
- Read `speed` as `fast` or `standard`; default to `fast`.
- Read `agents` as the requested worker count; default to `1` and never exceed `4`.
- Read `sandbox` as `read-only` or `workspace-write`; default to `read-only`.
- Require every delegated objective to be independent and bounded.

Each isolated job may have its own `effort`, `speed`, and `sandbox`. Fast maps to
`service_tier = "fast"`; Standard maps to `service_tier = "default"`. These settings belong to
the isolated child process and do not need to match the parent session.

## Isolated mode (default)

1. Normalize the parameters and state them briefly.
2. Split work only along independent boundaries. Give each worker a self-contained task.
3. Locate the launcher:
   - In this repository on Windows: `scripts/luna-agent.ps1`.
   - In this repository on macOS/Linux: `scripts/luna-agent.sh`.
   - Global Windows install: `$env:CODEX_HOME\luna-agent\scripts\luna-agent.ps1`, falling back to
     `$env:USERPROFILE\.codex\luna-agent\scripts\luna-agent.ps1` when `CODEX_HOME` is unset.
   - Global macOS/Linux install: `$CODEX_HOME/luna-agent/scripts/luna-agent.sh`, falling back to
     `$HOME/.codex/luna-agent/scripts/luna-agent.sh` when `CODEX_HOME` is unset.
4. For one worker, run `run` with explicit `--effort`, `--speed`, `--sandbox`, and `--workspace`.
5. For multiple workers, run one `batch` command with repeated `--task`, `--effort`, `--speed`,
   and `--sandbox` values. Use `--max-workers` no greater than `4`.
6. The launcher requires access to the saved Codex login and OpenAI network service. If the current
   shell sandbox blocks either, tell the user that the isolated runner requires host execution and
   request the narrow approval needed for the launcher command.
7. Wait for all results. Review their evidence, resolve conflicts, and run parent-level checks.
8. Report each failed, interrupted, timed-out, or unavailable worker.

Example for one worker on Windows:

```powershell
./scripts/luna-agent.ps1 run "Review the authentication module." --effort max --speed fast --sandbox read-only --workspace .
```

Example with independent speeds:

```powershell
./scripts/luna-agent.ps1 batch --task "Review the API." --task "Review the docs." --speed fast --speed standard --effort max --effort high --sandbox read-only --max-workers 2 --workspace .
```

Use `--task-file` for a long single task and `--manifest` for complex batches so shell quoting cannot
change the task text.

## Native compatibility mode

Use native mode only when the user explicitly requests `mode=native`. Native workers use Codex's
`spawn_agent` tool and inherit the parent session speed; they cannot select speed independently.

Map effort to the installed native custom agent:

| Effort | Agent |
| --- | --- |
| `low` | `luna_low` |
| `medium` | `luna_medium` |
| `high` | `luna_high` |
| `xhigh` | `luna_xhigh` |
| `max` | `luna_worker` |

Before native delegation, verify the parent speed with `/fast status` and change it with `/fast on`
or `/fast off` when the user requests that session-level change.

## Guardrails

- The isolated runner fixes the model to `gpt-5.6-luna`, ignores unrelated user configuration while
  retaining authentication, disables nested multi-agent tools, removes `OPENAI_API_KEY` and
  `CODEX_API_KEY` from the child environment, and uses the saved Codex login.
- Never silently substitute another model, speed, or effort.
- Use `read-only` for analysis and review. Use `workspace-write` only when the user asks workers to
  edit files.
- Do not let concurrent workers edit overlapping files. Assign ownership explicitly.
- Do not use isolated mode if Codex is not logged in or Luna is unavailable to the account.
- Keep sequential dependencies in the parent task.
