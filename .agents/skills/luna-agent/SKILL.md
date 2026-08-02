---
name: luna-agent
description: Delegate one or more bounded tasks to native GPT-5.6 Luna subagents with selectable reasoning effort. Use when a user asks Codex to use Luna, Luna subagents, parallel Luna workers, or a specific Luna effort (low, medium, high, xhigh, or max).
---

# Luna Agent

Use Codex's native subagent workflow. Spawn the installed Luna agent presets directly so their
threads, progress, communication, context, permissions, configuration, and tools remain integrated
with the parent conversation.

## Parameters

- Read `effort` as `low`, `medium`, `high`, `xhigh`, or `max`; default to `max`.
- Read `agents` as `auto` or a worker count from `1` to `4`; default to `auto`.
- Require every delegated objective to be independent and bounded.

For `agents=auto`, choose the smallest useful worker count after identifying independent work:

- Use one worker for a single, small, or sequential objective.
- Use one worker per independent objective, up to four workers.
- Do not invent extra work, duplicate an objective, or parallelize dependent steps to fill slots.

Treat an explicit count as an upper bound when the request has fewer safe independent objectives.
State the selected count and task boundaries before launching workers.

## Workflow

1. Normalize the parameters and resolve `agents=auto`.
2. Split work only along independent boundaries and give each worker a self-contained task.
3. Map the requested effort to the installed custom agent.
4. Spawn each worker with Codex's native `spawn_agent` tool, up to four at once.
5. Give concurrent write workers explicit, non-overlapping file ownership.
6. Wait for every worker, review its evidence, resolve conflicts, and run parent-level checks.
7. Report every failed, interrupted, or unavailable worker.

## Effort mapping

| Effort | Agent |
| --- | --- |
| `low` | `luna_low` |
| `medium` | `luna_medium` |
| `high` | `luna_high` |
| `xhigh` | `luna_xhigh` |
| `max` | `luna_worker` |

## Guardrails

- Native Luna workers inherit the parent conversation's service tier and live runtime settings.
- Never change the parent service tier or silently substitute another model or effort.
- Do not let concurrent workers edit overlapping files. Assign ownership explicitly.
- Keep sequential dependencies in the parent task.
