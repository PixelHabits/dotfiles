# Neovim

This configuration requires Neovim 0.12 or later for the built-in package manager.
An older version reports this requirement before it loads plugins.
The yank highlight uses the available Neovim API.

The editor does not force a Go experiment on every project.
For a project that needs JSON v2, start the editor with `GOEXPERIMENT=jsonv2 nvim`.
Use the Go toolchain that the project requires.
The language server inherits that environment.

Mason does not install Copilot automatically.
The existing Sidekick configuration remains available.

Run `nvim --headless -u NONE -i NONE -l tests/nvim.lua` from this worktree.
The test does not install plugins or start language servers.
