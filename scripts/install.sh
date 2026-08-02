#!/usr/bin/env sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_root=$(dirname -- "$script_dir")

codex_home_path=${CODEX_HOME:-"$HOME/.codex"}
skills_root_path="$HOME/.agents/skills"
force=0
skip_capability_check=0

usage() {
  echo "Usage: $0 [--codex-home PATH] [--skills-root PATH] [--force] [--skip-capability-check]"
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

if [ "$skip_capability_check" -eq 0 ]; then
  if ! command -v codex >/dev/null 2>&1; then
    echo "codex was not found on PATH. Install or update Codex before installing Luna Agent." >&2
    exit 1
  fi
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

install_managed_file "$project_root/.codex/config.toml" "$codex_home_path/luna.config.toml"
install_managed_file "$project_root/.codex/agents/luna-worker.toml" "$codex_home_path/agents/luna-worker.toml"
install_managed_file "$project_root/.codex/agents/luna-low.toml" "$codex_home_path/agents/luna-low.toml"
install_managed_file "$project_root/.codex/agents/luna-medium.toml" "$codex_home_path/agents/luna-medium.toml"
install_managed_file "$project_root/.codex/agents/luna-high.toml" "$codex_home_path/agents/luna-high.toml"
install_managed_file "$project_root/.codex/agents/luna-xhigh.toml" "$codex_home_path/agents/luna-xhigh.toml"
install_managed_file "$project_root/.agents/skills/delegate-luna-workers/SKILL.md" "$skills_root_path/delegate-luna-workers/SKILL.md"
install_managed_file "$project_root/.agents/skills/delegate-luna-workers/agents/openai.yaml" "$skills_root_path/delegate-luna-workers/agents/openai.yaml"

echo "Luna Agent is installed. Restart Codex or open a new thread."
echo "Launch it from a target repository with: codex -p luna"
