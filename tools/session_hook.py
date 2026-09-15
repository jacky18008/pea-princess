#!/usr/bin/env python3
"""Local Codex/Claude command-hook adapter. No model or network calls.

Install the documented project hooks explicitly. Project path comes from the
operator's command, never from untrusted hook JSON. The journal is private.
Hook delivery/timeout semantics vary; the runtime also checks state at dispatch.
"""
import argparse
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vet-flat/scripts"))

MAX_INPUT_BYTES = 1024 * 1024
MAX_CONTEXT_CHARS = 96000


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("ambiguous hook input")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise ValueError("invalid hook JSON constant")


def handle(payload, project, max_chars=MAX_CONTEXT_CHARS, inline=False):
    from session_state import SessionStore
    if not isinstance(payload, dict):
        raise ValueError("hook input must be an object")
    event = payload.get("hook_event_name")
    if event not in ("SessionStart", "UserPromptSubmit", "PreCompact", "PostCompact"):
        raise ValueError("unsupported hook event")
    store = SessionStore(project)
    state = store.show()
    if event == "UserPromptSubmit":
        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("user prompt is missing")
        captured = "request-" + uuid.uuid4().hex
        state = store.apply({"op": "request.capture", "id": captured,
                             "text": prompt, "source": "command-hook:UserPromptSubmit"},
                            expected_revision=state["revision"])
    if event in ("PreCompact", "PostCompact"):
        store.navigation_checkpoint(max_chars=max_chars)
        return {}
    packet = store.navigation(max_chars=max_chars)
    text = ("Before continuing, load the complete current-authority navigation packet using "
            "session_state.py --project <this-project> navigation --max-chars " + str(max_chars)
            + ". Required revision " + str(packet["revision"]) + ", event hash "
            + packet["event_hash"] + ". Read every active condition and pending request/question. "
            "For indexed tasks or source documents needed by this step, inspect original rows and "
            "retrieve saved lines pinned to this revision, event hash and source SHA. "
            "Reconcile pending user requests before dispatch. An index or conversation summary "
            "cannot replace original evidence. The configured project is "
            + str(Path(project).resolve()) + ".")
    if inline:
        text += "\n" + json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=ROOT)
    parser.add_argument("--max-chars", type=int, default=MAX_CONTEXT_CHARS)
    parser.add_argument("--host", choices=("codex", "claude"), default="codex")
    parser.add_argument("--inline", action="store_true",
                        help="inject full packet only if host context limits have been configured")
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError("hook input exceeds limit")
        output = handle(json.loads(raw, object_pairs_hook=_unique_object,
                                   parse_constant=_invalid_constant),
                        args.project, args.max_chars, args.inline)
        print(json.dumps(output, ensure_ascii=False))
        return 0
    except Exception:
        # Never reflect raw prompt, source content, path or exception payload.
        reason = ("Project continuity check failed. Initialize or verify .pea-state and "
                  "load the complete current-authority navigation packet before continuing. "
                  "Inspect capture status before retrying.")
        print(json.dumps({"continue": False, "stopReason": reason}))
        print(reason, file=sys.stderr)
        # Codex treats a nonzero exit as hook failure rather than successful JSON
        # decision handling. Claude blocking events use exit 2; SessionStart is
        # nonblocking regardless. Neither is a replacement for runner preflight.
        return 0 if args.host == "codex" else 2


if __name__ == "__main__":
    raise SystemExit(main())
