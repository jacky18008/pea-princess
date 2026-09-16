Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Finding the paragraph that answers a question (`scripts/find.py`)

## When to use it
- The user pasted a document bigger than about 5 KB: a tenancy agreement, an operator's terms, a planning officer's report, a saved review page.
- The question is not one of the eighteen fixed ones. `scripts/scan.py` already covers those, because their regexes are written down. Everything else — the user's own `my_questions`, "any move-out reviews about damp?", "how far is the approved building?" — has nothing until you ask this.
- A review page with hundreds of reviews, where the three that matter are on page four.

Do not use it on a page you can read in one go. It ranks; it does not summarise.

## The three commands
```
python3 scripts/find.py pasted/ --ask "break clause"
python3 scripts/find.py pasted/ --ask "潮濕 發霉 move-out" --top 8
python3 scripts/find.py pasted/ --fixed F1,F12
```
Ask in English or Chinese; the question is expanded through `references/find-synonyms.yaml`, so "break clause" finds a clause headed **Early termination** and 押金 finds an English deposit clause. A synonym weighs 0.6 against 1.0 for the words the user typed, so it can add a hit but never outranks a literal match on equal evidence. `--fixed` runs the same `look_for` regexes `scan.py` uses and ranks their hits in the same output shape.

Useful flags: `--top N` (default 5), `--context N` paragraphs either side (default 1), `--all` for every paragraph that scored at all, `--json` for another script, `--min-score X`, `--selftest`.

Exit codes: 0 hits, 1 nothing found, 2 wrong arguments. The footer on stderr says how many units, files and milliseconds.

## What a thick view is, and why it is here
Each hit prints the **whole paragraph**, plus its neighbours, up to about 1,000 characters — not a snippet of the matching line. That is deliberate, and it is a **hypothesis under test in this repo, not a proven gain**: the pattern was seen elsewhere, on another project, where a model given the best paragraph with a little context chose well, while the same model given thin snippets did worse than not searching at all. The same work suggested that an interface with many rules hurts weak models and leaves strong ones unchanged, which is why this tool has one command shape and no modes.


## grep still works
Nothing in this skill is findable only through `find.py`. `grep -n "deposit" pasted/*.txt` finds the same lines, and if the script is missing, broken, or the shell has no Python, grep is the fallback and it is a complete one. What `find.py` adds is ranking and the surrounding paragraph. Say that plainly to the user when you use it: "I searched the pasted document; here are the five paragraphs that best match, in the order the ranker put them."

## The honesty line
**A hit is a sentence to READ, never an answer.** The ranker does not understand the document; it counts words. Two hits can say opposite things, the top hit can be the wrong clause, and a document that never answers the question still produces five hits.

So: read the paragraph, then quote it. In a report, the sentence goes in the fixed form as `found` with the quote and the source; if what you read does not actually answer the question, the state is `unknown` or `asked`, never a paraphrase of the best-ranked paragraph. Never write "the contract says X" on the strength of a rank alone.
