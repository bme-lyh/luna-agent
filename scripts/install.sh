#!/usr/bin/env sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_root=$(dirname -- "$script_dir")

codex_home_path=${CODEX_HOME:-"$HOME/.codex"}
skills_root_path="$HOME/.agents/skills"
runtime_path=""
force=0
skip_capability_check=0

usage() {
  echo "Usage: $0 [--codex-home PATH] [--skills-root PATH] [--runtime-path PATH] [--force] [--skip-capability-check]"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --codex-home)
      [ "$#" -ge 2 ] || { usage >&2; exit 2; }
      codex_home_path=$2
      shift 2
      ;;
    --skills-root)
      [ "$#" -ge 2 ] || { usage >&2; exit 2; }
      skills_root_path=$2
      shift 2
      ;;
    --runtime-path)
      [ "$#" -ge 2 ] || { usage >&2; exit 2; }
      runtime_path=$2
      shift 2
      ;;
    --force)
      force=1
      shift
      ;;
    --skip-capability-check)
      skip_capability_check=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$runtime_path" ]; then
  runtime_path="$codex_home_path/luna-agent"
fi

if command -v python3 >/dev/null 2>&1; then
  python_command=python3
elif command -v python >/dev/null 2>&1; then
  python_command=python
else
  echo "Python 3.11 or newer is required for isolated Luna workers." >&2
  exit 1
fi
"$python_command" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' || {
  echo "Python 3.11 or newer is required for isolated Luna workers." >&2
  exit 1
}

if [ "$skip_capability_check" -eq 0 ]; then
  if ! command -v codex >/dev/null 2>&1; then
    echo "codex was not found on PATH. Install or update Codex before installing Luna Agent." >&2
    exit 1
  fi
  exec_help=$(codex exec --help)
  for required_flag in --ignore-user-config --ephemeral --json; do
    printf '%s' "$exec_help" | grep -q -- "$required_flag" || {
      echo "This Codex version is too old for isolated Luna workers. Update Codex first." >&2
      exit 1
    }
  done
  catalog=$(codex debug models --bundled)
  case "$catalog" in
    *'"slug":"gpt-5.6-luna"'*) ;;
    *)
      echo "This Codex installation does not expose gpt-5.6-luna." >&2
      exit 1
      ;;
  esac
  luna_catalog=${catalog#*\"slug\":\"gpt-5.6-luna\"}
  luna_catalog=${luna_catalog%%\},\{\"slug\":*}
  printf '%s' "$luna_catalog" | grep -q '"effort":"max"' || {
    echo "The installed Luna model catalog does not support reasoning effort max." >&2
    exit 1
  }
  printf '%s' "$luna_catalog" | grep -q '"additional_speed_tiers":\["fast"\]' || {
    echo "The installed Luna model catalog does not support Fast mode." >&2
    exit 1
  }
fi

install_managed_file() {
  source_path=$1
  destination_path=$2
  destination_directory=$(dirname -- "$destination_path")
  mkdir -p "$destination_directory"

  if [ -f "$destination_path" ]; then
    if cmp -s "$source_path" "$destination_path"; then
      echo "Already current: $destination_path"
      return
    fi
    if [ "$force" -ne 1 ]; then
      echo "Refusing to overwrite a different file: $destination_path. Re-run with --force after reviewing it." >&2
      exit 1
    fi
  fi

  cp -f "$source_path" "$destination_path"
  echo "Installed: $destination_path"
}

migrate_legacy_skill() {
  legacy_path=$1
  destination_path=$2

  if [ -L "$legacy_path" ]; then
    echo "Refusing to migrate a linked legacy skill directory: $legacy_path" >&2
    exit 1
  fi
  if [ ! -e "$legacy_path" ]; then
    return
  fi
  if [ ! -d "$legacy_path" ]; then
    echo "Legacy skill path is not a directory: $legacy_path" >&2
    exit 1
  fi
  if [ -e "$destination_path" ] || [ -L "$destination_path" ]; then
    echo "Both legacy and current skill directories exist. Review them manually: $legacy_path and $destination_path" >&2
    exit 1
  fi
  if [ "$force" -ne 1 ]; then
    echo "Legacy skill found at $legacy_path. Re-run with --force to rename it to Luna Agent." >&2
    exit 1
  fi

  mkdir -p "$skills_root_path"
  skills_root_abs=$(CDPATH= cd -P -- "$skills_root_path" && pwd -P)
  legacy_parent_abs=$(CDPATH= cd -P -- "$(dirname -- "$legacy_path")" && pwd -P)
  destination_parent_abs=$(CDPATH= cd -P -- "$(dirname -- "$destination_path")" && pwd -P)
  if [ "$skills_root_abs" = "/" ]; then
    echo "Skills root must not be the filesystem root." >&2
    exit 1
  fi
  if [ "$legacy_parent_abs" != "$skills_root_abs" ] || [ "$destination_parent_abs" != "$skills_root_abs" ]; then
    echo "Skill migration paths must be direct children of $skills_root_abs" >&2
    exit 1
  fi

  mv -- "$legacy_path" "$destination_path"
  echo "Migrated skill: $legacy_path -> $destination_path"
}

skill_source="$project_root/.agents/skills/luna-agent"
legacy_skill_destination="$skills_root_path/delegate-luna-workers"
skill_destination="$skills_root_path/luna-agent"
migrate_legacy_skill "$legacy_skill_destination" "$skill_destination"
install_managed_file "$skill_source/SKILL.md" "$skill_destination/SKILL.md"
install_managed_file "$skill_source/agents/openai.yaml" "$skill_destination/agents/openai.yaml"

install_managed_file "$project_root/.codex/config.toml" "$codex_home_path/luna.config.toml"
install_managed_file "$project_root/.codex/agents/luna-worker.toml" "$codex_home_path/agents/luna-worker.toml"
install_managed_file "$project_root/.codex/agents/luna-low.toml" "$codex_home_path/agents/luna-low.toml"
install_managed_file "$project_root/.codex/agents/luna-medium.toml" "$codex_home_path/agents/luna-medium.toml"
install_managed_file "$project_root/.codex/agents/luna-high.toml" "$codex_home_path/agents/luna-high.toml"
install_managed_file "$project_root/.codex/agents/luna-xhigh.toml" "$codex_home_path/agents/luna-xhigh.toml"
install_managed_file "$project_root/src/luna_agent/__init__.py" "$runtime_path/src/luna_agent/__init__.py"
install_managed_file "$project_root/src/luna_agent/__main__.py" "$runtime_path/src/luna_agent/__main__.py"
install_managed_file "$project_root/src/luna_agent/cli.py" "$runtime_path/src/luna_agent/cli.py"
install_managed_file "$project_root/src/luna_agent/models.py" "$runtime_path/src/luna_agent/models.py"
install_managed_file "$project_root/src/luna_agent/runner.py" "$runtime_path/src/luna_agent/runner.py"
install_managed_file "$project_root/scripts/luna-agent.ps1" "$runtime_path/scripts/luna-agent.ps1"
install_managed_file "$project_root/scripts/luna-agent.sh" "$runtime_path/scripts/luna-agent.sh"
chmod +x "$runtime_path/scripts/luna-agent.sh"

echo "Luna Agent is installed. Restart Codex or open a new thread."
echo "Launch it from a target repository with: codex -p luna"
echo "Check isolated workers with: $runtime_path/scripts/luna-agent.sh doctor"
