---
name: luna-agent
description: Delegate work to native GPT-5.6 Luna subagents with bounded coordination and effort selection. Use when the user invokes $luna-agent, asks Codex to use Luna workers, or a current complex objective has at least two ready independent workstreams where parallel workers materially help. Do not use implicitly for trivial, sequential, or non-parallelizable work; incidental or quoted Luna/model discussion; setup or capability questions; unsafe overlapping writes; or when the user asks not to use agents.
---

# Luna Agent

Use native subagent tools. The root owns one finite objective and its waves. Workers inherit its
context, service tier, permissions, approvals, configuration, and tools.

## Invocation

Follow the frontmatter trigger. `$luna-agent` is the explicit override. Stay parent-only when
overhead exceeds value, ownership is unclear, or no slot is free. Never create filler work.

## Inputs

- `effort`: `low|medium|high|xhigh|max`; default `max`. Use one effort per invocation.
- `agents`: `auto|1|2|3|4`; default to `auto`; this is a per-wave ceiling.
- Reject invalid or mixed per-task values. With `auto`, use one worker per ready independent task,
  limited by configured and free slots.

## Workflow

1. Build a finite labeled task plan with dependencies and ownership. Derive each task's unique,
   concise `snake_case` `task_name`; pass it to `spawn_agent`, keep it stable for lineage/result
   correlation, and never reuse it for another objective. Specify objective, scope, acceptance,
   stop condition, and one initial attempt plus at most one retry or follow-up.
2. Before each wave, call `list_agents`. Dispatch up to
   `min(ready, agents ceiling, 4, free slots)`. Queue excess. Use `spawn_agent` for new work and
   `followup_task` only for the same idle worker and task lineage.
3. Keep orchestration in the root parent. Workers must not spawn or delegate to other agents.
4. Refill slots, then collect. Record `done`, `blocked`, or `failed`, changed paths, checks, risks,
   and interruption reason; after one no-progress check, interrupt a stalled worker as `failed`.
5. Validate and replan only within the objective. Start another wave only for ready, valuable work;
   every wave must close or advance a planned task. Preserve active ownership.
6. Retry a safe pre-start or transient failure at most once, unchanged model and effort. If work may
   have started, inspect before an idempotent continuation; never blindly retry writes.
7. Set parent state `DONE` after objective checks pass. Set parent state `BLOCKED` when dependencies
   fail, no task can progress, or budget ends. Report task status and residual risk.

## Effort mapping

| Effort | Agent |
| --- | --- |
| `low` | `luna_low` |
| `medium` | `luna_medium` |
| `high` | `luna_high` |
| `xhigh` | `luna_xhigh` |
| `max` | `luna_worker` |

Never change service tier or substitute model/effort. Never allow overlapping concurrent writes.
