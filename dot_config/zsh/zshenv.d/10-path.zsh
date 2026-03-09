# zshenv.d/10-path.zsh — PATH construction
typeset -U path PATH

# User scripts
[[ -d "$HOME/.local/bin" ]] && path=("$HOME/.local/bin" "${path[@]}")

# Rust / Cargo
[[ -d "$CARGO_HOME/bin" ]] && path=("$CARGO_HOME/bin" "${path[@]}")

# Go
[[ -d "$GOPATH/bin" ]] && path=("$GOPATH/bin" "${path[@]}")

# Bun
[[ -d "$BUN_INSTALL/bin" ]] && path=("$BUN_INSTALL/bin" "${path[@]}")

# .NET tools
[[ -d "$DOTNET_CLI_HOME/tools" ]] && path=("$DOTNET_CLI_HOME/tools" "${path[@]}")

export PATH
