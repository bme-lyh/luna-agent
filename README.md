# Luna Agent

Luna Agent adds native GPT-5.6 Luna subagents to Codex. They appear in Codex's subagent interface,
share the parent conversation's context and tools, and return their results directly to the main
agent.

It uses your existing Codex login and native multi-agent support. You do not need an API key, MCP
server, Docker container, background service, or separate worker runtime.

## What you need

- Codex CLI with access to `gpt-5.6-luna`
- A ChatGPT account signed in through Codex
- PowerShell on Windows, or a terminal on macOS/Linux

## Install

Download or clone this repository, open a terminal in the project folder, and run one command.

Windows PowerShell:

```powershell
./scripts/install.ps1
```

macOS or Linux:

```bash
./scripts/install.sh
```

Restart Codex or open a new conversation when the installer finishes.

The installer adds a `luna` profile, five native Luna presets, and the `luna-agent` skill. It does
not edit your main `~/.codex/config.toml` file.

In Codex, both the project and the skill appear as **Luna Agent**. Invoke the skill as
`$luna-agent`. Explicit invocation keeps the Skill body out of unrelated conversations.

When upgrading from version 0.3 or earlier, add `-Force` on Windows or `--force` on macOS/Linux.
The installer then renames the old `delegate-luna-workers` directory to `luna-agent` instead of
deleting its contents.

## Use it in Codex

Start Codex in the project you want to work on:

```bash
codex -p luna
```

Then ask Codex to use the installed skill:

```text
Use $luna-agent with agents=auto and effort=max.
Delegate this task to as many independent Luna workers as are useful, then give me one summary.
```

Workers use Codex's native child threads and inherit the parent conversation's service tier,
permissions, approvals, configuration, and tools.

## Available settings

| Setting | Values | Default |
| --- | --- | --- |
| Reasoning | `low`, `medium`, `high`, `xhigh`, `max` | `max` |
| Agents per wave | `auto`, 1 to 4 | `auto` |

With `agents=auto`, Codex uses one worker for one bounded task and one per ready independent task,
up to the configured limit and currently free slots. An explicit number is a per-wave upper bound;
Codex queues excess work instead of duplicating tasks or exceeding capacity.

When several workers can edit files, give each worker separate files or directories.

The parent may run several waves for the same objective. It launches only tasks whose dependencies
are ready, validates each result, then unlocks the next wave. It reuses an idle worker only for the
same task lineage and stops when the objective is done or no safe progress remains.

## Check the setup

The check validates the installed Codex model catalog without sending a model request.

Windows:

```powershell
./scripts/check.ps1
```

macOS or Linux:

```bash
./scripts/check.sh
```

## How it works

The Skill maps reasoning effort to one of five Luna presets. The root parent maintains a finite
task plan, schedules dependency-ordered native child-agent waves, applies capacity and write-scope
guards, validates concise results, and performs the final checks. Child workers never delegate.

## Troubleshooting

- Run `codex login status` if Codex is not logged in.
- Run `./scripts/check.ps1` or `./scripts/check.sh` to check Luna support.
- Update Codex if `gpt-5.6-luna` or a required reasoning effort is missing.
- Restart Codex after installation so it can load the skill and agent presets.

Versions 0.4 and earlier may have installed an unused runtime at `~/.codex/luna-agent`. The native
Skill does not call it; it can be removed after upgrading.

## Development

Development checks use Python 3.11 or newer:

```bash
python -m unittest discover -s tests -v
```

See [docs/architecture.md](docs/architecture.md) for implementation details and
[SECURITY.md](SECURITY.md) for the permission model.

## License

MIT
