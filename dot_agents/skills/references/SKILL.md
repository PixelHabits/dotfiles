---
name: references
description: Read fast-moving libraries from their local source checkouts. Load this skill for "read the source", "which version is current", "the API changed", or "add a reference". Also load it for any build or answer that touches a library listed in the available_references block.
---

# References

The `<available_references>` block in the session context lists local git checkouts of libraries. Each line gives the alias, the absolute path, the ref and commit, the fetch age, and a description. The block arrives in full at session start. After that, only changed lines arrive. The `refs` binary maintains the checkouts.

## Read the source first

1. Before you build with or answer about a listed library, open its checkout at the path shown. Start with `README`, `docs/`, `examples/`, and the changelog. Then read the implementation of the API you need.
2. The commit on the line is the version. Read that version, not the one in memory. When the exact version matters, run `git -C <path> log -1 --oneline`.
3. Cite the file and line you read in your answer or your commit message. A claim about an API without a citation is a guess.
4. Do not infer an API from another repository, from a pattern you remember, or from the shape of a similar library. The checkout proves the commit shown; fetch failures and pending updates can leave it behind upstream.
5. `node_modules` in the working repository shows the pinned version the project runs. Use it to see what the project has today. Use the reference checkout to see what the library offers now. When the two differ, name the difference.

## When a library is missing

Add a missing library only when the user requests it, or when it is a top-level dependency with broad repo impact, frequent use, or a central role in the current feature. Do not add small transitive dependencies or one-off lookups. For those, inspect the installed source or official documentation without changing the manifest.

For a qualifying library, run `refs add <owner/repo>`. Pass `--alias <name>` to choose the alias, `--ref <branch|tag|sha>` to pin a version, `--description "..."` for the line text. The command clones, creates the checkout, and prints the new line. The hook delivers the delta on the next turn. Then read the checkout as above. Tell the user that `~/.agents/references.json` changed so they can keep it in their dotfiles.

## When the line says upstream moved

A line with `upstream +N commits` means the remote moved and the checkout did not. The checkout never moves while you read it. When you need the newer commit, run `refs apply <alias>` between two reads, then re-read what depends on it. Session start applies pending updates on its own.

## When the line reports a problem

- `fetch failed <age>: <reason>`: the checkout is still valid at the commit shown. Read it, mention the stale fetch, and do not retry the network yourself.
- `missing, run refs sync`: no checkout exists yet. Run `refs sync <alias>` once, then read.
- Offline work: set `REFERENCES_OFFLINE=1`. Then `refs` skips every network call and works from local data.

## Commands

- `refs list`: aliases, refs, commits, status.
- `refs add <repository> [--alias x] [--ref x] [--description "..."]`: add a library and create its checkout.
- `refs sync [alias...]`: fetch and report upstream movement. No checkout moves.
- `refs apply [alias...]`: move the checkout to the fetched commit.
- `refs remove <alias>`: drop a library.
- `refs render --full`: print the block by hand.

To pin a version, set `ref` to a tag or commit in `~/.agents/references.json`. Then run `refs sync <alias>` and `refs apply <alias>`.
