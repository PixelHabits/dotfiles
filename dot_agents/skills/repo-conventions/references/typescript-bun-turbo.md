# TypeScript monorepo: Bun plus Turborepo

Applies to TypeScript workspaces. Other languages in the same repository keep their own idiom behind the shared task names.

## Workspace shape

- `package.json` workspaces: `apps/*`, `packages/*`, `tooling/*`. `packageManager` pinned to Bun.
- Shared tsconfig presets in `tooling/typescript` (`base`, `api`, `library`) behind one `@<org>/tsconfig` workspace dev dependency. Strict, `noUncheckedIndexedAccess`, bundler resolution, no emit. Native TypeScript compiler.
- `bunfig.toml`: `minimumReleaseAge` gate, `minimumReleaseAgeExcludes` for exact-pinned packages, isolated linker.
- Vendored UI components live in their own package and are never hand-edited. Override at call sites.

## Scripts

Root `package.json` runs turbo; a root-only twin handles files outside any workspace.

| Script | Root | Each package |
| --- | --- | --- |
| `dev` | `turbo run dev` (persistent, no cache) | start the app |
| `build` | `turbo run build` (depends on `generate`, `^build`) | build |
| `typecheck` | `turbo run typecheck` | `tsc -p tsconfig.json --noEmit` |
| `test` | `turbo run test` | `bun test --isolate` |
| `check` | `turbo run check //#_check` | `ultracite check` |
| `fix` | `turbo run fix //#_fix` | `ultracite fix` |
| `clean` | `turbo run clean //#_clean` | `git clean -Xdf <dirs>` |
| `generate` | `turbo run generate` | codegen |

- Root twins `_check`, `_fix`, `_clean`. `_fix` also runs `sherif --fix`.
- `postinstall`: `sherif`. `prepare`: `lefthook install` plus any compiler patch step.
- lefthook pre-commit: `bun run fix` with `stage_fixed`. Automated commits set `LEFTHOOK=0`.
- Hooks call `bun x ultracite fix <file>` directly, not the turbo wrapper.
- `bun run --parallel a b` for fan-out inside one package. Turbo owns the cross-package graph.
- Ultracite on Biome with the framework preset per package. No rule disables. Formatter: tabs.

## CI specifics

- Composite setup action: install Bun at the pinned version, `bun install --frozen-lockfile`.
- `bun dedupe --check` before `bun run check`.
- Turbo remote cache on Vercel.
