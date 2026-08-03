---
name: luna-agent
description: Delegate a bounded objective to native GPT-5.6 Luna subagents with controlled multi-wave coordination and selectable reasoning effort. Use only when the user explicitly invokes $luna-agent.
---

# Luna Agent

Use Codex's native subagent tools. The root parent owns one finite user objective and may run
multiple dependency-ordered waves. Workers inherit the parent conversation's context, service
tier, permissions, approvals, configuration, and tools.

## Inputs

- Read `effort` as `low`, `medium`, `high`, `xhigh`, or `max`; default to `max`.
- Read `agents` as `auto` or `1` to `4`; default to `auto`. It is a per-wave concurrency ceiling.
- Reject invalid or mixed per-task values instead of silently coercing them. Use one effort for the
  entire invocation.

With `agents=auto`, use one worker for one bounded task or one per ready independent task, subject
to the configured limit and currently free slots. Never create filler work.

## Workflow

1. Create a finite labeled task plan. Derive each task's unique, concise `snake_case` `task_name`
   from its objective; pass it to `spawn_agent`, keep it stable for lineage/result correlation, and
   never reuse it for another objective. Record dependencies and write ownership. Give every worker
   an objective, scope, acceptance check, stop condition, and finite budget: one initial attempt
   plus at most one retry or follow-up.
2. Before each wave, use `list_agents` to inspect live capacity. Dispatch ready independent tasks up to
   `min(ready tasks, agents ceiling, 4, free slots)` and queue the rest. Use `spawn_agent` for new
   work; use `followup_task` only for the same idle worker and task lineage.
3. Keep orchestration in the root parent. Workers must not spawn or delegate to other agents.
4. Refill free slots from the current ready queue, then collect the wave. Record every labeled
   result as `done`, `blocked`, or `failed`, including changed paths, checks, risks, and the reason
   for any interruption or unavailability. Use bounded waits; after one no-progress check,
   interrupt a stalled worker and record it as `failed`. Prefer concise evidence over raw logs.
5. Validate results and replan only within the original objective. Start another wave only when
   required work is ready and delegation adds value; every wave must close or advance a planned
   task. Preserve ownership across active tasks.
6. Retry a safe pre-start or transient failure at most once with the same model and effort. If
   execution or writes may have started, inspect state before an idempotent continuation; never
   blindly retry writes.
7. Set parent state `DONE` when the objective and parent-level checks pass. Set parent state
   `BLOCKED` when dependencies failed, no task can progress, or a budget is exhausted. Report
   every task status and residual risk.

## Effort mapping

| Effort | Agent |
| --- | --- |
| `low` | `luna_low` |
| `medium` | `luna_medium` |
| `high` | `luna_high` |
| `xhigh` | `luna_xhigh` |
| `max` | `luna_worker` |

Never change the parent service tier or silently substitute another model or effort. Never let
concurrent workers edit overlapping paths.
