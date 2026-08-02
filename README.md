# Luna Agent

Luna Agent lets Codex run GPT-5.6 Luna workers at different speeds. Each worker gets its own Codex
session, so a Fast worker and a Standard worker can run at the same time even when the parent
conversation uses another speed.

It uses your existing Codex login. You do not need an API key, MCP server, Docker container, or
background service.

## What you need

- Codex CLI with access to `gpt-5.6-luna`
- A ChatGPT account signed in through Codex
- Python 3.11 or newer
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

The installer adds a `luna` profile, five native Luna presets, the delegation skill, and the
isolated runner. It does not edit your main `~/.codex/config.toml` file.

## Use it in Codex

Start Codex in the project you want to work on:

```bash
codex -p luna
```

Then ask Codex to use the installed skill:

```text
Use $delegate-luna-workers in isolated mode. Run two workers in parallel:
- review the API with effort=max and speed=fast
- review the documentation with effort=high and speed=standard
Wait for both workers and give me one summary.
```

Isolated mode is the default. A worker's speed does not need to match the parent conversation or
the other workers.

## Available settings

| Setting | Values | Default |
| --- | --- | --- |
| Mode | `isolated`, `native` | `isolated` |
| Speed | `fast`, `standard` | `fast` |
| Reasoning | `low`, `medium`, `high`, `xhigh`, `max` | `max` |
| File access | `read-only`, `workspace-write` | `read-only` |
| Parallel workers | 1 to 4 | 1 |

Fast uses Codex Fast mode. Standard uses the normal service tier. Fast usually returns sooner but
uses credits at a higher rate. See the [Codex speed documentation](https://learn.chatgpt.com/docs/agent-configuration/speed)
for current usage details.

Use `workspace-write` only when you want a worker to edit files. When several workers can edit,
give each worker separate files or directories.

## Run the worker tool directly

The skill normally handles these commands for you. They are also useful for checks and scripts.

Run one Fast worker on Windows:

```powershell
./scripts/luna-agent.ps1 run "Review this project for bugs." --speed fast --effort max --workspace .
```

Run one Standard worker on macOS or Linux:

```bash
./scripts/luna-agent.sh run "Review this project for bugs." --speed standard --effort max --workspace .
```

Run two workers with different speeds:

```powershell
./scripts/luna-agent.ps1 batch `
  --task "Review the API." `
  --task "Review the documentation." `
  --speed fast `
  --speed standard `
  --effort max `
  --effort high `
  --max-workers 2 `
  --workspace .
```

For complex batches, put the settings in a JSON manifest:

```json
{
  "workspace": ".",
  "max_workers": 2,
  "jobs": [
    {
      "id": "api-review",
      "task": "Review the API.",
      "speed": "fast",
      "effort": "max"
    },
    {
      "id": "docs-review",
      "task": "Review the documentation.",
      "speed": "standard",
      "effort": "high"
    }
  ]
}
```

Run it with:

```powershell
./scripts/luna-agent.ps1 batch --manifest ./jobs.json
```

## Check the setup

The regular check does not send a model request or consume model credits.

Windows:

```powershell
./scripts/check.ps1
```

macOS or Linux:

```bash
./scripts/check.sh
```

To test both speeds with the same small Luna task:

```powershell
./scripts/luna-agent.ps1 verify-speeds --workspace .
```

`verify-speeds` makes one Standard request and one Fast request. Both requests use credits. The
command verifies the selected service tiers and output, then reports elapsed time. It does not
require Fast to beat Standard by a fixed ratio because service load varies.

## Native compatibility mode

Native mode uses Codex's built-in `spawn_agent` tool and the installed Luna presets. It keeps native
thread integration, but every native worker inherits the parent conversation's speed.

Use native mode only when that behavior is useful:

```text
Use $delegate-luna-workers with mode=native, effort=max, speed=fast, and agents=2.
```

## How isolation works

The runner starts `codex exec` with an argument list rather than a shell command. It fixes the model
to GPT-5.6 Luna, passes the task through standard input, disables nested agents, and sets the speed
and reasoning effort for that worker. It ignores unrelated user configuration but keeps saved Codex
authentication. API-key environment variables are removed before the child starts.

Workers use read-only file access unless you explicitly select `workspace-write`.

## Troubleshooting

- Run `codex login status` if the worker says Codex is not logged in.
- Run `./scripts/check.ps1` or `./scripts/check.sh` to check Luna support.
- Update Codex if `gpt-5.6-luna`, `max`, or Fast mode is missing.
- Restart Codex after installation so it can load the skill and agent presets.
- If the runner needs network or saved-login access from a restricted parent sandbox, approve the
  narrowly scoped launcher command when Codex asks.

## Development

Run the unit tests with Python 3.11 or newer:

```bash
python -m unittest discover -s tests -v
```

See [docs/architecture.md](docs/architecture.md) for implementation details and
[SECURITY.md](SECURITY.md) for the permission model.

## License

MIT
