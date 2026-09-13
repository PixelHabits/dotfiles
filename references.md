# References

The `refs` tool keeps local git checkouts of libraries that change faster than an AI model's training data.
Claude Code and Codex learn the paths through hooks and read the source before they answer.
When `dev = true`, chezmoi installs the tool, the manifest, and the hooks.

- `~/.agents/references.json`: the manifest. One entry per library.
- `~/.local/share/references/`: the store with the checkouts.
- `~/.local/state/references/`: session markers and the sync lock.
- `~/.local/share/agent-references/`: the tool source.
- `~/.local/bin/refs`: the compiled binary.
- `~/.agents/skills/references/`: the skill that tells agents how to use the block.

## The manifest

The manifest is a JSON object. The key is the alias. The value describes the repository.

```json
{
  "effect-ts": {
    "repository": "Effect-TS/effect",
    "ref": "main",
    "description": "Use when building with Effect"
  }
}
```

`repository` accepts `owner/repo`, `github:owner/repo`, `host/owner/repo`, or a full URL.
`ref` is a branch, a tag, or a commit. When `ref` is absent, the tool uses the default branch of the remote.
`description` is optional. `depth` is optional and sets the shallow fetch depth. The default is 100 commits. A `depth` of 0 fetches the full history.
The tool keeps keys it does not know.

## The store

```text
~/.local/share/references/
├── repos/<host>/<owner>/<repo>.git   one shared bare clone per repository
├── trees/<alias>@<sha>/              one git worktree per applied commit
├── <alias>                           a symlink to the current tree
└── state.json                        what the tool knows about every alias
```

Agents see only the `<alias>` path. The link changes in one atomic step, so a reader never sees a half-moved tree.
A background sync only fetches. It never moves a link.
`refs apply` moves a link to the fetched commit. The old tree stays until no session younger than 24 hours refers to it. The next `refs sync` removes it.

## The prompt block

`refs render --full` prints this block:

```text
<available_references>
Read the friendly manual. Before you build with or answer about a library below, read
its source and its own docs (README, docs/, examples, changelog) in the path given.
These libraries move faster than training data. Do not infer an API from patterns you
remember or from other repositories. Cite the file and line you read.
- effect-ts  /home/me/.local/share/references/effect-ts  main@1a2b3c4  fetched 12m ago  Use when building with Effect
</available_references>
```

A line can also say `upstream +3 commits, run refs apply effect-ts`, `fetch failed 2h ago: <reason>`, or `missing, run refs sync`.
`refs render --delta --session <id>` prints only the lines that changed since the last render for that session. When nothing changed, it prints nothing.

## Hooks

Every hook reads `state.json` and returns in a few milliseconds. No hook touches the network.

Claude Code reads them from `~/.claude/settings.json`. The chezmoi modify template adds them.

- `SessionStart` on startup, resume, clear, or compact: prints the full block. On startup and resume it first applies fetched updates. Then it starts one background `refs sync`. When the working directory is a git worktree or holds a `.bare` directory, the hook adds a `<worktrees>` block with one line per worktree from `git worktree list`, at most 40 lines. A git error or a plain directory produces no block.
- `UserPromptSubmit`: prints the delta. When the last sync is older than one hour, it starts one background `refs sync`.
- `PostToolUse` for Bash: when the command was `refs add`, `refs apply`, `refs sync`, or `refs remove`, prints the delta. Otherwise prints nothing.

Codex, in `~/.config/codex/hooks.json`: the same three events with the same behavior.
Codex hooks live in `$CODEX_HOME/hooks.json`. This repository sets `CODEX_HOME` to `~/.config/codex`.
The template keeps hook entries that other tools added to the Claude settings file.

## Add a reference

By hand, add an entry to `~/.agents/references.json` and run `refs sync`.

From a terminal or an agent session, run `refs add TanStack/router --alias tanstack-router`.
The command writes the manifest, clones the repository, creates the checkout, and prints the new line.
When no description is given, the tool asks `gh repo view` for one, then falls back to the `package.json` description in the checkout.
Chezmoi manages the manifest file. After `refs add`, run `chezmoi re-add ~/.agents/references.json` to keep the change in the dotfiles.

## Pin a tag or commit

Set `ref` to the tag or commit in the manifest. Then run `refs sync <alias>` and `refs apply <alias>`.
A pinned entry never reports upstream movement.

## Work offline

Set `REFERENCES_OFFLINE=1`. The tool skips every network call and keeps working from the local store.

## Build

When a source file changes, chezmoi runs `run_onchange_after_agent-references.sh`.
The script compiles `~/.local/share/agent-references/src/cli.ts` to `~/.local/bin/refs` with Bun.
The script runs `bun install --frozen-lockfile` first. The dependencies are for development only. The compiled binary carries none of them.
Run `bun run test` inside the tool directory. The tests use temporary homes and local git remotes. `bun run check` and `bun run typecheck` run the linter and the type checker.
Run `uv run tests/test_references.py` from the worktree for the chezmoi templates.

## Limits

A session that never compacts sees the full block once at start. After that it only sees deltas.
Codex coverage matches the events its hooks support: `SessionStart`, `UserPromptSubmit`, and `PostToolUse`. The tool passes the payload with `additionalContextLimit` set to 8000 so a long block is not cut.
Every hook depends on `~/.local/bin/refs`. When the binary is absent, the hook fails and the agent shows an error until `chezmoi apply` builds it.
