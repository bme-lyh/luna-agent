# Luna Agent

Luna Agent lets Codex split a task into smaller jobs and run them with GPT-5.6 Luna subagents.
Your main Codex session stays in control, waits for the workers, and combines their results.

It uses your existing Codex login. You do not need an API key, an MCP server, Docker, or a separate
background service.

## What you get

- GPT-5.6 Luna subagents inside Codex
- Up to four workers running at the same time
- Five reasoning levels: low, medium, high, xhigh, and max
- Fast mode enabled by default
- Safe installers for Windows, macOS, and Linux

## Before you start

You need:

- A recent version of Codex
- A ChatGPT or Codex account with access to GPT-5.6 Luna
- PowerShell on Windows, or a terminal on macOS/Linux

## Install

Download or clone this repository, open a terminal in the project folder, and run the installer.

Windows PowerShell:

```powershell
./scripts/install.ps1
```

macOS or Linux:

```bash
./scripts/install.sh
```

Restart Codex or open a new conversation after installation.

## Start Codex

Open the project you want to work on, then run:

```bash
codex -p luna
```

The `luna` profile uses GPT-5.6 Luna for subagents, max reasoning, Fast mode, and a limit of four
workers.

## Run your first task

Paste this into Codex:

```text
Use $delegate-luna-workers with effort=max, speed=fast, and agents=3 to review this project. Wait for every worker, then give me one clear summary.
```

Change the task at the end to match what you need. For example, you can ask the workers to review
code, check documentation, investigate bugs, or compare several approaches.

## Choose the reasoning level

Set `effort` in your prompt:

| Effort | Best for |
| --- | --- |
| `low` | Short, simple tasks |
| `medium` | Routine work that needs some planning |
| `high` | Careful reviews and multi-step tasks |
| `xhigh` | Difficult but focused work |
| `max` | The deepest reasoning, used by default |

Example:

```text
Use $delegate-luna-workers with effort=high and agents=2 to check these changes for bugs.
```

## Choose the speed

Fast mode is the default. In Codex CLI, use:

```text
/fast on       Turn on Fast mode
/fast off      Use Standard mode
/fast status   Show the current mode
```

In the Codex app or IDE extension, use the model and speed controls in the interface. Fast mode can
use your credits faster than Standard mode.

## Check the installation

Windows:

```powershell
./scripts/check.ps1
```

macOS or Linux:

```bash
./scripts/check.sh
```

The check reads Codex's local model catalog. It does not send a model request or use paid API
tokens.

## If something does not work

- Update Codex if the installer says GPT-5.6 Luna is unavailable.
- Check that your account or workspace has access to GPT-5.6 Luna.
- Restart Codex or open a new conversation if the custom agents do not appear.
- Run the check script and read the error message before reinstalling.

The installer does not change your main `~/.codex/config.toml` file. It creates a separate
`luna.config.toml` profile and refuses to replace different files unless you explicitly use
`-Force` or `--force`.

## For contributors

Run the project tests with Python 3.11 or newer:

```bash
python -m unittest discover -s tests -v
```

See [architecture](docs/architecture.md) for implementation details and [security](SECURITY.md) for
the permission model.

## License

MIT
