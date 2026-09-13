---
name: repo-conventions
description: How I set up and run repositories in any language. Bare repo plus worktrees, git flow (main from dev only, features squash onto dev), the script vocabulary every repo exposes, CI shape, rebase and lockfile discipline. Use when creating a repository, adding a worktree or branch, writing task scripts, rebasing, or opening a PR. TypeScript monorepo mechanics live in references/typescript-bun-turbo.md.
---

# Repository conventions

Language-agnostic. When the repository is a TypeScript monorepo, also read `references/typescript-bun-turbo.md`.

## Layout: bare repo plus worktrees

Every repository lives in a container directory:

```text
<root>/
├── .bare/        git metadata (bare clone)
├── main/         stable branch
├── dev/          integration branch
└── <feature>/    one directory per feature branch
```

New repository or fresh clone:

```sh
mkdir -p <root> && cd <root>
git clone --bare <url> .bare
git --git-dir=.bare config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
git --git-dir=.bare fetch origin
git --git-dir=.bare worktree add main main
git --git-dir=.bare worktree add dev dev
git --git-dir=.bare worktree add -b feat/<name> <name> dev
```

Rules:

- Run git from inside a worktree, or `git --git-dir=<root>/.bare` for repository admin.
- Commands run where the shell sits. Confirm the worktree before every install, build, or verify.
- One writer per worktree. Parallel agents get parallel worktrees.
- Remove a worktree with `git --git-dir=.bare worktree remove <dir>` after its branch merges.
- Older repositories use `<repo>/.worktrees/<name>` inside a normal checkout. The same rules apply.

## Git flow

- `main`: release branch. Receives merges from `dev` only. Tagged for releases. Never a feature target.
- `dev`: integration branch. Every feature PR targets `dev` and squash-merges.
- Feature branches: `feat/*`, `fix/*`, `chore/*`, `docs/*`, `refactor/*`. Branch from `dev`. Rebase onto `dev` before merge. Never merge `dev` into a feature.
- Multi-part work ships as stacked PRs: one layer per logical unit, bottom targets `dev`, merge bottom-up. Delete a merged bottom branch only after the child PR is retargeted, or GitHub closes the child for good.
- Conventional commits. Each commit builds, typechecks, and tests alone. When a commit changes dependencies, its lockfile matches its own manifest (relock per commit in a rebase `--exec`).
- A fix folds into the commit that introduced the flaw: `git commit --fixup=<sha>`, then `git rebase -i --autosquash <sha>^`. Foundation-forced changes fold; voluntary refactors stay standalone with a reworded message.
- No attribution trailers. No "address review" commits on an unmerged branch.
- Push a rebased branch with `--force-with-lease` only.

## Script vocabulary

Every repository exposes the same task names, whatever the language runs them:

| Task | Meaning |
| --- | --- |
| `dev` | start the app or watcher; assume it is already running before starting another |
| `build` | produce artifacts; depends on `generate` |
| `typecheck` | static checks with no emit |
| `test` | the full suite |
| `check` | lint and format verification, no writes |
| `fix` | lint and format with writes |
| `clean` | remove generated and cached files |
| `generate` | codegen from specs or schemas |

- A pre-commit hook runs `fix` and stages the result. Automated commits skip hooks.
- Hooks and automations call the underlying tool directly. Developers and CI call the task name.
- Language-specific runners (Bun and Turbo for TypeScript, `go` for Go) sit behind these names, never beside them.

## CI

- GitHub Actions on `pull_request` and `push` for `main` and `dev`, plus `merge_group`. Cancel in-progress runs on feature refs only.
- One composite setup action installs the toolchains and does a frozen install.
- Jobs: `check`, then `typecheck`, `build`, `test`. Add a dependency-consistency check where the ecosystem has one.
- Remote build cache where the runner supports it. No hand-rolled cache actions.

## Before opening a PR

- `gh pr list --state open` and `git worktree list`: know what is in flight.
- Sweep the branch for fold candidates. Rebase onto `dev`. Verify the tip: frozen install, typecheck, test, check.
- PR body says what and why in plain English. No attribution footer.
