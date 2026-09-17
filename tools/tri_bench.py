#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Three hosts, one message, three sessions: the same skill answering side by side.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

WHY THIS EXISTS
===============
``bench/journeys.py`` plays a scripted conversation against one agent and grades it.
Writing the skill is the other way round: you have a sentence in your head, you want to
know what it does to Claude Code, to Codex and to Grok Build, and you want to see the
three answers next to each other before you change a paragraph. Doing that by hand means
three terminals, three session ids to keep straight, and no way to ask the follow-up on
all three at once.

This is a loopback page that does it. One text box, three columns, a Continue button.
Each host keeps its own session - Claude and Grok carry the conversation in the CLI's
own session, Codex has no resume so its transcript is replayed each turn - and every
turn is written to ``.pea-playground/tri/<session>/<host>/transcript.jsonl``.

The commands, the prompts, the pasted-text attachments and the grader all come from
``bench/journeys.py`` and ``bench/launch.py``. Nothing about how a host is called lives
here twice.

A message can also carry files - the photo from the viewing, the agent's PDF, a page
saved as text. They are kept once in the session folder and copied into every enabled
host's working folder under ``attachments/<turn>/``, so each CLI opens them with its own
Read tools. The bench reads none of them: no OCR, no conversion, no text extraction.

WHAT IT DOES NOT DO
===================
No network of its own: it binds 127.0.0.1, serves one page it holds inline, and starts
the CLIs the author is already logged into. It needs no API key. Model requests leave the
machine through those CLIs' own logins, exactly as they do when the author types into
them. Everything it writes stays in ``.pea-playground/tri/<session>/``, with one named
exception it announces on the page: Grok Build 1.0.30 reads no project-level skill
folder, so the pinned skill is also synced into ``~/.grok/skills/pea-princess``.

Run:  python3 tools/tri_bench.py          # then open http://127.0.0.1:8790
"""
import argparse
import collections
import io
import json
import os
import re
import shutil
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
BENCH = os.path.join(ROOT, "bench")
if BENCH not in sys.path:
    sys.path.insert(0, BENCH)
import journeys                    # noqa: E402  commands, prompts, attachments, grading
import launch                      # noqa: E402  the shared launcher: one attempt, tails, usage
import legacy_control              # noqa: E402  only for its codex event-stream reply reader

HOSTS = ("claude", "codex", "grok")
HOST_LABEL = collections.OrderedDict([("claude", "Claude Code"), ("codex", "Codex"),
                                      ("grok", "Grok Build")])
HOST_CLI = {"claude": "claude", "codex": "codex", "grok": "grok"}
DEFAULT_MODEL = {"claude": None, "codex": None, "grok": journeys.GROK_MODEL}
DEFAULT_PORT = 8790
DEFAULT_TIMEOUT = int(os.environ.get("VETFLAT_TURN_TIMEOUT", 900))
PLAYGROUND = os.path.join(ROOT, ".pea-playground", "tri")
GROK_HOME_SKILL = os.path.join(os.path.expanduser("~"), ".grok", "skills", "pea-princess")
GROK_SYNC_MARKER = ".tri-bench-synced"
MAX_BODY = 400000          # one pasted page is large; a listing is not a megabyte
MAX_MESSAGE = 40000

# What the page may attach to a message. The list is short on purpose: the photo you took
# on the viewing, the PDF the agent sent, a page saved as text. Anything else can be
# pasted into the attachment box as words.
MAX_UPLOAD = 20 * 1024 * 1024      # all the files of one message together
MAX_FILES = 8
UPLOAD_SLACK = 64 * 1024           # the boundaries and headers around those bytes
MAX_PARTS = 40                     # a sanity bound on the parser, not the file limit
TEXT_KINDS = ("txt", "md", "html", "json", "csv")
ACCEPTED = ("pdf", "png", "jpg", "jpeg", "webp", "heic", "webarchive") + TEXT_KINDS

# What a bench turn may do, per host: read the folder it was given, nothing else. Claude
# gets Read, Codex a read-only sandbox, Grok its read-only three with web search off, so
# a difference between the three columns is the host and not the permissions.
CLAUDE_TOOLS = journeys.CLAUDE_TOOLS_READ
CODEX_SANDBOX = "read-only"

BENCH_NOTE = (
    "# How this bench works (do not repeat in replies)\n\n"
    "The pea-princess skill under test is pinned in your working folder at %s/. It is the "
    "whole folder: when the skill sends you to one of its own reference files, read it from "
    "there. Nothing outside that folder is part of the exercise.\n"
    "Answer the person directly, in the language they wrote in. Keep execution settings and "
    "instruction headings internal, and use everyday housing language. Do not write a JSON "
    "report unless the person asks for one.\n"
    "You have no shell and no browser in this bench, and web search is off: work from the "
    "skill, from what the person tells you, and say plainly what you would have to look up.")


class BenchError(ValueError):
    """Something the page asked for that the bench will not do."""


# ----------------------------------------------------------------- small helpers --
def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def safe_name(name, fallback="pasted.txt"):
    """A pasted attachment's name as a plain file name inside the run's folder."""
    base = os.path.basename((name or "").strip())
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-.")
    if not base or base in (".", "..") or len(base) > 80:
        return fallback
    return base


def human_size(size):
    """412 KB, 1.8 MB: what the page shows and what the hosts are told."""
    if size < 1024:
        return "%d B" % size
    if size < 1024 * 1024:
        return "%d KB" % int(round(size / 1024.0))
    return "%.1f MB" % (size / 1048576.0)


def upload_name(raw, taken=(), index=1):
    """A chosen file's name as a plain file name, unique inside this turn.

    Basename only, no separator, nothing but ASCII letters, digits, dot, dash and
    underscore. A browser that sends ``C:\\Users\\me\\..\\photo (1).JPG`` lands as
    ``photo-1.jpg`` inside the turn's own folder and nowhere else. Returns
    ``(name, extension)``; the extension is what the type gate is decided on."""
    base = os.path.basename((raw or "").replace("\\", "/").strip().rstrip("/"))
    stem, dot, ext = base.rpartition(".")
    if not dot:
        stem, ext = base, ""
    ext = re.sub(r"[^a-z0-9]+", "", ext.lower())[:10]
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._")[:60] or "file-%d" % index
    tail = "." + ext if ext else ""
    name, count = stem + tail, 1
    while name in taken:
        count += 1
        name = "%s-%d%s" % (stem, count, tail)
    return name, ext


def sniff(kind, raw):
    """Do the first bytes agree with the name? The magic number, not the extension.

    This is not a virus scan and not a decoder. It stops an archive renamed ``.pdf`` and
    a name that promises a photo over something else; it says nothing about whether the
    file is safe to open, which is why the hosts get a read-only copy and nothing more."""
    if kind == "pdf":
        return b"%PDF-" in raw[:1024]
    if kind == "png":
        return raw[:8] == b"\x89PNG\r\n\x1a\n"
    if kind in ("jpg", "jpeg"):
        return raw[:3] == b"\xff\xd8\xff"
    if kind == "webp":
        return raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
    if kind == "heic":
        brands = (b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1")
        return raw[4:8] == b"ftyp" and raw[8:12] in brands
    if kind == "webarchive":
        return raw[:8] == b"bplist00"
    if kind in TEXT_KINDS:
        if b"\x00" in raw:
            return False
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            return False
        return True
    return False


def accept_uploads(files):
    """[(safe name, kind, bytes)] for what the page attached, or the sentence it failed on.

    Everything is decided here: how many, how big together, the extension, and whether the
    bytes agree with it. One bad file stops the whole message, because half a message
    reaching three hosts is worse than none - and the page says which file and why."""
    files = list(files or [])
    if len(files) > MAX_FILES:
        raise BenchError("that is %d files; the bench takes %d with one message."
                         % (len(files), MAX_FILES))
    total = sum(len(data) for _name, data in files)
    if total > MAX_UPLOAD:
        raise BenchError("those files come to %s together; the bench takes %s with one "
                         "message." % (human_size(total), human_size(MAX_UPLOAD)))
    out, taken = [], set()
    for index, (raw, data) in enumerate(files, 1):
        name, kind = upload_name(raw, taken, index)
        if kind not in ACCEPTED:
            raise BenchError("%s: the bench takes %s files only. Anything else you can paste "
                             "into the attachment box as text." % (name, ", ".join(ACCEPTED)))
        if not data:
            raise BenchError("%s is empty, so nothing was sent." % name)
        if not sniff(kind, data):
            raise BenchError("%s is not a %s file inside, whatever its name says, so nothing "
                             "was sent." % (name, kind))
        taken.add(name)
        out.append((name, kind, data))
    return out


def webarchive_main_document(data):
    """The HTML inside a Web Archive (what a phone's share sheet or Safari saves), or None."""
    try:
        import plistlib
        doc = plistlib.loads(data)
        main = doc.get("WebMainResource") if isinstance(doc, dict) else None
        body = main.get("WebResourceData") if isinstance(main, dict) else None
        if not isinstance(body, (bytes, bytearray)):
            return None
        return bytes(body).decode(str(main.get("WebResourceTextEncodingName") or "utf-8"), "replace")
    except Exception:  # noqa: BLE001 - not an archive we can open; the hosts still get the file
        return None


def attachment_line(uploaded):
    """The one line the hosts are told: what arrived, where it is, how big it is."""
    if not uploaded:
        return ""
    line = "附件（在你的工作資料夾）：" + "、".join(
        "%s (%s)" % (item["rel"], human_size(item["size"])) for item in uploaded)
    if any(item["kind"] == "pdf" for item in uploaded):
        line += "\n（PDF 可以用你自己的讀檔工具直接打開，不用先轉檔。）"
    return "\n\n" + line


def thousands(value):
    try:
        return "{:,}".format(int(value))
    except (TypeError, ValueError):
        return str(value)


def usage_line(usage):
    """One short line of what the host said it spent, or "" when it said nothing.

    A missing number is missing: nothing here fills one in with zero."""
    if not isinstance(usage, dict) or not usage:
        return ""
    bits = []
    total = usage.get("total_tokens")
    if isinstance(total, (int, float)) and not isinstance(total, bool):
        bits.append("%s tokens" % thousands(total))
    else:
        pair = [usage.get("input_tokens"), usage.get("output_tokens")]
        if all(isinstance(v, (int, float)) for v in pair):
            bits.append("%s in / %s out" % (thousands(pair[0]), thousands(pair[1])))
    cached = usage.get("cache_read_input_tokens")
    if isinstance(cached, (int, float)) and cached:
        bits.append("%s cached" % thousands(cached))
    for key in ("total_cost_usd", "cost_usd", "cost"):
        value = usage.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            bits.append("$%.4f" % value)
            break
    return " · ".join(bits)


def journey_catalogue(path=None):
    """[(label, title)] for the page's journey select: exactly what the runner would run."""
    doc = journeys.load_journeys(path)
    out = []
    for journey in doc["journeys"]:
        for variant_id, _variant in journeys.variants_of(journey):
            label = journey["id"] + ("#" + variant_id if variant_id else "")
            out.append((label, journey["title"]))
    return out


def find_journey(label, path=None):
    """The resolved journey behind a select label (``id`` or ``id#variant``)."""
    jid, _sep, wanted = label.partition("#")
    for journey in journeys.load_journeys(path)["journeys"]:
        if journey["id"] != jid:
            continue
        for variant_id, variant in journeys.variants_of(journey):
            if (variant_id or "") == wanted:
                return journeys.resolve(journey, variant)
    raise BenchError("no journey %r in the journeys file" % label)


# -------------------------------------------------------------------- the bench --
class Bench(object):
    """One bench session: three host folders, three CLI sessions, one transcript each."""

    def __init__(self, skill_dir=None, models=None, timeout=DEFAULT_TIMEOUT,
                 root=PLAYGROUND, sync_grok_home=True, journeys_path=None, runner=None):
        self.skill_dir = os.path.abspath(skill_dir or journeys.SKILL_DIR)
        self.models = dict(DEFAULT_MODEL)
        self.models.update(models or {})
        self.timeout = int(timeout)
        self.journeys_path = journeys_path
        self.catalogue = journey_catalogue(journeys_path)
        self.sync_grok_home = bool(sync_grok_home)
        self.runner = runner or launch.run          # the tests hand in their own
        self.session = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self.dir = os.path.join(os.path.abspath(root), self.session)
        self.lock = threading.Lock()
        self.notes = []
        self.busy = 0
        self.turn = 0
        self.journey = None            # {"label", "turn", "turns"} while one is playing
        self.stopping = False
        self.hosts = collections.OrderedDict()
        for host in HOSTS:
            self.hosts[host] = {"enabled": True, "status": "idle", "session_id": None,
                                "resumable": host in ("claude", "grok"), "turn": 0,
                                "cards": [], "history": [], "model": self.models.get(host)}
        self.system = ""

    # -- folders ---------------------------------------------------------------
    def owned(self, path):
        """Every write goes through here: inside this session's folder or not at all."""
        root = os.path.realpath(self.dir)
        real = os.path.realpath(path)
        if real != root and not real.startswith(root + os.sep):
            raise BenchError("the bench writes only inside %s" % root)
        return path

    def host_dir(self, host):
        return os.path.join(self.dir, host)

    def work(self, host):
        return os.path.join(self.host_dir(host), "work")

    def start(self):
        """Make the session folder, stage the pinned skill for each host, say what it did."""
        os.makedirs(self.dir, mode=0o700, exist_ok=True)
        if not os.path.isfile(os.path.join(self.skill_dir, "SKILL.md")):
            raise BenchError("%s has no SKILL.md; --skill-dir must name a skill folder"
                             % self.skill_dir)
        for host in HOSTS:
            self.stage(host)
        self.system = self.chat_system()
        self.reset_sessions(self.system)
        self.write_json(os.path.join(self.dir, "session.json"), collections.OrderedDict([
            ("session", self.session), ("started_at", now()), ("skill_dir", self.skill_dir),
            ("models", self.models), ("timeout_s", self.timeout), ("notes", self.notes)]))
        return self

    def stage(self, host):
        """The pinned skill where this host expects it, plus the notes the page shows."""
        work = self.owned(self.work(host))
        home = os.path.join(work, journeys.SKILL_HOME[host])
        os.makedirs(self.owned(home), mode=0o700, exist_ok=True)
        target = os.path.join(home, "vet-flat")
        if os.path.lexists(target):
            (shutil.rmtree if os.path.isdir(target) and not os.path.islink(target)
             else os.unlink)(self.owned(target))
        shutil.copytree(self.skill_dir, self.owned(target))
        if host == "codex":
            # `codex exec` has no append-system-prompt flag; the runner delivers the
            # prompt as AGENTS.md and so does this.
            self.write_text(os.path.join(work, "AGENTS.md"), "")
        if host == "grok":
            self.notes.append(self.sync_grok())
        return target

    def sync_grok(self):
        """Grok reads no project-level skill folder, so the pinned skill goes to its home.

        Probed against Grok Build 1.0.30 on 2026-09-17: a copy at ``.grok/skills/``,
        ``.agents/skills/`` or ``.claude/skills/`` inside the working folder never appears
        in ``grok inspect --json``, in a gitignored folder or in a fresh repository of its
        own. Only the user-scope directories are read, and ``~/.grok/skills/`` outranks the
        ``~/.agents/skills/`` copy the author installed, so this sync is what Grok actually
        loads. A folder this bench did not create is never overwritten.
        """
        if not self.sync_grok_home:
            return ("Grok: home sync off. Grok Build reads no project-level skill folder, so "
                    "it will use whatever is already installed for the author, not the pin.")
        marker = os.path.join(GROK_HOME_SKILL, GROK_SYNC_MARKER)
        if os.path.isdir(GROK_HOME_SKILL) and not os.path.isfile(marker):
            return ("Grok: ~/.grok/skills/pea-princess exists and was not made by this bench, "
                    "so it was left alone. Grok is answering from that copy, not from the pin.")
        if os.path.islink(GROK_HOME_SKILL):
            return "Grok: ~/.grok/skills/pea-princess is a symlink; it was left alone."
        if os.path.isdir(GROK_HOME_SKILL):
            shutil.rmtree(GROK_HOME_SKILL)
        os.makedirs(os.path.dirname(GROK_HOME_SKILL), mode=0o700, exist_ok=True)
        shutil.copytree(self.skill_dir, GROK_HOME_SKILL)
        with io.open(marker, "w", encoding="utf-8") as fh:
            fh.write("%s\n%s\n%s\n" % (self.session, now(), self.skill_dir))
        return ("Grok: the pinned skill was synced to ~/.grok/skills/pea-princess (the only "
                "place Grok Build 1.0.30 reads it from); it outranks the author's "
                "~/.agents/skills copy for as long as it is there.")

    def unsync_grok(self):
        """Take this session's copy back out of Grok's home when the bench stops.

        Only a folder carrying this session's marker is removed, so a copy someone else
        put there, or one a still-running bench is using, is never taken away."""
        marker = os.path.join(GROK_HOME_SKILL, GROK_SYNC_MARKER)
        if not os.path.isfile(marker) or os.path.islink(GROK_HOME_SKILL):
            return False
        with io.open(marker, encoding="utf-8") as fh:
            if fh.readline().strip() != self.session:
                return False
        shutil.rmtree(GROK_HOME_SKILL, ignore_errors=True)
        return True

    # -- prompts ---------------------------------------------------------------
    def pinned_note(self, host):
        return BENCH_NOTE % os.path.join(journeys.SKILL_HOME[host], "vet-flat")

    def chat_system(self):
        """The pinned skill's own text: SKILL.md, the two protocol files, the bench note.

        Identical for the three hosts but for the one line that names the folder, because
        each host expects the skill in a different place."""
        parts = []
        for rel, title in (("SKILL.md", "THE SKILL (pinned for this bench)"),
                           (os.path.join("references", "inputs.md"),
                            "WHEN YOU CANNOT GET SOMETHING"),
                           (os.path.join("references", "onboarding.md"), "ONBOARDING")):
            path = os.path.join(self.skill_dir, rel)
            if os.path.exists(path):
                parts.append("# %s\n\n%s" % (title, journeys.read_text(path)))
        return "\n\n".join(parts)

    def system_for(self, host, system):
        return system + "\n\n" + self.pinned_note(host)

    # -- session bookkeeping ---------------------------------------------------
    def reset_sessions(self, system, journey_label=None):
        """New CLI session ids, empty replay history, and the prompt this run will use."""
        with self.lock:
            self.system = system
            self.turn = 0
            for host, state in self.hosts.items():
                state["session_id"] = str(uuid.uuid4()) if state["resumable"] else None
                state["turn"] = 0
                state["history"] = []
                state["cards"] = []
                state["status"] = "idle"
        for host in HOSTS:
            self.append_transcript(host, collections.OrderedDict([
                ("event", "session"), ("at", now()), ("host", host),
                ("session_id", self.hosts[host]["session_id"]),
                ("journey", journey_label), ("skill_dir", self.skill_dir),
                ("model", self.models.get(host)), ("system_chars", len(system))]))

    # -- files -----------------------------------------------------------------
    def write_text(self, path, text):
        self.owned(path)
        folder = os.path.dirname(path)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder, mode=0o700, exist_ok=True)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def write_json(self, path, obj):
        return self.write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")

    def append_transcript(self, host, entry):
        path = os.path.join(self.host_dir(host), "transcript.jsonl")
        self.owned(path)
        folder = os.path.dirname(path)
        if not os.path.isdir(folder):
            os.makedirs(folder, mode=0o700, exist_ok=True)
        with io.open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return path

    def keep_uploads(self, turn, turn_no):
        """The turn's attached files into the session folder, once, before anyone runs.

        This is the copy that stays. Each host then gets its own copy of these same bytes
        at the same relative path, so the three columns are reading one file and not three
        uploads that might differ."""
        staged = turn.pop("uploads", None)
        if not staged:
            return []
        folder = self.owned(os.path.join(self.dir, "attachments", str(turn_no)))
        os.makedirs(folder, mode=0o700, exist_ok=True)
        kept = []
        for name, kind, data in staged:
            with io.open(self.owned(os.path.join(folder, name)), "wb") as fh:
                fh.write(data)
            kept.append(collections.OrderedDict([
                ("name", name), ("rel", "attachments/%d/%s" % (turn_no, name)),
                ("size", len(data)), ("kind", kind)]))
            if kind == "webarchive":
                # The archive is a container; its main document is written beside it as
                # .html so that the text-only hosts can read the page too.
                page = webarchive_main_document(data)
                if page is not None:
                    html_name = name[:-len(".webarchive")] + ".html"
                    with io.open(self.owned(os.path.join(folder, html_name)), "w", encoding="utf-8") as fh:
                        fh.write(page)
                    kept.append(collections.OrderedDict([
                        ("name", html_name), ("rel", "attachments/%d/%s" % (turn_no, html_name)),
                        ("size", len(page.encode("utf-8"))), ("kind", "html"),
                        ("note", "the main document unpacked from %s" % name)]))
        turn["uploaded"] = kept
        return kept

    def copy_uploads(self, turn, work):
        """One copy per host, in that host's own folder, at the same relative path.

        The host opens it with its own Read tool: Claude Code shows a photo and a PDF,
        Codex and Grok read the text kinds. Nothing here converts anything."""
        written = []
        for item in turn.get("uploaded") or []:
            source = os.path.join(self.dir, *item["rel"].split("/"))
            target = self.owned(os.path.join(work, *item["rel"].split("/")))
            folder = os.path.dirname(target)
            if not os.path.isdir(folder):
                os.makedirs(folder, mode=0o700, exist_ok=True)
            shutil.copyfile(source, target)
            written.append(item["rel"])
        return written

    # -- one turn --------------------------------------------------------------
    def command(self, host, turn_no, user, state, system):
        """The command for this host's next turn, straight out of bench/journeys.py."""
        work = self.work(host)
        model = self.models.get(host)
        if host == "claude":
            first = turn_no == 1 or not state["session_id"]
            prompt = user if state["resumable"] or first else \
                journeys.transcript(state["history"], user)
            return journeys.claude_command(
                prompt, work, model, self.system_for(host, system), tools=CLAUDE_TOOLS,
                session_id=state["session_id"] if (state["resumable"] and first) else None,
                resume=state["session_id"] if (state["resumable"] and not first) else None)
        if host == "codex":
            # No resume in `codex exec`: the conversation is replayed every turn, and the
            # system prompt is the AGENTS.md written beside it.
            self.write_text(os.path.join(work, "AGENTS.md"), self.system_for(host, system))
            prompt = journeys.transcript(state["history"], user) if state["history"] else user
            return journeys.codex_command(prompt, work, model, CODEX_SANDBOX)
        first = turn_no == 1 or not state["session_id"]
        path = self.write_text(os.path.join(self.host_dir(host), "prompt-%02d.txt" % turn_no),
                               user if user.endswith("\n") else user + "\n")
        return journeys.grok_command(path, work, model,
                                     rules=self.system_for(host, system) if first else None,
                                     session_id=state["session_id"] if first else None,
                                     resume=None if first else state["session_id"])

    def reply_of(self, host, result, state):
        """(reply, usage, what the CLI said about itself) for one host, with its own reader."""
        if host == "claude":
            if getattr(result, "session_id", None):
                state["session_id"] = result.session_id   # the id the CLI actually used
            return result.text, result.usage, None
        if host == "codex":
            return legacy_control.reply_text(result, "codex"), result.usage, None
        raw = result.stdout or result.text
        reply, usage = journeys.grok_answer(raw)
        said = journeys.grok_session_id(raw)
        if said:
            state["session_id"] = said
        # Grok exits 0 on a refusal ("Not signed in": run `grok login` once), so the
        # column must show that sentence and not the JSON it arrived in.
        return reply, usage or journeys.grok_usage(state["session_id"]), journeys.grok_error(raw)

    def play_turn(self, host, turn_no, turn, journey, system, label):
        """Run one turn on one host and file the card. Never raises at the caller."""
        state = self.hosts[host]
        work = self.work(host)
        card = collections.OrderedDict([
            ("turn", turn_no), ("host", host), ("at", now()), ("journey", label),
            ("user", turn["user"]), ("reply", ""), ("error", None), ("note", None),
            ("wall_s", None), ("usage", None), ("usage_line", ""),
            ("session_id", state["session_id"]), ("score", None), ("failed", []),
            ("questions", None), ("files", [])])
        started = time.time()
        try:
            card["files"] = journeys.materialise_attachments(turn, work, host)
            card["files"] += self.copy_uploads(turn, work)
            user = journeys.user_message(turn, files=True) + attachment_line(
                turn.get("uploaded"))
            cmd = self.command(host, turn_no, user, state, system)
            result = self.runner(cmd, work, self.timeout, host, attempts=1,
                                 label="%s turn %d" % (host, turn_no))
            reply, usage, said = self.reply_of(host, result, state)
            card["wall_s"] = round(time.time() - started, 2)
            card["session_id"] = state["session_id"]
            card["usage"] = usage
            card["usage_line"] = usage_line(usage)
            card["note"] = said or result.note
            if not (reply or "").strip():
                card["error"] = said or result.tail_note("the CLI ") or "no reply"
            else:
                card["reply"] = reply
                state["history"].append(("user", user))
                state["history"].append(("assistant", reply))
                if journey is not None:
                    scored = journeys.score_turn(turn, reply, journey, workdir=work,
                                                 agent=host)
                    card["score"] = scored["score"]
                    card["questions"] = scored["questions_asked"]
                    card["failed"] = [row["check"] for row in scored["checks"]
                                      if row["status"] == "fail"]
        except Exception as exc:                       # a host that breaks blocks nobody
            card["wall_s"] = round(time.time() - started, 2)
            card["error"] = "%s: %s" % (type(exc).__name__, exc)
        with self.lock:
            state["status"] = "error" if card["error"] else "done"
            state["turn"] = turn_no
            state["cards"].append(card)
            self.busy = max(0, self.busy - 1)
        self.append_transcript(host, card)
        return card

    def start_turn(self, turn, hosts, journey=None, system=None, label=None):
        """Start one turn on every enabled host at once. Returns the threads."""
        system = self.system if system is None else system
        with self.lock:
            if self.busy:
                raise BenchError("a turn is still running; wait for the three columns")
            targets = [h for h in HOSTS if self.hosts[h]["enabled"] and h in (hosts or HOSTS)]
            if not targets:
                raise BenchError("no host is enabled")
            self.turn += 1
            turn_no = self.turn
            self.busy = len(targets)
            for host in targets:
                self.hosts[host]["status"] = "running"
        try:
            self.keep_uploads(turn, turn_no)
        except Exception:
            # The files never reached disk, so this turn never happened: give the number
            # back and let the page say what went wrong rather than sit on "running".
            with self.lock:
                self.turn = turn_no - 1
                self.busy = 0
                for host in targets:
                    self.hosts[host]["status"] = "idle"
            raise
        threads = []
        for host in targets:
            thread = threading.Thread(target=self.play_turn, name="tri-" + host,
                                      args=(host, turn_no, turn, journey, system, label))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        return threads

    # -- what the page asks for ------------------------------------------------
    def send(self, text, attachment=None, hosts=None, uploads=None):
        """One typed message to every enabled host, as the next turn of each session.

        ``uploads`` is what ``accept_uploads`` let through: the files go into the session
        folder and into every enabled host's folder, and the message gains one line
        saying what they are called and how big they are."""
        text = (text or "").strip()
        if not text:
            raise BenchError("type a message first")
        if len(text) > MAX_MESSAGE:
            raise BenchError("that message is longer than the bench accepts")
        if self.journey and not self.journey.get("done"):
            raise BenchError("a journey is playing; stop it first")
        turn = collections.OrderedDict([("user", text)])
        if attachment and (attachment.get("text") or "").strip():
            if len(attachment["text"]) > MAX_BODY:
                raise BenchError("that pasted page is longer than the bench accepts")
            name = (attachment.get("name") or "pasted.txt").strip()[:80] or "pasted.txt"
            turn["attachments"] = [collections.OrderedDict([
                ("name", name), ("file", safe_name(name)),
                ("text", attachment["text"])])]
        if uploads:
            turn["uploads"] = list(uploads)
        self.start_turn(turn, hosts)
        return self.turn

    def play_journey(self, label, hosts=None):
        """Play a scripted journey turn by turn on the enabled hosts, scoring each turn."""
        with self.lock:
            if self.busy or (self.journey and not self.journey.get("done")):
                raise BenchError("something is still running")
        journey = find_journey(label, self.journeys_path)
        targets = [h for h in HOSTS if self.hosts[h]["enabled"] and h in (hosts or HOSTS)]
        if not targets:
            raise BenchError("no host is enabled")
        with self.lock:
            self.journey = collections.OrderedDict([
                ("label", label), ("title", journey["title"]), ("turn", 0),
                ("turns", len(journey["turns"])), ("done", False)])
            self.stopping = False
        thread = threading.Thread(target=self.journey_loop, name="tri-journey",
                                  args=(journey, label, targets))
        thread.daemon = True
        thread.start()
        return thread

    def journey_loop(self, journey, label, targets):
        # A journey is graded against the runner's own system prompt, so the scores can be
        # read beside bench/journeys.py's. That means a fresh session on every host.
        system = journeys.system_prompt(journey, "needed")
        self.reset_sessions(system, journey_label=label)
        try:
            for index, turn in enumerate(journey["turns"], 1):
                if self.stopping:
                    break
                with self.lock:
                    self.journey["turn"] = index
                for thread in self.start_turn(turn, targets, journey=journey,
                                              system=system, label=label):
                    thread.join()
        finally:
            with self.lock:
                if self.journey:
                    self.journey["done"] = True

    def stop(self):
        with self.lock:
            self.stopping = True
        return True

    def enable(self, host, enabled):
        if host not in self.hosts:
            raise BenchError("no host called %r" % host)
        with self.lock:
            self.hosts[host]["enabled"] = bool(enabled)
        return self.hosts[host]["enabled"]

    def new_session(self):
        """Forget the three conversations and start the next one in the same folder."""
        with self.lock:
            if self.busy:
                raise BenchError("a turn is still running")
            self.journey = None
        self.reset_sessions(self.chat_system())
        return self.session

    def state(self):
        with self.lock:
            hosts = []
            for host, state in self.hosts.items():
                hosts.append(collections.OrderedDict([
                    ("id", host), ("label", HOST_LABEL[host]), ("cli", HOST_CLI[host]),
                    ("enabled", state["enabled"]), ("status", state["status"]),
                    ("session_id", state["session_id"]), ("turn", state["turn"]),
                    ("model", state["model"] or "(the CLI's own default)"),
                    ("carry", "the CLI session carries the history" if state["resumable"]
                     else "no resume in codex exec: the transcript is replayed each turn"),
                    ("cards", state["cards"])]))
            return collections.OrderedDict([
                ("session", self.session), ("folder", self.dir), ("turn", self.turn),
                ("busy", bool(self.busy)), ("notes", list(self.notes)),
                ("skill_dir", self.skill_dir), ("timeout_s", self.timeout),
                ("journey", self.journey), ("journeys", self.catalogue),
                ("hosts", hosts)])


# --------------------------------------------------------------------- the page --
# One file, held here, served from loopback: no CDN, no external asset, no font, no
# framework. Every value the page shows is written with textContent, so a reply that
# contains markup is text and stays text.
PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tri-bench</title>
<style nonce="__NONCE__">
:root { color-scheme: light dark;
  --ink:#16181d; --dim:#5b6472; --line:#d9dde4; --bg:#f6f7f9; --card:#fff;
  --warn:#8a5a00; --bad:#a3232b; --good:#1f6f43; --run:#1d4ed8; }
@media (prefers-color-scheme: dark) { :root {
  --ink:#e7e9ee; --dim:#a0a8b6; --line:#333945; --bg:#15171c; --card:#1c1f26;
  --warn:#e0a94a; --bad:#f0868c; --good:#6ed69f; --run:#86a9ff; } }
* { box-sizing:border-box }
body { margin:0; background:var(--bg); color:var(--ink);
  font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif }
main { max-width:1500px; margin:0 auto; padding:18px 20px 60px }
h1 { font-size:19px; margin:0 0 2px }
a { color:inherit }
.sub, .meta, .hint { color:var(--dim); font-size:12px }
.meta { margin:6px 0 0 }
.meta code { font-size:11px }
ul.notes { list-style:none; margin:10px 0 0; padding:0 }
ul.notes li { border-left:3px solid var(--warn); background:var(--card); padding:6px 10px;
  margin:4px 0; font-size:12px; border-radius:0 4px 4px 0 }
section.controls { background:var(--card); border:1px solid var(--line); border-radius:8px;
  padding:12px; margin:14px 0 }
textarea, input[type=text] { width:100%; font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
  color:var(--ink); background:var(--bg); border:1px solid var(--line); border-radius:6px;
  padding:8px; resize:vertical }
.row { display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-top:10px }
.row label { font-size:13px; display:inline-flex; gap:5px; align-items:center }
input[type=file] { font:12px/1.4 inherit; color:var(--dim); max-width:100% }
#chosen { overflow-wrap:anywhere }
.spacer { flex:1 1 auto }
button, select { font:13px/1.4 inherit; color:var(--ink); background:var(--card);
  border:1px solid var(--line); border-radius:6px; padding:7px 12px; cursor:pointer }
button.go { background:var(--run); border-color:var(--run); color:#fff; font-weight:600 }
button[disabled] { opacity:.45; cursor:default }
details { margin-top:10px } summary { cursor:pointer; font-size:12px; color:var(--dim) }
p.err { color:var(--bad); font-size:13px; margin:10px 0 0; white-space:pre-wrap }
.cols { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px }
@media (max-width:1000px) { .cols { grid-template-columns:1fr } }
.col { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px;
  min-width:0 }
.col.off { opacity:.5 }
.col h2 { font-size:14px; margin:0 0 2px; display:flex; align-items:center; gap:7px }
.dot { width:9px; height:9px; border-radius:50%; background:var(--line); flex:0 0 auto }
.dot.running { background:var(--run) } .dot.done { background:var(--good) }
.dot.error { background:var(--bad) }
.card { border-top:1px solid var(--line); padding-top:9px; margin-top:11px }
.card .head { display:flex; flex-wrap:wrap; gap:8px; font-size:11px; color:var(--dim) }
.card .you { font-size:12px; color:var(--dim); white-space:pre-wrap; margin:5px 0;
  padding-left:8px; border-left:2px solid var(--line) }
.card .files { font-size:11px; color:var(--dim); overflow-wrap:anywhere; margin:5px 0 0 }
.card .reply { white-space:pre-wrap; overflow-wrap:anywhere; font-size:13px; margin:6px 0 0 }
.card .bad { color:var(--bad); white-space:pre-wrap; font-size:12px; margin-top:6px }
.score { font-weight:600 } .score.low { color:var(--bad) } .score.high { color:var(--good) }
.failed { color:var(--warn); font-size:11px; margin-top:5px }
.waiting { color:var(--dim); font-size:12px; margin-top:10px }
</style>
<main>
  <h1>Three-host test bench</h1>
  <p class="sub">One message, three CLIs, three sessions. The pinned skill is staged in each
    host's own folder; every turn is written to the session folder.</p>
  <p class="meta" id="meta"></p>
  <ul class="notes" id="notes"></ul>

  <section class="controls">
    <textarea id="msg" rows="4" placeholder="Type the message all three hosts should answer."></textarea>
    <details id="attbox">
      <summary>Attachment (pasted text: a listing, a certificate, a tenancy clause)</summary>
      <div class="row"><input type="text" id="attname" placeholder="what it is, e.g. listing.txt"></div>
      <textarea id="atttext" rows="6" placeholder="Paste the page here. It is written into every host's folder under that name."></textarea>
    </details>
    <div class="row">
      <label for="files">Files</label>
      <input type="file" id="files" multiple
             accept=".pdf,.png,.jpg,.jpeg,.webp,.heic,.webarchive,.txt,.md,.html,.json,.csv">
      <span class="hint" id="chosen"></span>
      <span class="hint">up to 8 files, 20 MB a message; each host gets its own copy under
        attachments/&lt;turn&gt;/ in its working folder</span>
    </div>
    <div class="row" id="hostrow"></div>
    <div class="row">
      <button class="go" id="send">Send</button>
      <span class="spacer"></span>
      <select id="journey"><option value="">run journey…</option></select>
      <button id="runj">Play</button>
      <button id="stop">Stop</button>
      <button id="reset">New session</button>
    </div>
    <p class="err" id="err"></p>
  </section>

  <section class="cols" id="cols"></section>
</main>
<script nonce="__NONCE__">
(function () {
  var seen = "", catalogue = "";
  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) { node.className = cls; }
    if (text !== undefined && text !== null) { node.textContent = String(text); }
    return node;
  }
  function api(path, body) {
    var init = { method: body ? "POST" : "GET", headers: { "X-Pea-Client": "tri-bench" } };
    if (body instanceof FormData) { init.body = body; }          // the browser sets the boundary
    else if (body) { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(body); }
    return fetch(path, init).then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok) { throw new Error(data && data.message ? data.message : "HTTP " + r.status); }
        return data;
      });
    });
  }
  function fail(error) { document.getElementById("err").textContent = error ? String(error.message || error) : ""; }

  function meta(state) {
    var box = document.getElementById("meta");
    box.textContent = "";
    box.appendChild(el("span", null, "session " + state.session + " · skill " + state.skill_dir + " · "));
    var link = el("a", null, state.folder);
    link.href = "file://" + state.folder;
    box.appendChild(link);
    box.appendChild(el("span", null, " · " + state.timeout_s + " s per turn"));
    var notes = document.getElementById("notes");
    notes.textContent = "";
    (state.notes || []).forEach(function (note) { notes.appendChild(el("li", null, note)); });
  }

  function hostRow(state) {
    var row = document.getElementById("hostrow");
    if (row.dataset.ready) { return; }
    row.dataset.ready = "1";
    state.hosts.forEach(function (host) {
      var label = el("label");
      var box = document.createElement("input");
      box.type = "checkbox"; box.checked = host.enabled; box.dataset.host = host.id;
      box.addEventListener("change", function () {
        api("/api/hosts", { host: host.id, enabled: box.checked }).then(function () { fail(null); poll(); }, fail);
      });
      label.appendChild(box);
      label.appendChild(el("span", null, host.label));
      row.appendChild(label);
    });
  }

  function journeyOptions(state) {
    var key = JSON.stringify(state.journeys || []);
    if (key === catalogue) { return; }
    catalogue = key;
    var select = document.getElementById("journey");
    select.textContent = "";
    select.appendChild(el("option", null, "run journey…"));
    (state.journeys || []).forEach(function (entry) {
      var option = el("option", null, entry[0] + " — " + entry[1]);
      option.value = entry[0];
      select.appendChild(option);
    });
  }

  function card(entry) {
    var box = el("div", "card");
    var head = el("div", "head");
    head.appendChild(el("span", null, "turn " + entry.turn));
    if (entry.wall_s !== null && entry.wall_s !== undefined) { head.appendChild(el("span", null, entry.wall_s + " s")); }
    if (entry.usage_line) { head.appendChild(el("span", null, entry.usage_line)); }
    if (entry.score !== null && entry.score !== undefined) {
      head.appendChild(el("span", "score " + (entry.score >= 0.9 ? "high" : "low"),
                          "score " + entry.score.toFixed(2)));
    }
    if (entry.questions !== null && entry.questions !== undefined) {
      head.appendChild(el("span", null, entry.questions + " question(s)"));
    }
    box.appendChild(head);
    box.appendChild(el("div", "you", entry.user));
    if (entry.files && entry.files.length) {
      box.appendChild(el("div", "files", "files: " + entry.files.join(" · ")));
    }
    if (entry.error) { box.appendChild(el("div", "bad", entry.error)); }
    if (entry.reply) { box.appendChild(el("div", "reply", entry.reply)); }
    if (entry.failed && entry.failed.length) {
      box.appendChild(el("div", "failed", "failed: " + entry.failed.join(", ")));
    }
    return box;
  }

  function columns(state) {
    var cols = document.getElementById("cols");
    cols.textContent = "";
    state.hosts.forEach(function (host) {
      var col = el("div", "col" + (host.enabled ? "" : " off"));
      var title = el("h2");
      title.appendChild(el("span", "dot " + host.status));
      title.appendChild(el("span", null, host.label));
      col.appendChild(title);
      col.appendChild(el("p", "hint", host.cli + " · " + host.model + " · turn " + host.turn));
      col.appendChild(el("p", "hint", "session " + (host.session_id || "—")));
      col.appendChild(el("p", "hint", host.carry));
      host.cards.forEach(function (entry) { col.appendChild(card(entry)); });
      if (host.status === "running") { col.appendChild(el("p", "waiting", "waiting for " + host.cli + "…")); }
      cols.appendChild(col);
    });
  }

  function render(state) {
    meta(state);
    hostRow(state);
    journeyOptions(state);
    columns(state);
    var send = document.getElementById("send");
    var playing = state.journey && !state.journey.done;
    send.textContent = state.busy ? "running…"
      : (state.turn ? "Continue — turn " + (state.turn + 1) : "Send turn 1");
    send.disabled = !!state.busy || !!playing;
    document.getElementById("runj").disabled = !!state.busy || !!playing;
    document.getElementById("reset").disabled = !!state.busy || !!playing;
    document.getElementById("stop").disabled = !playing;
    if (playing) {
      document.getElementById("err").textContent = state.journey.label + ": turn " +
        state.journey.turn + " of " + state.journey.turns + " — playing";
    }
  }

  function poll() {
    return api("/api/state").then(function (state) {
      var key = JSON.stringify(state);
      if (key !== seen) { seen = key; render(state); }
      return state;
    }, function () { /* the server is restarting; the next tick tries again */ });
  }

  function chosen() {
    var picker = document.getElementById("files"), names = [], i;
    for (i = 0; i < (picker.files ? picker.files.length : 0); i++) { names.push(picker.files[i].name); }
    document.getElementById("chosen").textContent = names.length ? names.join(" · ") : "";
  }
  document.getElementById("files").addEventListener("change", chosen);
  document.getElementById("send").addEventListener("click", function () {
    var picker = document.getElementById("files");
    var name = document.getElementById("attname").value;
    var pasted = document.getElementById("atttext").value;
    var text = document.getElementById("msg").value, call, i;
    fail(null);
    if (picker.files && picker.files.length) {
      // With files the message goes as a form, so the bytes travel as bytes.
      var form = new FormData();
      form.append("text", text);
      form.append("attname", name);
      form.append("atttext", pasted);
      for (i = 0; i < picker.files.length; i++) { form.append("files", picker.files[i]); }
      call = api("/api/upload", form);
    } else {
      call = api("/api/send", { text: text, attachment: { name: name, text: pasted } });
    }
    call.then(function () {
      document.getElementById("msg").value = "";
      picker.value = "";
      chosen();
      poll();
    }, fail);
  });
  document.getElementById("runj").addEventListener("click", function () {
    var label = document.getElementById("journey").value;
    if (!label) { fail(new Error("choose a journey first")); return; }
    fail(null);
    api("/api/journey", { id: label }).then(poll, fail);
  });
  document.getElementById("stop").addEventListener("click", function () {
    api("/api/stop", {}).then(poll, fail);
  });
  document.getElementById("reset").addEventListener("click", function () {
    api("/api/reset", {}).then(poll, fail);
  });
  document.getElementById("msg").addEventListener("keydown", function (event) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") { document.getElementById("send").click(); }
  });
  poll();
  setInterval(poll, 1500);
})();
</script>
"""


def page(nonce):
    return PAGE.replace("__NONCE__", nonce)


# ------------------------------------------------- one upload off the wire --
# A hand parser and not ``cgi.FieldStorage``: cgi is deprecated since 3.11 and gone in
# 3.13, and a photo has to come back out of here byte for byte. Only the shape a browser
# sends for a form is understood - a boundary, a Content-Disposition per part, the bytes
# between - and a body that is not that shape is refused rather than guessed at.
def form_boundary(content_type):
    """The boundary string out of ``multipart/form-data; boundary=...``, or a refusal."""
    kind, _sep, rest = (content_type or "").partition(";")
    if kind.strip().lower() != "multipart/form-data":
        raise BenchError("that upload did not arrive as a form")
    for param in rest.split(";"):
        key, _eq, value = param.partition("=")
        if key.strip().lower() == "boundary":
            value = value.strip().strip('"')
            if value and len(value) <= 200:
                return value.encode("ascii", "ignore")
    raise BenchError("that upload has no boundary, so the bench cannot read it")


def part_disposition(head):
    """(field name, file name) out of one part's headers; the file name is None for a field."""
    name = filename = None
    for line in head.decode("utf-8", "replace").split("\r\n"):
        key, _sep, value = line.partition(":")
        if key.strip().lower() != "content-disposition":
            continue
        for param in value.split(";")[1:]:
            k, _eq, v = param.partition("=")
            k, v = k.strip().lower(), v.strip().strip('"')
            if k == "name":
                name = v
            elif k == "filename":
                filename = v
    return name, filename


def parse_multipart(body, content_type):
    """[(field name, file name or None, bytes)] for one multipart/form-data body."""
    marker = b"--" + form_boundary(content_type)
    chunks = (b"\r\n" + body).split(b"\r\n" + marker)
    if len(chunks) < 2:
        raise BenchError("that upload is not shaped like a form the bench can read")
    parts = []
    for chunk in chunks[1:]:
        if chunk[:2] == b"--":                 # the closing boundary; the rest is epilogue
            break
        if not chunk.startswith(b"\r\n"):
            raise BenchError("that upload is not shaped like a form the bench can read")
        head, sep, data = chunk[2:].partition(b"\r\n\r\n")
        if not sep or len(head) > 4096:
            raise BenchError("that upload is not shaped like a form the bench can read")
        name, filename = part_disposition(head)
        if not name:
            raise BenchError("that upload has a part with no name")
        parts.append((name, filename, data))
        if len(parts) > MAX_PARTS:
            raise BenchError("that upload has more pieces than the bench reads")
    return parts


def read_form(body, content_type):
    """(fields, files) from one upload: the typed message, and what was attached to it.

    Fields come back as text, files as ``(name the browser gave, bytes)`` in the order the
    page added them. A file part with an empty name is an empty picker and is dropped."""
    fields, files = {}, []
    for name, filename, data in parse_multipart(body, content_type):
        if filename is None:
            fields[name] = data.decode("utf-8", "replace")
        elif filename.strip():
            files.append((filename, data))
    return fields, files


# ------------------------------------------------------------------ the server --
class Handler(BaseHTTPRequestHandler):
    server_version = "tri-bench"
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass                      # no user text and no session id in an HTTP log

    def _send(self, code, body, ctype="application/json; charset=utf-8", nonce=None):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        policy = ("default-src 'none'; connect-src 'self'; base-uri 'none'; "
                  "form-action 'none'; frame-ancestors 'none'")
        if nonce:
            policy += "; script-src 'nonce-%s'; style-src 'nonce-%s'" % (nonce, nonce)
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", policy)
        self.end_headers()
        self.wfile.write(body)

    def _guard(self, api=False):
        """Loopback is not a permission: the page is the only caller this answers."""
        expected = "127.0.0.1:%d" % self.server.server_port
        if self.headers.get("Host") != expected:
            raise BenchError("this bench answers http://%s only" % expected)
        if api:
            if self.headers.get("Origin") not in (None, "http://" + expected):
                raise BenchError("cross-origin requests are not allowed")
            if self.headers.get("Sec-Fetch-Site", "") not in ("", "none", "same-origin"):
                raise BenchError("cross-origin requests are not allowed")
            if self.headers.get("X-Pea-Client") != "tri-bench":
                raise BenchError("this is the bench API, not a link to follow")

    def _body(self, cap):
        """The request body, whole, or a refusal - never a partial read taken as one."""
        if self.headers.get("Transfer-Encoding"):
            raise BenchError("chunked requests are not accepted")
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= cap:
            self.close_connection = True      # nothing drains a body this size
            raise BenchError("that request is the wrong size")
        body = self.rfile.read(length)
        if len(body) != length:
            raise BenchError("that request arrived incomplete")
        return body

    def do_GET(self):
        try:
            self._guard(self.path.startswith("/api/"))
            if self.path == "/":
                nonce = uuid.uuid4().hex
                return self._send(200, page(nonce).encode("utf-8"),
                                  "text/html; charset=utf-8", nonce=nonce)
            if self.path == "/api/state":
                return self._send(200, self.server.bench.state())
            self._send(404, {"message": "no such page"})
        except BenchError as exc:
            self._send(403, {"message": str(exc)})
        except Exception:
            self._send(500, {"message": "the bench could not answer that read"})

    def do_POST(self):
        try:
            self._guard(True)
            bench = self.server.bench
            kind = (self.headers.get("Content-Type") or "").partition(";")[0].strip().lower()
            if kind == "multipart/form-data":
                if self.path != "/api/upload":
                    raise BenchError("files go to /api/upload")
                if int(self.headers.get("Content-Length") or 0) > MAX_UPLOAD + UPLOAD_SLACK:
                    self.close_connection = True      # nothing drains a body this size
                    raise BenchError("that message carries more than the %s of files the "
                                     "bench takes at once." % human_size(MAX_UPLOAD))
                fields, files = read_form(self._body(MAX_UPLOAD + UPLOAD_SLACK),
                                          self.headers.get("Content-Type"))
                return self._send(200, {"turn": bench.send(
                    fields.get("text"),
                    {"name": fields.get("attname"), "text": fields.get("atttext")},
                    None, accept_uploads(files))})
            body = json.loads(self._body(MAX_BODY).decode("utf-8"))
            if not isinstance(body, dict):
                raise BenchError("the request must be a JSON object")
            if self.path == "/api/send":
                return self._send(200, {"turn": bench.send(body.get("text"),
                                                           body.get("attachment"),
                                                           body.get("hosts"))})
            if self.path == "/api/journey":
                bench.play_journey(body.get("id"), body.get("hosts"))
                return self._send(200, {"journey": body.get("id")})
            if self.path == "/api/stop":
                return self._send(200, {"stopping": bench.stop()})
            if self.path == "/api/reset":
                return self._send(200, {"session": bench.new_session()})
            if self.path == "/api/hosts":
                return self._send(200, {"enabled": bench.enable(body.get("host"),
                                                                body.get("enabled"))})
            self._send(404, {"message": "no such action"})
        except BenchError as exc:
            self.refuse(400, str(exc))
        except (ValueError, TypeError, KeyError) as exc:
            self.refuse(400, "the bench refused that request: %s" % exc)
        except Exception:
            self.refuse(500, "the bench could not run that; the transcript is on disk and "
                             "nothing is retried automatically")

    def refuse(self, code, message):
        """Say no and hang up: a refused POST may have a body nobody read, and a line with
        an unread upload still on it cannot be used for the next request."""
        self.close_connection = True
        self._send(code, {"message": message})


def serve(bench, port=DEFAULT_PORT):
    """A loopback server on 127.0.0.1 and nowhere else."""
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.bench = bench
    return server


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help="loopback port, default %d" % DEFAULT_PORT)
    parser.add_argument("--skill-dir", help="pin this skill folder instead of the working "
                                            "tree's skills/vet-flat")
    parser.add_argument("--claude-model", help="model for the claude CLI")
    parser.add_argument("--codex-model", help="model for the codex CLI")
    parser.add_argument("--grok-model", default=journeys.GROK_MODEL,
                        help="model for the grok CLI, default %s" % journeys.GROK_MODEL)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="seconds per host per turn, default %d" % DEFAULT_TIMEOUT)
    parser.add_argument("--root", default=PLAYGROUND,
                        help="where session folders are made; default .pea-playground/tri")
    parser.add_argument("--journeys", help="a journeys file other than evals/journeys.json")
    parser.add_argument("--no-grok-home-sync", action="store_true",
                        help="do not sync the pinned skill into ~/.grok/skills/pea-princess; "
                             "Grok then answers from whatever is installed already")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not 1024 <= args.port <= 65535:
        print("usage error: --port must be 1024..65535", file=sys.stderr)
        return 2
    os.umask(0o077)
    bench = Bench(skill_dir=args.skill_dir,
                  models={"claude": args.claude_model, "codex": args.codex_model,
                          "grok": args.grok_model},
                  timeout=args.timeout, root=args.root,
                  sync_grok_home=not args.no_grok_home_sync,
                  journeys_path=args.journeys)
    try:
        bench.start()
    except BenchError as exc:
        print("cannot start: %s" % exc, file=sys.stderr)
        return 2
    server = serve(bench, args.port)
    print("tri-bench  http://127.0.0.1:%d" % args.port)
    print("session    %s" % bench.dir)
    print("skill      %s" % bench.skill_dir)
    for note in bench.notes:
        print("note       %s" % note)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if bench.unsync_grok():
            print("note       the pinned copy was taken back out of "
                  "~/.grok/skills/pea-princess")
    return 0


if __name__ == "__main__":
    sys.exit(main())
