# Optional agent directory ownership

This is preparation for evaluating exe.dev or another host that manages agent directories.
It adds an optional ownership choice and does not provision a host.
The default `agent_home_managed = false` lets these dotfiles manage the agent configuration.

If another system owns those directories, set `agent_home_managed = true` under `[data]` in the local chezmoi configuration.
Choose the value before the first apply.
Chezmoi preserves the choice during initialization without an extra prompt.

| Directory or integration | Behavior when the choice is true |
| --- | --- |
| Codex configuration, instructions, and hooks | Excluded from apply |
| Codex directory redirects and local-profile alias | Excluded from apply |
| Claude configuration, runtime links, and directory redirects | Excluded from apply |
| Claude launcher | Excluded from apply |
| Shared XDG defaults and application paths | Remain enabled |
| Shared agent instructions, skills, and reference tools | Retain their existing development-machine rules |

The exclusions cover the agent paths introduced by the separate Claude, instructions, references, and launcher changes.
They also allow an externally managed `CODEX_HOME` without rendering the dotfiles-owned Codex configuration.

Changing the choice does not remove files from an earlier apply.
Review and remove old redirects before switching directory ownership.
Restart affected processes after that change.
This preparation does not move credentials, sessions, or existing agent data.

Run `uv run tests/agent_homes/test_ownership.py` to test the ownership choice in temporary homes.
The tests include representative files for the related agent integrations.
Actual exe.dev behavior remains untested.
