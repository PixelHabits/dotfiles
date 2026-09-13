# How I work

Read this first. Domain detail lives in skills under `~/.agents/skills`: `repo-conventions`, `bun-first`, `effect-way`, `vercel-bun-stack-notes`. Load the one that matches the task before you start.

## Code

- Fix the cause. A workaround that needs a paragraph to justify it means the code is wrong.
- Code, comments, and docs carry no history. Git holds history. Never write "previously", "used to", "legacy", "migrated from", or describe old behavior in new code. A comment states a present constraint the code cannot show. Nothing else.
- No lint overrides. No `biome-ignore`, `eslint-disable`, `@ts-expect-error`, or rule downgrades to pass a gate. Use the framework preset or fix the code. Removing an override is a win: report it.
- A library with a bug or bad handling gets patched (`bun patch`, committed under `patches/`), never worked around. A workaround is debt.
- No `any`. `unknown` when the type is unknown. Narrow, never assert.
- No test seams in application code: no interface or injection that exists for tests. Concrete types, module mocks at the boundary.
- Route and entrypoint files show their own orchestration. Only shared machinery goes into lib packages.
- One canonical language in domain code. Translate each outside dialect once, at the lowest boundary, behind a contract plus registry.
- Loud failure over tolerated missing data. A write states final state. Blank means clear.
- Never add a database column or index field as a crutch for a design gap.
- Temporal, never `Date`. Money as exact decimal with an integer-cents invariant, never float, half-even rounding stated explicitly. Identifier codes are text.
- Simple over clever. If a simpler solution exists, propose it. If asked for too much at once, say so.

## Git and repositories

- Bare repo plus worktrees: `<root>/.bare`, `<root>/main`, `<root>/dev`, `<root>/<feature>`. Commands in `repo-conventions`.
- `main` receives merges from `dev` only. Features branch from `dev`, rebase onto `dev`, squash-merge into `dev`.
- Every commit builds and tests on its own. Fold a fix into the commit that introduced the flaw (`--fixup` plus `--autosquash`). Rebase, never merge commits. No "address review" commits on an unmerged branch.
- Conventional commit messages. No co-author trailers, generated-with text, session links, or watermarks of any kind.
- Never read `.env*`, credential, or key files. Give the user the command instead.
- Do not touch files owned by a parallel in-flight branch.

## Tooling

- Bun for runtime, package manager, test runner, and scripts. `bun run <script>`, never the bare `bun <script>` shortcut. No npm, no Yarn.
- Prefer a Bun built-in over a dependency. Check current Bun docs before choosing. Training data lags. Details in `bun-first`.
- TypeScript on the native compiler with strict presets. Effect on the server, Effect Schema at every edge. Details in `effect-way`.
- Turborepo monorepos with Ultracite on Biome, sherif, lefthook. Script names in `repo-conventions`.
- Default stack when unstated: Bun, TypeScript, Effect, TanStack Start plus Router, Vite, React, Tailwind v4, shadcn on Base UI, Neon Postgres with drizzle, Vercel.
- Assume the dev server already runs. Do not start another.

## Working with me

- Situation check before any claim about repository state: open PRs, worktrees, recent notes.
- Facts with evidence, labeled proven, inferred, or unknown. Never guess. "Not determinable from code" is a valid answer.
- Open decisions get pros and cons, then one firm recommendation. Never assume a decision was made.
- Make the reversible move now. Defer the irreversible bet until there is signal. Record a decision so it stops being re-litigated.
- Before a write to live data: dry run, per-record before and after, explicit approval.
- Plain English for anything a non-developer reads. Short sentences, active voice. No em dashes, no filler, no "should".
