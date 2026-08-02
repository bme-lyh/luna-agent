---
name: delegate-luna-workers
description: Delegate one or more bounded tasks to native GPT-5.6 Luna custom subagents with explicit reasoning effort and session speed. Use when a user asks Codex to use Luna, Luna subagents, parallel Luna workers, a specific Luna effort (low, medium, high, xhigh, or max), or a specific speed (fast or standard).
---

# Delegate Luna Workers

Use Codex's native multi-agent tools and the installed Luna custom agents. Do not call an MCP server or the OpenAI Platform API.

## Parameters

- Read `effort` as one of `low`, `medium`, `high`, `xhigh`, or `max`; default to `max`.
- Read `speed` as `fast` or `standard`; default to `fast`.
- Read `agents` as the requested worker count; default to `1` and never exceed the configured concurrency limit.
- Require each delegated objective to be independent and bounded.

Map effort to the installed custom agent:

| Effort | Agent |
| --- | --- |
| `low` | `luna_low` |
| `medium` | `luna_medium` |
| `high` | `luna_high` |
| `xhigh` | `luna_xhigh` |
| `max` | `luna_worker` |

## Speed Control

Treat speed as a parent-session setting inherited by spawned agents, not as a spawn parameter.

- Treat `fast` as active when the repository `.codex/config.toml` or the selected `luna` profile sets `service_tier = "fast"` and no live runtime override says otherwise.
- Use `/fast on` for `speed=fast`.
- Use `/fast off` for `speed=standard`.
- Use `/fast status` when the active setting is uncertain.
- If the requested speed conflicts with the loaded configuration and the current client cannot verify or change it, pause and ask the user to set it before spawning workers. Never claim a speed change based only on prompt text.

## Workflow

1. Normalize `effort`, `speed`, and `agents` and state the chosen values briefly.
2. Confirm the requested speed from the loaded project/profile configuration or the client's native speed control.
3. Split work only along independent boundaries. Give every worker a self-contained objective, relevant paths, constraints, and expected output.
4. Spawn the mapped Luna custom agent for each task. Do not substitute another model silently.
5. Wait for all requested workers unless the user asks for streaming progress.
6. Review returned evidence and workspace changes. Resolve conflicts in the parent thread and run proportionate verification.
7. Return one consolidated result and disclose failed, interrupted, or unavailable workers.

## Guardrails

- Keep sequential dependencies in the parent thread.
- Avoid multiple workers editing the same file unless the parent explicitly coordinates ownership.
- Preserve the parent session's sandbox and approval policy.
- Stop if Luna is unavailable to the authenticated Codex account or the client does not expose native subagents.
- Do not fall back to API-key, MCP, `codex exec`, or another model without explicit user approval.
