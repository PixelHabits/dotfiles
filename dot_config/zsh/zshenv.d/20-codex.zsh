# Codex: keep managed config machine-agnostic; mutable local state, like project
# trust decisions, belongs in $CODEX_HOME/local.config.toml.
# Lives in zshenv.d (not zshrc.d) so the alias also applies in non-interactive
# shells (agent tooling, scripts). Note: paths that spawn the codex binary
# without a shell still bypass this.
if require_cmd codex; then
  alias codex='codex --profile local'
fi
