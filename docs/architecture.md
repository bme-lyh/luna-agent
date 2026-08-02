# Architecture

## Native request path

```text
Codex parent
  -> delegate-luna-workers skill
  -> native spawn_agent orchestration
  -> selected custom agent in .codex/agents or ~/.codex/agents
  -> gpt-5.6-luna with an explicit effort preset
  -> inherited parent tools, sandbox, approvals, and speed tier
  -> native agent thread result
  -> Codex parent consolidates and verifies
```

There is no secondary API client or service process. Authentication and usage are owned by the
Codex host and the signed-in account.

## Configuration layers

Repository use loads `.codex/config.toml` and `.codex/agents/*.toml`. Global installation copies
the same defaults to `~/.codex/luna.config.toml`, custom agents to `~/.codex/agents/`, and the skill
to `~/.agents/skills/`. Launching `codex -p luna` layers the Luna profile over the user's base
configuration without modifying that base file.

The profile enables native multi-agent tools, caps child concurrency at four, defaults spawned
agents to `gpt-5.6-luna`, defaults effort to `max`, and enables Fast mode.

## Effort selection

Custom-agent files make effort selection explicit and auditable:

| Requested effort | Agent name |
| --- | --- |
| `low` | `luna_low` |
| `medium` | `luna_medium` |
| `high` | `luna_high` |
| `xhigh` | `luna_xhigh` |
| `max` | `luna_worker` |

This avoids relying on an orchestrator to infer effort. The model remains fixed to
`gpt-5.6-luna` in every preset.

## Speed selection

Speed belongs to the parent session and is inherited by spawned agents. The installed profile uses
`service_tier = "fast"` with `features.fast_mode = true`. Use `/fast on`, `/fast off`, and
`/fast status` for explicit session-level selection. The workflow never treats natural-language
prompt text as proof that the speed tier changed.

## Boundaries and failures

The host must expose native subagents and `gpt-5.6-luna` to the authenticated account. Configuration
cannot bypass a client model allowlist, workspace policy, account entitlement, sandbox, or approval
policy. The installer and check scripts inspect the bundled Codex model catalog without making a
billable inference request and fail clearly when Luna, max reasoning, or Fast mode is unavailable.

Multiple agents share the workspace. Split tasks along independent boundaries, assign file
ownership when workers may write, and let the parent resolve conflicting results. Child sessions
inherit live parent runtime permission overrides.

## Distribution choice

This repository is a native Codex configuration package, not an MCP server or a standalone plugin.
Plugins can package skills, but they do not currently install project or user custom-agent TOML
files. Keeping installation explicit prevents a plugin from appearing functional while its required
agents are missing.
