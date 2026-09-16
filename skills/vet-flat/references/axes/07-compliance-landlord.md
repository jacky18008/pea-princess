Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 7 — Agent and landlord compliance (the money gate)

## Purpose
Establish which legal person you would be contracting with, whether they are allowed to hold your money, and what the law entitles you to.
Nothing on this axis is optional: it is the gate that money passes through.

## What counts as evidence
- **G** — the company register (number, status, activity codes, charges, officers, filing history); the Land Registry title register naming the proprietor; redress-scheme and client-money registries; the borough's rental licensing register; enforcement and tribunal records; legislation.
- **S** — the agent's own certificate PDF, a logo on their website, a verbal assurance.
- **C** — press coverage, review sites, an industry body listing.
- **I** — a landlord type inferred from activity codes or charges.
- **U** — the entity cannot be resolved.

## Method in shell mode
1. `python3 scripts/company.py search --name "<name>"` → `profile <company number>` → `filings <company number>`.
2. `python3 scripts/company.py address-search --query "<postcode>"` — related entities at the same address.
3. `python3 scripts/redress.py cmp --agent "<agent>"` — client-money protection; `redress.py prs`, `redress.py tpo` (manual-check instructions, no arguments) — redress schemes; `redress.py rogue --name` — the London enforcement checker.
4. `python3 scripts/landregistry.py title` — the route to the title register (a paid, signed-in human step; the script tells the user what to buy).

## Method in fetch mode
The company register, the client-money registry and the enforcement checker are fetchable. One redress scheme's site blocks named AI crawler user agents outright, and another's member-lookup endpoint silently ignores its filter and returns the same recent-members list for every query — treat both as manual and never report their default output as a search result.

## Method in manual mode
Ask the user for:
1. The agent's redress-scheme membership number and their client-money certificate, obtained in writing from the agent.
2. The client-money registry entry opened to the current certificate (an old PDF on the agent's own site is the usual cause of a false "lapsed" finding).
3. The title register for a private landlord (`land_registry_title_fee_gbp` per document, signed-in card payment; never automate it).
4. The name of the legal entity on the draft tenancy agreement, and the payee name on any invoice.

## How to read the numbers
- `deposit_cap_weeks` where annual rent is below `deposit_annual_rent_threshold_gbp`, otherwise `deposit_cap_weeks_high_rent`.
- `holding_deposit_weeks` — the maximum holding deposit.
- `rent_in_advance_max_months` — the usual monthly pre-tenancy cap, after signing and before commencement, for agreements within scope; not a universal payment rule.
- `deposit_protection_days` — the deadline for the deposit to be placed in a protection scheme.
- `tenant_notice_months` — the tenant's notice period, in writing; a shorter period can be agreed in writing, so agree it before signing if a short stay is possible.
- `land_registry_title_fee_gbp`, `land_registry_document_fee_gbp`.

## Legal facts (England, as at 2026-09)
- **Renters' Rights Act 2025 (c. 26)**, in force from **2026-05-01** for assured tenancies that are not social housing, by SI 2026/421. In-scope assured tenancies are periodic. Identify the agreement before applying this rule: halls/PBSA, lodgers, licences and social housing can differ. Cite from `sources.yaml`.
- Deposit caps and the holding-deposit cap come from the **Tenant Fees Act 2019**; the deposit-protection deadline from the **Housing Act 2004**.
- For an assured periodic tenancy there is no fixed minimum term; do not apply this to excluded agreements.
- **Rent timing matters.** For in-scope agreements signed from 2026-05-01, rent cannot be requested or accepted before both parties sign. Between signing and commencement, the usual cap is one month for monthly rent or 28 days for weekly rent. Once started, rent cannot be required before its agreed due date; voluntary early payments differ. Check transitional, social/supported-housing and council-arranged exceptions in `govuk_rent_in_advance_guidance`. Deposits are separate.
- **Student halls are a separate branch.** University halls and qualifying code-member private PBSA usually use common law tenancies or licences; confirm status using `govuk_student_tenancies`, not the advert's label alone.
- **Exclusive possession decides tenancy versus licence**, not the title on the document.
- More than `short_let_nights_per_calendar_year` nights of short letting in Greater London needs planning permission (Deregulation Act 2015 s.44 and the provision it inserts).
- A tenancy transfers with the property on a sale; the tenant keeps the tenancy, and the buyer never assessed the tenant.

## Traps and lessons
- **Resolve the entity by number, not by name.** Dissolved same-name shells and near-identical trading names are common; match the company number.
- **Four registers do four different jobs and cannot substitute for each other:** the portal advert (marketing), the Land Registry (ownership), the energy register (energy), and the borough's rental licensing register (mandatory, additional or selective licensing).
- **Evidence ladder for membership:** an entry in the independent registry beats the agent's own certificate, which beats a logo on their website. Open the registry entry to read the current expiry. A number that does not match is a document to resolve, not a fraud finding.
- **Payee name in three sources.** A trading name is not a legal entity ("X Ltd trading as Y"). A third entity appearing on the invoice or as the payee is a red flag.
- **Conduct forensics on the entity:** no liquidation; no judgments in the property tribunal or the case-law records; no director disqualification; no charge over the trading assets; no phoenix pattern; no recent change of name; check gazette notices; and check whether filings stayed on time through quiet periods. Archived snapshots of the company's own site show whether an operator is an experienced restart or genuinely new.
- **A deposit above the cap is usually a stale price, not an intention.** The cap runs on the current rent, and an advertised deposit is often five weeks of a previous, higher rent left un-updated. Ask for the correction, treat it as leverage, and do not present it as an accusation.
- **Off-platform pressure is a retreat signal.** A phone number spelled out in words to defeat a filter, a push to a messaging app, a request for a bank transfer outside the platform: keep money and messages where they are logged.
- **Absence of an enforcement record only means no borough reported one.** It is not a clean bill of health.
- **Universal armour, applied identically to every landlord and agent, with no exceptions based on who they are:**
  1. a custodial deposit scheme, so the landlord never holds the money;
  2. an independent, third-party check-in inventory, with photographs;
  3. everything in writing, in the language of the tenancy;
  4. a red flag means walk away.
  Amateur landlords of every background dispute deposits at similar rates; the armour is what protects you, and it is worn for everyone.
- **Guarantor route.** Ask early, before spending anything on viewings: which guarantor arrangements does the landlord accept, and is a commercial guarantor product acceptable? Route this through `profile.yaml`; the only structural blocker is "an individual guarantor in this country, with no commercial alternative accepted".
- **Ask the money-gate questions before any money moves:** which deposit scheme, in which mode; the client-money certificate in writing; and who the payee is.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 7`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].hard_filters[]` — one row for the guarantor route from the profile.
- `candidates[].landmines[]` with code **L12** (who owns it and what they will demand: rent in advance beyond the legal limit, an oversized deposit, a guarantor requirement, a newly formed company with no history).
- `candidates[].killer_questions[]` — the money-gate question usually belongs here.
- `sources[]` — every registry entry with its `id`, `retrieved_at`, `evidence_class` and, where relevant, the membership or company number in `note`.
Numbers to record: deposit weeks requested against the cap, months of rent in advance, deposit protection deadline in days, company number, certificate expiry date.

## Working with agents and landlords
Everything in this axis is verification, not suspicion. Agents and landlords are the other half of every tenancy and the people who will hand over the keys; most are trying to do a decent job under pressure. Ask for documents as a matter of routine ("the same for every flat I look at"), thank them for what they send, and treat a missing document as a question to ask, not a verdict. The skill is a filter that gets you to the right viewings; the viewing, and the conversation there, decides.

