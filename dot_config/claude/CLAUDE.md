@~/.config/agents/AGENTS.md

# Claude Code only


## Delegation

Personal cost scores below describe user preference, not public pricing. Higher scores are better.

| Model | Cost | Intelligence | Taste |
| --- | --- | --- | --- |
| gpt-5.6 | 9 | 8 | 5 |
| sonnet-5 | 5 | 5 | 7 |
| opus-5 | 4 | 7 | 8 |
| fable-5 | 2 | 9 | 9 |

- Use available models only. Never Haiku. Escalate poor output without asking. Judge quality, not cost alone.
- Mechanical work and investigation: prefer Codex. Orchestration, judgment, user-facing work: prefer fable-5. UI, copy, and API design need taste >= 7.
- Review: fable-5 or opus-5. Add a Codex independent review when available. Verify architectural and user-facing Codex output.
- Claude model selection: Agent/Workflow `model`. Codex selection: installed CLI configuration; omit model and effort overrides by default.

## Codex integration, when installed

- Preferred handoff: `codex:codex-rescue` Agent subagent. `--write` for implementation; read-only for diagnosis. `--background` for long tasks. See `codex-notes` for Codex sandbox limits and job tracking.
- Workflow: `agent(prompt, {agentType: 'codex:codex-rescue', label: 'gpt-5.6:...'})`; `schema` for structured results. Label actual Codex model because wrapper UI shows Claude model.
- Plugin slash commands are user-only. Do not invoke them through Skill. Discover the installed companion script and read its command instructions before using its runtime.
- Rescue forwards tasks only. Background launch means started, not finished. Parent checks `status <job-id> --json`, then `result <job-id> --json` in the same repo/session. Wait for terminal status; inspect result and errors before claiming success. Empty output, launch exit zero, or wrapper completion proves no task outcome.
- Follow-up: `--resume` continues repo thread; `--fresh` starts new thread.
- Quick lookup fallback: `codex exec -s read-only "<self-contained prompt>"`. Include paths, constraints, expected output. Codex has no conversation context.
- Parallel writers need `isolation: 'worktree'`. Workflow budgets count Claude tokens only, not Codex usage.
- Missing plugin: discover installed capabilities before choosing fallback. Never invent tools or model availability.
