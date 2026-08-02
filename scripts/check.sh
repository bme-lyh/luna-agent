#!/usr/bin/env sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_root=$(dirname -- "$script_dir")

if ! command -v codex >/dev/null 2>&1; then
  echo "codex was not found on PATH." >&2
  exit 1
fi

catalog=$(codex -C "$project_root" debug models --bundled)
case "$catalog" in
  *'"slug":"gpt-5.6-luna"'*) ;;
  *)
    echo "gpt-5.6-luna is missing from the bundled model catalog." >&2
    exit 1
    ;;
esac
luna_catalog=${catalog#*\"slug\":\"gpt-5.6-luna\"}
luna_catalog=${luna_catalog%%\},\{\"slug\":*}
printf '%s' "$luna_catalog" | grep -q '"effort":"max"' || {
  echo "The bundled Luna model does not advertise reasoning effort max." >&2
  exit 1
}
printf '%s' "$luna_catalog" | grep -q '"additional_speed_tiers":\["fast"\]' || {
  echo "The bundled Luna model does not advertise Fast mode." >&2
  exit 1
}

echo "Project configuration loaded by Codex."
echo "gpt-5.6-luna supports reasoning effort max and Fast mode."
echo "No model request was made."
