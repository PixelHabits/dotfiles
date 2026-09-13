---
name: bun-first
description: Bun as runtime, package manager, bundler, and test runner. Use when adding a dependency, writing scripts or server code, configuring installs, or when a task touches fetch, SQL, files, processes, compression, parsing, or scheduling. Always check the current Bun docs and changelog first; training data lags behind Bun releases.
---

# Bun first

Bun ships new built-ins every release. Training data lags by months. Before choosing an approach:

1. Run `bun --version`. Read the changelog for that version and every later one (bun.com/blog, bun.com/docs). Use the Bun docs MCP server when it is available.
2. Search the docs for the task ("Bun SQL", "Bun.cron", "fetch proxy") before reaching for a package.
3. If a built-in exists, use it. If memory says a package is needed, verify that claim against the docs first. The optimized way is often newer than your knowledge.

## Built-ins that replace packages

Verify names in the docs; the list grows. Images (`Bun.Image`), headless browser automation (`Bun.WebView`), markdown (`Bun.markdown`, output unsanitized), cron (`Bun.cron`), pty (`Bun.Terminal`), compression streams with brotli and zstd, XML, TOML, JSONC, JSON5, JSONL streaming, tar archives, string width and ANSI helpers, `URLPattern`, Postgres (`Bun.SQL`), S3 (`Bun.S3Client`), SQLite (`bun:sqlite`), password hashing, semver, glob, shell (`Bun.$`), `Bun.serve` with static directory and routes, `fetch` with `protocol`, `compress`, and `proxy` options, the `Temporal` global.

## Package manager habits

- `bun install` with a lockfile. `--frozen-lockfile` in CI. `bun dedupe --check` in CI, `bun dedupe` after `bun update -r`.
- `bun outdated -r` and `bun update -r`. The root-only forms silently skip workspaces.
- `bunfig.toml`: a `minimumReleaseAge` gate with `minimumReleaseAgeExcludes` for exact-pinned packages; the isolated linker for new monorepos.
- `bun patch <pkg>` for upstream bugs. Commit the patch under `patches/`, keyed to the exact version, re-keyed on every bump.
- `bun add --filter <workspace>` for a workspace dependency.

## Scripts and tests

- `bun run <script>` always. Bare `bun <name>` collides with reserved subcommands such as `bun build`.
- `bun run --parallel a b` inside a package. Turbo owns cross-package graphs.
- `bun test --isolate` per package, `--preload` for one shared setup file, `mock.module` at boundaries.
- `bun --bun <cli>` runs a Node CLI under Bun and does not load `.env`. Pass `--env-file` when the script needs it.

## Runtime facts that bite

- On a serverless function with no `node_modules`, an unresolved optional import triggers auto-install on a read-only filesystem and kills the process. Stub `node_modules/.keep` in the function directory, or bundle the peer.
- Server code uses the native `Temporal` global. The polyfill is for browser bundles only. Never mix the two classes in one module.
- `Bun.SQL`: no `COPY`; bulk load through `unnest` arrays; the parameter bind limit is 65,535; `Query.cancel()` does not stop a sent statement (use `pg_cancel_backend`); numeric and bigint arrive as strings unless configured.
- `Bun.XML.parse` is fast and memory-hungry (tree about twice the body). Fine for hundreds of megabytes; plan the memory.
- YAML 1.2 semantics: `on`, `yes`, and `no` parse as strings.
- The deployed runtime version comes from the platform, not the local binary. Confirm it before using an API newer than the local version.
