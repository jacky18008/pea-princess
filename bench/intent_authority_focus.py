#!/usr/bin/env python3
"""Focused, tool-free conversation-policy follow-up to the frozen v1 study.

The initial package-reading lane proved too expensive for the 2M token plan.
This separate version inlines exact relevant public guidance, retains the
same cases/repetitions, and preserve the original lane's incomplete evidence.
Preparation/inspection never dispatch; run uses the existing durable controller.
"""

import argparse
import json
import subprocess
import sys

import intent_authority_ablation as study
from call_control import CallControlError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--out", required=True)
    prep.add_argument("--baseline", required=True)
    prep.add_argument("--case", action="append", required=True)
    prep.add_argument("--rubric", required=True)
    prep.add_argument("--max-total-tokens", type=int, required=True,
                      help="remaining actor budget after all preserved v1 usage")
    run = commands.add_parser("run")
    run.add_argument("--out", required=True)
    run.add_argument("--max-new-calls", type=int, default=1,
                     help="dispatch at most this many new slots; default 1 allows a cost checkpoint")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--out", required=True)
    inspect.add_argument("--export", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = study.prepare(args.out, args.baseline, args.case, args.rubric,
                                   focused=True, max_total_tokens=args.max_total_tokens)
        else:
            _out, manifest = study._load(args.out)
            if manifest["config"].get("profile") != "inline-conversation-policy-v2":
                raise ValueError("focus entry point requires an inline-conversation-policy-v2 plan")
            result = study.run(args.out, max_new_calls=args.max_new_calls) if args.command == "run" else study.inspect(args.out, args.export)
    except (ValueError, OSError, CallControlError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
