# Optional project hooks

Read [the harness guide](session-harness.md) first. Initialize state before enabling hooks. The examples use a 24,000-character local packet ceiling, independently of the host’s short hook-output limit. These are templates, not active settings; this work did not change global configuration or grant host trust. Official host behavior and sources are in [source notes](harness-source-notes-2026-09-09.md).

## Codex

Merge into the project's `.codex/hooks.json`. Replace `/ABSOLUTE/PROJECT` with the actual checkout path, quoting paths with spaces. Trust the project through the host’s normal project-trust flow, then use Codex `/hooks` to review and trust the exact hook definitions; never bypass the trust registry.

```json
{
  "hooks": {
    "SessionStart": [{"matcher": "startup|resume|clear|compact", "hooks": [{"type": "command", "command": "python3 \"/ABSOLUTE/PROJECT/tools/session_hook.py\" --project \"/ABSOLUTE/PROJECT\" --host codex --max-chars 24000", "timeout": 10, "additionalContextLimit": 2500}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python3 \"/ABSOLUTE/PROJECT/tools/session_hook.py\" --project \"/ABSOLUTE/PROJECT\" --host codex --max-chars 24000", "timeout": 10, "additionalContextLimit": 2500}]}],
    "PreCompact": [{"matcher": "manual|auto", "hooks": [{"type": "command", "command": "python3 \"/ABSOLUTE/PROJECT/tools/session_hook.py\" --project \"/ABSOLUTE/PROJECT\" --host codex --max-chars 24000", "timeout": 10}]}]
  }
}
```

The adapter returns successful JSON with `continue:false` on Codex errors. Session context output is a short pointer; the complete packet must still be read or inserted by `session_runner.py`.

## Claude Code

Merge into `.claude/settings.local.json` for personal setup, or shared project settings deliberately. Do not overwrite existing hooks. The documented exec form avoids shell interpolation of the prompt:

```json
{
  "hooks": {
    "SessionStart": [{"matcher": "startup|resume|clear|compact", "hooks": [{"type": "command", "command": "python3", "args": ["${CLAUDE_PROJECT_DIR}/tools/session_hook.py", "--project", "${CLAUDE_PROJECT_DIR}", "--host", "claude", "--max-chars", "24000"], "timeout": 10}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python3", "args": ["${CLAUDE_PROJECT_DIR}/tools/session_hook.py", "--project", "${CLAUDE_PROJECT_DIR}", "--host", "claude", "--max-chars", "24000"], "timeout": 10}]}],
    "PreCompact": [{"matcher": "manual|auto", "hooks": [{"type": "command", "command": "python3", "args": ["${CLAUDE_PROJECT_DIR}/tools/session_hook.py", "--project", "${CLAUDE_PROJECT_DIR}", "--host", "claude", "--max-chars", "24000"], "timeout": 10}]}]
  }
}
```

The adapter uses exit 2 for Claude errors. SessionStart cannot block regardless of exit code. Timeout behavior differs across events and SDKs. `CLAUDE_PROJECT_DIR` can remain the original checkout after entering a worktree; configure the intended project explicitly for separate worktree state. The adapter never trusts input `cwd` to choose another project's state.

### Optional: the pre-send checker as a Stop hook (Claude Code only)

`bench/stop_check_hook.py` runs the skill's `scripts/reply_check.py` on the reply Claude is about to send and, when it
finds something (a number without a source, a preference written as an exclusion, internal jargon, a decision
stated as the person's), blocks the stop with the findings so the model revises — at most twice a turn
(`PEA_STOP_MAX`), then the reply goes through. Measured 2026-09-15 on 15 replayed turns (`docs/EXPERIMENTS.md`,
"Stop-hook enforcement"): 13 of 15 replies were revised at least once, judge quality unchanged, missing work
unchanged within noise, cost +18%. It is **not on by default**; turn it on when bare figures in replies bother
you more than the extra revision turns.

```json
{
  "hooks": {
    "Stop": [{"hooks": [{"type": "command", "command": "python3", "args": ["${CLAUDE_PROJECT_DIR}/bench/stop_check_hook.py"], "timeout": 30}]}]
  }
}
```

`PEA_REPLY_CHECK` points the hook at another copy of `reply_check.py` (default: the installed skill's,
`~/.claude/skills/pea-princess/scripts/reply_check.py`). Codex has a `stop` hook event too (`[features] hooks = true`);
untested here. Other hosts: run the checker by hand on the draft.

## Verify before relying on automation

Test capture → resolve → checkpoint → resume in a throwaway initialized project, including an integrity failure. Check that the host runs the hook and respects its response. Unit tests cannot prove a host configuration is active.

Do not enable `--inline` without checking all host context limits; a host can truncate long hook output. The default pointer stays short. `session_runner.py` deterministically inserts the complete packet into each managed request and stops on overflow or stale state. These hooks do not create schedules or restart paused Claude experiments.
