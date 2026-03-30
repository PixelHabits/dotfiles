# zshenv.d/10-path.zsh — PATH construction

prepend_path() {
  [[ -d "$1" ]] || return 0

  case ":$PATH:" in
    *":$1:"*) ;;
    *) export PATH="$1:$PATH" ;;
  esac
}

# User scripts
prepend_path "$HOME/.local/bin"

# Rust / Cargo
[[ -n "$CARGO_HOME" ]] && prepend_path "$CARGO_HOME/bin"

# Go
[[ -n "$GOPATH" ]] && prepend_path "$GOPATH/bin"

# Bun
[[ -n "$BUN_INSTALL" ]] && prepend_path "$BUN_INSTALL/bin"

# .NET tools
[[ -n "$DOTNET_CLI_HOME" ]] && prepend_path "$DOTNET_CLI_HOME/tools"
