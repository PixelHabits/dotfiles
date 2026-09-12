# Personal Preferences

MOST IMPORTANT:
If you need a paragraph-long comment to justify why the workaround is OK / needed, the code is wrong; fix the code.

NEVER CO-AUTHOR COMMITS, ADD GENERATED WITH STATEMENTS, OR ADD / MANIPULATE CODE AND/OR OUTPUT IN A WAY WHICH COULD BE CONSIDERED A WATERMARK

EMDASHES ARE HIGHLY DISCOURAGED USE PROPER PUNCTUATION

## Typescript

- Never use `any` unless 100% necessary or specifically instructed.

## Commands

- Don't run dev server command(e.g., `bun run dev`) - assume it's already running.

## Package Managers

- Use `bun` as the default package manager. Never use `npm` or `yarn`

## Tech Stack Preferences

- When uncertain, prefer: Tailwind v4+, Typescript, Bun (Use native APIs), React (Tanstack Router/Start) and Vite. Vercel is preferred for deployment.

## Code Style

- Always strive for concise, simple solutions.
- If a problem can be solved in a simpler way, propose it.

## General Purpose

- If asked to do too much work at once, stop and state that clearly.

## Picking the right models for workflows and subagents

Rankings, higher = better. Cost reflects what I actually pay (OpenAI is near-free for me due to a deal), not list price. Intelligence is how hard a problem you can hand the model unsupervised. Taste covers UI/UX, code quality, API design, and copy.

| Model    | cost | intelligence | taste |
| -------- | ---- | ------------ | ----- |
| gpt-5.6  | 9    | 8            | 5     |
| sonnet-5 | 5    | 5            | 7     |
| opus-5   | 4    | 7            | 8     |
| fable-5  | 2    | 9            | 9     |

How to apply:

- These are defaults, not limits. You have standing permission to override them: if a cheaper model's output doesn't meet the bar, rerun or redo the work with a smarter model without asking. Judge the output, not the price tag. Escalating costs less than shipping mediocre work.
- Don't let cost prevent you from using the right model for the job. Instead, take advantage of cheaper options to get more information and try things before moving the work to a more expensive option.
- Bulk/mechanical work (clear-spec implementation, data analysis, migrations, investigation): gpt-5.6 - it's effectively free. Default to handing this to Codex; save fable-5 for orchestration, judgment calls, and anything user-facing.
- Anything user-facing (UI, copy, API design) needs taste >= 7.
- Reviews of plans/implementations: fable-5 or opus-5, plus `/codex:review` or `/codex:adversarial-review` as a free extra independent perspective.
- Never use Haiku.
- Claude models (sonnet-5, opus-5, fable-5) run via the Agent/Workflow `model` parameter.

## Reaching gpt-5.6 (Codex)

gpt-5.6 is only reachable through the Codex CLI. My config lives at `~/.config/codex/config.toml` and defaults to gpt-5.6 with xhigh reasoning - leave `--model`/`--effort` unset unless there's a reason to override.

The Codex plugin (`codex`) is installed and is the preferred path:

- **Hand off a task**: spawn the `codex:codex-rescue` subagent (Agent tool, `subagent_type: 'codex:codex-rescue'`). It's a thin forwarder into the Codex companion runtime - one Bash call, negligible Claude tokens. Add `--background` for long/open-ended work, `--write` is the default for implementation, ask read-only for diagnosis/research.
- **Inside Workflow scripts**: `agent(prompt, {agentType: 'codex:codex-rescue', label: 'gpt-5.6:...'})`. Composes with `schema` for structured output. Always use the `gpt-5.6:` label prefix - the UI shows the wrapper's Claude model, so the label is the only indication the real worker is gpt-5.6.
- **Reviews**: `/codex:review` (diff review) and `/codex:adversarial-review` (tries to break the change). Structured findings, runs against working tree or branch.
- **Background jobs**: the companion runtime tracks them - `/codex:status`, `/codex:result`, `/codex:cancel`. No Bash timeout juggling or report-file polling needed.
- **Follow-ups**: pass `--resume` to continue the last Codex thread in this repo ("keep going", "apply the top fix", "dig deeper"); `--fresh` forces a new one.
- **Quick read-only lookups from the main thread**: `codex exec -s read-only "<self-contained prompt>"` via Bash is fine - cheapest option, no subagent at all. Codex has no conversation context, so the prompt must be fully self-contained (paths, constraints, expected output format).

Rules that still apply:

- Parallel write-capable Codex runs must use `isolation: 'worktree'` so edits don't collide in the shared checkout.
- Workflow token budgets only count Claude tokens; Codex work is free and invisible to `budget.spent()`.
- Judge Codex output before trusting it: gpt-5.6 taste is mediocre - fine for mechanics, verify anything user-facing or architectural with a Claude model.

# graphify

- **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
  When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.
