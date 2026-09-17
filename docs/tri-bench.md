# The three-host bench: one message, three CLIs, side by side

`bench/journeys.py` plays a scripted conversation against one agent and grades it.
While you are writing the skill you want the other thing: a sentence in your head, and
the three answers to it next to each other before you change a paragraph.

`tools/tri_bench.py` is that page. One text box, three columns — Claude Code, Codex,
Grok Build — and a Continue button that sends the next message to all three. Each host
keeps its own session. Nothing is published; it binds loopback and holds its one page
inline.

```bash
python3 tools/tri_bench.py            # then open http://127.0.0.1:8790
```

Useful flags: `--port`, `--timeout` (seconds per host per turn, default 900),
`--skill-dir` (below), `--claude-model` / `--codex-model` / `--grok-model`
(default `grok-4.6`; the other two use each CLI's own default), `--no-grok-home-sync`.

It needs no API key: the hosts are the CLIs you are already logged into. If a column
says **Not signed in**, run that CLI's own login once in a terminal (`grok login`,
`claude`, `codex login`) and press Send again.

## What a column shows

| Line | What it is |
|---|---|
| the dot | grey idle, blue running, green done, red errored |
| `claude · model · turn N` | which CLI, which model, how many turns this session has had |
| `session …` | the CLI session the turns are going to. Codex has none: `codex exec` has no resume, so its transcript is replayed each turn, which is what `bench/journeys.py` does |
| turn card head | wall seconds, then tokens and cost **when the host reports them**. Claude reports both; Codex reports tokens; Grok's headless envelope has none, so the bench asks `grok usage <session id>` and shows nothing if that says nothing. A missing number stays missing |
| the reply | the host's own words, rendered as plain text with its line breaks |
| `score 0.86` and `failed: …` | journey mode only: `score_turn` from `bench/journeys.py`, the same grader the runner uses, and the checks that failed |

A host that errors shows the error text in its own column and never blocks the other
two — they run in parallel threads.

Everything is also written to `.pea-playground/tri/<session>/<host>/transcript.jsonl`,
one JSON object per line: the session line first, then one card per turn with the
prompt, the reply, the wall time, the usage and the error if there was one. The folder
link at the top of the page opens that directory.

## Pinning a skill

By default the bench stages the working tree's `skills/vet-flat` into each host's own
skill folder inside a per-session workdir, so the three hosts run identical text:

| Host | Where the copy goes inside the workdir |
|---|---|
| Claude Code | `.claude/skills/vet-flat` |
| Codex | `.agents/skills/vet-flat` |
| Grok Build | `.grok/skills/vet-flat` (readable, not discovered — see below) |

`--skill-dir bench/ab/skill-variants/skill-<commit>` pins another folder instead. Each
host is then told to use it the way the journeys runner tells it: the pinned SKILL.md,
`references/inputs.md` and `references/onboarding.md` travel in the system prompt
(`--append-system-prompt` for Claude, `AGENTS.md` for Codex, `--rules` for Grok), plus
one line naming the folder so the model reads the rest of the pinned skill from there.
That one line is the only difference between the three hosts' prompts.

Two things to know. A **journey** run is graded against the runner's own system prompt
(`journeys.system_prompt`, which reads `dist/prompt-pack/INSTRUCTIONS.md`) so its scores
can be read beside `bench/journeys.py` results — `--skill-dir` still decides what each
host has staged, but it does not change that prompt pack. And playing a journey starts a
fresh session on every host, because a CLI session cannot be given a new system prompt
half way through.

Each host is given the same reach: Claude `Read` only, Codex a read-only sandbox, Grok
`read_file,grep,list_dir` with `--sandbox read-only` and web search off. A difference
between the three columns is the host, not the permissions.

## Where Grok looks for skills (probed 2026-09-17, Grok Build 1.0.30)

Grok's own README lists four skill locations in priority order: `./.grok/skills/`,
`<repo_root>/.grok/skills/`, `~/.grok/skills/` and `~/.claude/skills/`. Only the
user-scoped ones actually answered:

* A copy at `.grok/skills/pea-princess`, `.agents/skills/pea-princess` **or**
  `.claude/skills/pea-princess` inside the working folder never appeared in
  `grok inspect --json` — not in a gitignored folder under this repo, and not in a
  fresh git repository of its own outside it (`projectTrusted: false`). Grok's README
  notes that repo-scoped skills are filtered out when `.gitignore` ignores them; the
  second probe says a project-level copy was not read here even when it was not ignored.
* `~/.agents/skills/pea-princess` — where the author's copy is installed — **is** read,
  reported as a `user` source.
* `~/.grok/skills/pea-princess` is read too, and **outranks** the `~/.agents` copy: a
  marker skill placed there replaced the installed one in `grok inspect --json`.

So a project-level pin cannot reach Grok. The bench therefore syncs the pinned skill
into `~/.grok/skills/pea-princess` at startup, says so in a banner on the page, and
takes it back out when the server stops (only if the marker file inside it names that
session). A folder that was not made by the bench is never overwritten — the page says
that too, and that Grok is then answering from that copy rather than from the pin.
`--no-grok-home-sync` turns the sync off, with the same warning. If a hard kill leaves
a copy behind, `rm -rf ~/.grok/skills/pea-princess` restores the author's install.

`--agent grok` also works for `bench/journeys.py --journey …` now, with the same
command shape (`grok_command` in `bench/journeys.py`). Its calls go straight through
`bench/launch.py`: the durable call boundary in `bench/legacy_control.py` reads
telemetry for the two CLIs it was written for and refuses every other family, so a Grok
journey run has no durable call accounting.

## Privacy

Everything you type goes to three model providers through the CLIs' own logins, exactly
as it would if you typed it into them yourself. Do not paste anything into this page you
would not paste into all three.

Writes stay inside `.pea-playground/tri/<session>/` (gitignored), with the one named
exception above, and every write goes through a check that refuses a path outside it.
An attachment name is reduced to a plain file name, so a pasted "`../../etc/passwd`" is
written as `passwd` inside the host's own folder and nowhere else. Attachment text is
written with `materialise_attachments` from the runner, which drops a leading title line
that is not part of the file.

The bench opens no network connection of its own: it binds 127.0.0.1, checks the `Host`
and `Origin` headers and a client header on every API call, serves one page held inline
with no CDN and no external asset, and starts the three CLIs. Session folders and
transcripts are private local files and can contain listings, addresses and provider
metadata — treat them the way `SECURITY.md` treats raw experiment logs.

## What it does not do

* It does not retry. One physical attempt per host per turn, the way `bench/launch.py`
  runs every other bench; a failed turn shows its error and stays in the transcript.
* Codex has no session to resume, so its column pays for the whole conversation again
  every turn. That is visible in its token count and is not a bug in the bench.
* One turn at a time: while three hosts are running, Send and Play are disabled.
* `Stop` ends a journey after the turn that is already running; it does not kill a CLI.
