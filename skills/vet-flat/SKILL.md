---
name: pea-princess
description: "Checks London rental listings using official and open UK data: identity, size, condition, surroundings, management, paperwork, price, light, total monthly cost and commute. Explains what is known, estimated or missing, then gives a plain-language recommendation. Use for a listing, a comparison or finding candidates around a destination; whenever someone asks to roast (尻洗) a flat; and when someone is moving to London to rent and has no idea where to start (倫敦租房、找房、租屋、想找房子從哪開始)."
license: CC-BY-4.0
metadata:
  runtime: Best with a shell and internet access (python3 + curl). Works in fetch-only or chat-only runtimes in reduced modes; the skill tells the user exactly what to paste.
  author: "Hsien Hao (Jacky) Chen"
  source: "https://github.com/jacky18008/pea-princess"
  version: "1.0.0-draft"
  brand: "Pea Princess / 豌豆公主"
---
# Pea Princess — London flat vetting

## Start
1. **The person's instruction outranks every default in this skill.** Record changes; read `references/rules.md` once.
2. Use supplied facts (`scripts/listing_fields.py`). Never open listing links or suggest fetching them. Use shipped open-register scripts.
3. Resume `.pea-state` (`references/session-harness.md`) or `profile.yaml`. Advance replies. Ask at most **three essential questions** with native choices if available.
4. **Route by intent** — choose one most specific row; do not stack rows, reread context, list folders or open `sources.yaml`:

| The user… | Read |
|---|---|
| how to start or what this does | `references/onboarding.md` |
| compares supplied listings and asks about their commute or surroundings | `references/comparison-research.md` |
| compares advertised fields | `references/inputs.md`; use supplied pages, compare only requested fields |
| ranks candidates, saves a comparison/TODO or records a viewing hold | `references/boundary-turn.md` |
| full flat assessment | `references/axes/README.md`, then relevant linked axes |
| candidates by area or commute | `references/axes/00-area-sweep.md` (`scripts/sweep.py`) |
| street noise, safety or works | `references/street-research.md`; run the scan in this thread, reuse saved results on follow-up |
| shortlist roast (尻洗) or comparison | `references/axes/13-adversarial-review.md`, then the report contract |
| signing, bridge stay or referencing | `references/axes/15`–`17` |
| before or after a viewing | `references/axes/14-site-visit.md`, `18` |
| depth, cost or model | `references/budget-modes.md` |
| changes requirements, resumes, needs goals/TODOs | `references/session-harness.md`, `references/how-to-use.md` |
| shares a seed or past-home stories | `references/sharing.md` (`scripts/seed.py`) |
| wants a personal check (add-on) | `extensions/README.md` |
| halls vs private flats, or typical rent | `references/student-housing.md` |
| needs a calculation | `references/arithmetic.md` (`scripts/calc.py`) |
| the report itself | `references/report-contract.md`, `report-schema.json` |
| wants the requirements as a page | `references/requirements-contract.md` (`scripts/panel.py`) |
| a script failed, or doubts the install | `scripts/doctor.py` |

Investigate discounts. Roast listings, never people. Never invent numbers. Each tool call re-sends context.

## Output
Before replying, run `scripts/reply_check.py` using `references/conversation-quality.md`. Saved comparison, sources and next steps need `save_gate.py --scope comparison-full` (`references/comparison-fidelity.md`); `comparison` checks export only. Reply in the person's language. Say “total monthly cost” / “每月總花費（房租加帳單）”; hide internal labels and paths. Give legal/payment advice when affected; explain verdict codes.
