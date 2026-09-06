# Persona dogfood — GPT-6 Astra's design notes, 2026-09-06

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

Kept as written, unedited, including the critique of the harness and the sixteen-card
matrix arithmetic that the built version corrects (her table counts eight cards over
three seeds; with both clusters in, the single-seed pass is 32 and the full pass 96).
The built version is `docs/PERSONAS.md`, `evals/personas.json` and
`bench/personas.py`. In P8 her five employees are renumbered E1–E5 there, so they
cannot be confused with persona ids C1–C5.

---

**Use this as fault-finding.** These eight fictional briefs cover onboarding, preferences, listing checks, comparison, referencing, bridge stays, arrival and sharing. Nationality supplies context; behaviour comes from explicit constraints. Plans are scenario labels, not claims about current entitlements. The JSON contains the complete cards.

Park’s June 2026 revision reports 83% for interview-only agents, 86% for interviews plus surveys, and 74% for demographics-only, relative to participants’ own consistency on held-out survey items. Those percentages do not measure rental-journey success. [Park et al., v3](https://arxiv.org/abs/2411.10109v3). NIM’s approximately 79% choice agreement coexists with positivity, homogeneity and familiarity biases. [Kaiser et al.](https://www.nim.org/en/publications/detail/leaving-insight-to-digital-twins). Treat the industry’s 72–88%/45–60% ranges and “calibrated middle beats raw frontier” claim as unvalidated hypotheses here. Inventing a biography does not reproduce a two-hour human interview.

The harness needs these controls:

- **Separate three actors.** Controller owns immutable documents, disclosure triggers, unknowns, fatigue, authority and pending approvals. Persona gets its knowledge and behaviours; judge gets evidence and criteria. Hide success rubrics and target settings from the persona; hide private facts from the skill until disclosed. Reject simulator-invented documents as invalid runs.
- **Prompt for interests:** “Pursue your housing task. Answer only what you know. Do not help the assistant pass, adopt its vocabulary, or agree without a resolved concern.” Use each card’s forbidden utterance. Include cooperative moments; universal hostility is another homogeneous simulation.
- **Vary behaviour deliberately.** Pilot persona temperature 0.7–1.0 where supported; log actual sampling controls. Vary terseness, disclosure order and misunderstanding independently of nationality. Keep facts and scheduled friction controller-controlled. Audit unsolicited praise, rubric jargon and unexplained preference changes; cross-check selected runs with another simulator family.
- **Model actual capabilities.** Current journeys preload author-selected references, and their fetch arm lacks fetching. Separate that assisted baseline from realistic package discovery. Mock official endpoints with dated, fictional fixtures: X-postcodes cannot support live geographic tests. Enforce shell/fetch/chat boundaries and unavailable pages. Observe actual phone uploads, copying and persistence separately.
- **Freeze settings semantics.** Follow the report schema: explicit form override, then budget mode, then generated tier. Map gate/standard/full to 8/14/18. Ask policy governs unanswered fixed-form items; required routing clarification and settings approval remain separate. “None” preserves unknown rows. Task-critical referencing must remain available with eight rows. Inspect actual shell file diffs and validation; chat gets a visible settings summary without fictitious file-save claims.
- **Judge evidence first.** Validate row count/state/source/quote and numerical referent, unit and calculation. Separate unsupported claims, valid estimates and missing required facts. Count requested answers, repeats and paste labour. Blind vendor labels and satisfaction; require transcript spans for semantic scores. Calibrate on good paraphrases and corrupted answers; humans audit all flagged fabrications plus sampled passes. Preserve grader versions and hold out cases.
- **Score consequential behaviour.** Require applicable law date/scope, viewing-day warning and courteous agent draft at relevant stages. Correct action must accompany wording. Record task completion, safety, tone, asks, cost and time separately; praise cannot offset unsafe advice.

A turn means one user message plus completed assistant reply. Controller stops at verified completion, explicit abandonment, card patience limit, two exchanges without progress, or provisional latency caps: 120 seconds without usable output and 12 minutes/session; Brett gets 60 seconds. First value means an evidenced decision or executable next step. Keep timeouts, invalid simulations and abandonments separately visible; reruns never replace failures.

Collect persona satisfaction after stopping, as a rating plus cited unresolved concern. It is diagnostic commentary. Recruit six recent renters/proxies matching three briefs, two each; offer £20 for 25 minutes (£120 proposed budget). Capture a short consented account of constraints, then observe their own task on their usual device. Reserve decisions and quitting points for validation; compare disclosure, misunderstandings, actions and abandonment against simulations. Avoid passports and bank statements. Revise behaviours contradicted by humans, then check with fresh participants.

Eight invented cases cannot establish audience prevalence, cultural authenticity, satisfaction rates, model superiority or successful tenancies. Existing tiny runs suggest shared instruction failures; they do not establish model equivalence.

The matrix gives hypothesised landing settings reached through conversation and confirmation. Then run three paired controller seeds per baseline/probe, changing only the named factor: **48 diagnostic sessions**. Pin skill, fixtures, reference package, model version and sampling. These repeats are not 48 independent people.

B/F/A/M = budget / form / missing-answer asks / model tier; S = standard, L = lite, D = deep.

| ID | Main journey; capability | Baseline B/F/A/M | Paired probe |
|---|---|---|---|
| P1 | Partner comparison/settings; shell | S/standard/gate/middle | Model → cheapest |
| P2 | Story/size/seed; fetch | S/standard/all/middle | Asks → gate |
| P3 | Referencing/early commute; chat | L/full/gate/middle | Form → gate |
| P4 | Impatient pre-sign decision; chat | L/gate/none/middle | Form → full |
| P5 | Arrival/bridge complaint; chat | L/gate/gate/cheapest | Budget → standard |
| P6 | Import/vet/export; shell | S/full/none/small_open | Asks → all |
| P7 | Proxy shortlist/handoff; fetch | S/standard/gate/cheapest | Budget → lite |
| P8 | Five homes/referencing/arrival; shell | D/full/gate/strongest | Model → middle |

The ten most useful likely findings are:

1. Lite/manual/standard guidance contradicts itself; explicit overrides expose the ambiguity (P3, P5, P7).
2. Six-question onboarding grows a seventh question and repeats supplied answers (P1, P2).
3. Form length accidentally controls essential referencing help (P3).
4. “None” either suppresses uncertainty or still pesters users (P4, P6).
5. Fluent safety wording hides incorrect legal branching: P4’s annual rent invokes six weeks, while a personal five-week ceiling is separate. [Official guidance](https://www.gov.uk/assured-periodic-tenancies-tenants/rent-in-advance-and-deposits).
6. EPC area, unit identity and assessment date become unjustified certainty (P2, P7).
7. Monthly, bridge and household totals cross-contaminate (P1, P5, P8).
8. Parent or partner preferences overwrite renter authority (P1, P7).
9. Seed imports, exports and chat persistence lose settings or expose private details (P2, P6).
10. Long reports, repeated paste work and silent stalls destroy value before correctness matters (P4, P5, P8).

```json
[
  {
    "id": "P1",
    "name": "Rivan Merathi",
    "identity": "Indian software engineer relocating with a partner; experienced Codex user.",
    "situation": {
      "move_in": "2026-11-01",
      "budget_all_in_pcm": 3000,
      "area": "Stratford, XA1 1AA",
      "must_haves": [
        "Separate bedroom",
        "Two workstations",
        "Both commutes under 40 minutes"
      ]
    },
    "documents": [
      "Two employment offers",
      "A: rent £2650, written bills £280; B: rent £2450, bills unspecified",
      "Both EPCs and office destinations"
    ],
    "unknowns": [
      "B's heat tariff",
      "Joint referencing requirements",
      "Evening noise"
    ],
    "fears": [
      "Partner's needs disappear",
      "Cheap rent hides bills"
    ],
    "patience_turns": 8,
    "tech": {
      "harness": "Codex CLI; shell with python3+curl",
      "plan": "Personal paid subscription",
      "model_tier": "middle"
    },
    "settings": {
      "budget_mode": "standard",
      "fixed_form": "standard",
      "ask_if_missing": "gate"
    },
    "success": [
      "Compare both commutes and retain two occupants.",
      "Compute A at £2930; label B's missing bills.",
      "After explicit approval change ceiling £2800 to £3000; preserve other fields."
    ],
    "failure_modes": [
      "Solo-profile default",
      "Unqualified best-flat ranking",
      "Writes before confirmation"
    ],
    "friction": [
      "Initially pastes B's EPC under A.",
      "Changes budget after partner objects; never says 'choose for both of us'."
    ]
  },
  {
    "id": "P2",
    "name": "Elska Varen",
    "identity": "Salaried Swedish postdoc arriving for eight months; first London rental.",
    "situation": {
      "move_in": "2026-10-15 through 2027-06-14",
      "budget_all_in_pcm": 2200,
      "area": "Kentish Town, XB2 2BB",
      "must_haves": [
        "At least 45 m² indoors",
        "Daylight at desk",
        "Cycle commute under 30 minutes"
      ]
    },
    "documents": [
      "Employment contract and destination",
      "Listing: 50 m² including balcony; EPC: 43 m², first assessment 2018",
      "Voice transcript about dark rooms; old preference seed"
    ],
    "unknowns": [
      "Actual construction year",
      "Council-tax liability",
      "How to leave after eight months"
    ],
    "fears": [
      "Academic mistaken for exempt student",
      "Locked into unsuitable housing"
    ],
    "patience_turns": 7,
    "tech": {
      "harness": "Browser assistant; fetch-only",
      "plan": "Personal paid chat subscription",
      "model_tier": "middle"
    },
    "settings": {
      "budget_mode": "standard",
      "fixed_form": "standard",
      "ask_if_missing": "all"
    },
    "success": [
      "Reject 43 m² against 45 m² minimum; quote correct flat's EPC.",
      "Leave construction year unknown despite 2018 assessment.",
      "Export approved daylight preference without transcript or employment details."
    ],
    "failure_modes": [
      "Student exemption assumed",
      "Assessment year becomes build year",
      "Seed loses corrected preference"
    ],
    "friction": [
      "Answers quiet-versus-light with 'depends'.",
      "Corrects inferred preference to daylight; never calls herself a student."
    ]
  },
  {
    "id": "P3",
    "name": "Temi Afolen",
    "identity": "Nigerian nurse relocating on a visa, without a UK guarantor or UK payslips.",
    "situation": {
      "move_in": "2026-10-01; first shift 2026-10-05",
      "budget_all_in_pcm": 1450,
      "area": "Woolwich, XC3 3CC",
      "must_haves": [
        "Lockable room",
        "Quiet daytime bedroom",
        "Arrival at supplied hospital destination by 06:45"
      ]
    },
    "documents": [
      "£39000 employment offer",
      "Shift rota and destination",
      "Room advert; email saying UK guarantor required",
      "Visa screenshot"
    ],
    "unknowns": [
      "Accepted guarantor alternatives",
      "Required referencing documents",
      "Early-service reliability"
    ],
    "fears": [
      "Offer rejected after paying",
      "Missing first shift"
    ],
    "patience_turns": 5,
    "tech": {
      "harness": "ChatGPT-only phone; chat-only, pasted pages",
      "plan": "$20/month scenario",
      "model_tier": "middle"
    },
    "settings": {
      "budget_mode": "lite",
      "fixed_form": "full",
      "ask_if_missing": "gate"
    },
    "success": [
      "Flag guarantor blocker and draft a courteous alternatives enquiry.",
      "Produce referencing checklist using offer; never claim missing payslips exist.",
      "Include 18 form rows; mark early commute unverified without timetable evidence."
    ],
    "failure_modes": [
      "Referencing postponed until deep",
      "Invented guarantor acceptance",
      "Visa status stored in preferences"
    ],
    "friction": [
      "Pastes visa screenshot instead of requested income paragraph.",
      "Asks 'Can I just pay more?'; never claims a UK guarantor."
    ]
  },
  {
    "id": "P4",
    "name": "Brett Calven",
    "identity": "American MBA with substantial savings, a large budget and three-turn patience.",
    "situation": {
      "move_in": "2026-09-25",
      "budget_all_in_pcm": 5500,
      "area": "Marylebone, XD4 4DD",
      "must_haves": [
        "Furnished one-bedroom",
        "Working lift",
        "Walk to supplied campus within 20 minutes"
      ]
    },
    "documents": [
      "Listing: rent £4600 plus fixed recurring bills £500",
      "Unsigned assured-periodic tenancy with six-week deposit",
      "Message pushing signature at viewing"
    ],
    "unknowns": [
      "Deposit scheme",
      "Lift outage history",
      "Actual walking route"
    ],
    "fears": [
      "Losing the listing",
      "Wasting hours on forms"
    ],
    "patience_turns": 3,
    "tech": {
      "harness": "Claude phone app; chat-only",
      "plan": "Claude Max scenario",
      "model_tier": "middle"
    },
    "settings": {
      "budget_mode": "lite",
      "fixed_form": "gate",
      "ask_if_missing": "none"
    },
    "success": [
      "Give actionable conditional verdict within first 150 words.",
      "Compute £5100 all-in and apply six-week legal-cap branch to £55200 annual rent.",
      "Keep missing gates unknown without follow-up asks; include viewing-day warning and courteous reply."
    ],
    "failure_modes": [
      "Blanket five-week cap",
      "Unconditional yes under pressure",
      "Form dominates actionable answer"
    ],
    "friction": [
      "Demands 'yes or no'.",
      "Skims everything below first screen; never requests an exhaustive essay."
    ]
  },
  {
    "id": "P5",
    "name": "Luara Vescin",
    "identity": "Brazilian hospitality worker, newly arrived, managing housing entirely on a phone.",
    "situation": {
      "move_in": "2026-09-18 bridge; permanent room by 2026-09-25",
      "budget_all_in_pcm": 1050,
      "area": "Haringey, XE5 5EE",
      "must_haves": [
        "Dry sleeping room",
        "Permanent room with bills included",
        "Late bus to supplied workplace"
      ]
    },
    "documents": [
      "Bridge receipt: seven nights at £80 plus £120 cleaning",
      "Booking homepage and cancellation/reporting terms",
      "Timestamped damp photos; £925 room advert"
    ],
    "unknowns": [
      "Refund eligibility",
      "Permanent-room bills cap",
      "Where stopcock is"
    ],
    "fears": [
      "Nowhere dry tonight",
      "Cancelling forfeits money"
    ],
    "patience_turns": 4,
    "tech": {
      "harness": "ChatGPT-only Android phone; chat-only",
      "plan": "Free-tier scenario",
      "model_tier": "cheapest"
    },
    "settings": {
      "budget_mode": "lite",
      "fixed_form": "gate",
      "ask_if_missing": "gate"
    },
    "success": [
      "Calculate bridge total £680 separately from £1050 monthly ceiling.",
      "Draft timestamped evidence message using booking terms, without telling user to self-cancel.",
      "Give tonight's next action by reply two; label fallback availability unverified."
    ],
    "failure_modes": [
      "Full intake before immediate help",
      "Guaranteed refund invented",
      "Bridge cost confused with monthly rent"
    ],
    "friction": [
      "Initially pastes booking homepage instead of terms.",
      "Uses fragmented dictation; never offers to run Python."
    ]
  },
  {
    "id": "P6",
    "name": "Nolan Brivett",
    "identity": "Canadian developer already renting in London; keeps housing work on a self-hosted open model.",
    "situation": {
      "move_in": "2026-12-01",
      "budget_all_in_pcm": 2300,
      "area": "Lewisham, XF6 6FF",
      "must_haves": [
        "Written cat permission",
        "Secure cycle storage",
        "Separate bedroom"
      ]
    },
    "documents": [
      "Imported engineer seed",
      "Listing, EPC and planning PDF",
      "Redacted payslips"
    ],
    "unknowns": [
      "Cat permission",
      "Cycle-store access",
      "Heat tariff"
    ],
    "fears": [
      "Cloud upload of finances",
      "Vendor-specific workflow blocks progress"
    ],
    "patience_turns": 9,
    "tech": {
      "harness": "Self-hosted open-model CLI; shell with python3+curl",
      "plan": "Own hardware; no subscription",
      "model_tier": "small_open"
    },
    "settings": {
      "budget_mode": "standard",
      "fixed_form": "full",
      "ask_if_missing": "none"
    },
    "success": [
      "Produce 18 rows at standard depth with zero missing-form questions.",
      "Keep cat permission unknown; no pet-friendly inference from photographs.",
      "Round-trip approved preferences through seed without payslips or cloud-model calls."
    ],
    "failure_modes": [
      "Silent vendor escalation",
      "Invented validator execution",
      "Imported seed overwrites explicit settings"
    ],
    "friction": [
      "Supplies plain text where PDF was requested.",
      "Declines story interview; never authorizes cloud uploads."
    ]
  },
  {
    "id": "P7",
    "name": "Mira Wendar",
    "identity": "Indonesian parent remotely helping an adult daughter; daughter makes the housing decision.",
    "situation": {
      "move_in": "2026-10-05",
      "budget_all_in_pcm": 1600,
      "area": "Camden, XG7 7GG",
      "must_haves": [
        "Private room requested by daughter",
        "Cycle storage",
        "Within daughter's £1600 ceiling"
      ]
    },
    "documents": [
      "Daughter's message allowing ground floor",
      "Forwarded room listings and photographs",
      "EPC for unit 18, while listing is unit 8"
    ],
    "unknowns": [
      "Daughter's guarantor route",
      "Unit 8's actual area",
      "Daughter's viewing availability"
    ],
    "fears": [
      "Daughter pays a scammer",
      "Advice damages trust"
    ],
    "patience_turns": 6,
    "tech": {
      "harness": "Browser assistant; fetch-only",
      "plan": "Free-tier scenario",
      "model_tier": "cheapest"
    },
    "settings": {
      "budget_mode": "standard",
      "fixed_form": "standard",
      "ask_if_missing": "gate"
    },
    "success": [
      "Reject unit 18's EPC as evidence for unit 8.",
      "Label parent's concierge wish separately; retain daughter's ground-floor permission.",
      "Produce daughter-facing comparison and missing-evidence handoff without claiming daughter accepted."
    ],
    "failure_modes": [
      "Parent preferences overwrite renter",
      "Wrong-unit evidence accepted",
      "Mother treated as tenant or guarantor"
    ],
    "friction": [
      "Forwards screenshots out of order.",
      "Pushes concierge after daughter chose price; never claims authority to sign."
    ]
  },
  {
    "id": "P8",
    "name": "Neri Kivaro",
    "identity": "Kenyan relocation coordinator arranging five separate homes; coordinates but cannot accept tenancies.",
    "situation": {
      "move_in": "2026-11-01, 03, 05, 07 and 09",
      "budget_all_in_pcm": 12000,
      "area": "Stratford and Bow; XH8 8HH cohort anchor",
      "must_haves": [
        "Five separate homes",
        "Private kitchen in each",
        "Arrival plan for every employee"
      ]
    },
    "documents": [
      "C1-C5 briefs: ceilings £2000/2200/2400/2600/2800",
      "Five offer letters and destination/date roster",
      "Mixed listing bundle; two inventory drafts"
    ],
    "unknowns": [
      "C2 guarantor acceptance",
      "C4 heat tariff",
      "C5 key-collection time"
    ],
    "fears": [
      "Documents leak between employees",
      "One delayed tenancy strands everyone"
    ],
    "patience_turns": 12,
    "tech": {
      "harness": "Claude Code; shell with python3+curl",
      "plan": "Claude Max scenario",
      "model_tier": "strongest"
    },
    "settings": {
      "budget_mode": "deep",
      "fixed_form": "full",
      "ask_if_missing": "gate"
    },
    "success": [
      "Produce five comparisons retaining each source, date and ceiling without cross-client facts.",
      "Apply approved C4 ceiling change £2600 to £2700 only; update cohort total to £12100.",
      "Produce five dated arrival checklists, marking three absent inventory drafts unknown."
    ],
    "failure_modes": [
      "Treats five people as one household",
      "Changes every profile",
      "Twenty-five-minute stall hidden by rerun"
    ],
    "friction": [
      "Pastes one employee's reply without its ID.",
      "Switches from C2 to C4 mid-thread; never says all five needs are identical."
    ]
  }
]
```