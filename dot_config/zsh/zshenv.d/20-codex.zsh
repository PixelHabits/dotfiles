# Optional machine-local overrides. Fresh machines use the shared base config.
# GUI and direct binary launches must select this profile explicitly.
if [[ -r "${CODEX_HOME:-${XDG_CONFIG_HOME:-$HOME/.config}/codex}/local.config.toml" ]]; then
  if require_cmd codex; then
    alias codex='codex --profile local'
  fi
fi
