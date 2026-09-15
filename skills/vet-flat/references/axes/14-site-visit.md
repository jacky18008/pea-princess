Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 14 — The site visit

## Purpose
Fold what the user saw, heard and smelled at the property into the report without letting a single visit overturn evidence it cannot reach.
A visit is a sample of one moment. It is extremely good at some things and worthless at others; this file separates the two.

## The three-column adoption table
Every observation is recorded as one row, and all three columns must be filled in.

| What was observed | How this round adopts it | What it cannot be used to claim |
|---|---|---|
| The user's own words, with the time, date and exact standing position. | The specific change: an assumption replaced, a concern lowered, a question added. | The claims this observation does not support, spelled out. |

## The four boundaries (declare all four, every time)
1. **Time of day** — an afternoon visit says nothing about the evening.
2. **Day type** — a weekend or public holiday says nothing about a weekday.
3. **Scope** — a street segment is not the building, and the building is not the flat.
4. **Subject** — the block is not this unit, and this unit is not this unit's window elevation.
An observation missing any of the four is recorded but not adopted.

## The four allowed effects
A visit may:
1. **Replace an assumption** with an observation (for example, "orientation unknown" becomes "compass reading taken at the living-room window").
2. **Lower a concern** that the desk research raised.
3. **Trigger a withdrawal** from a high position, if what was seen is bad enough — without inventing a precise new rank to replace it.
4. Nothing else.
A visit may **never upgrade anything to a pass**. It cannot grant "quiet", cannot grant "safe", cannot turn CONDITIONAL into PASS, and cannot release a hold. Those need evidence that a visit does not produce.

## Observation → scenario × flip-condition matrix
Expand each sensory observation into three or four scenarios, each with the condition that would flip it. For example, a strong cooking smell in the corridor becomes:
a neighbour cooking once (flips if absent on a second visit at a different hour) · a restaurant extract in the shared riser (flips if the plan shows no commercial unit below) · a shared ventilation path between flats (flips if the system is confirmed as flat-by-flat) · an extract fault under repair (flips on a maintenance record).
Never collapse the matrix to whichever scenario is most convenient.

## Conditional positives keep their condition
Record the whole sentence, condition included: "as long as there are no drunks and no event traffic, it is a quiet, comfortable little block." The condition is the finding. Quoting only the first half turns an observation into a conclusion it never was.

## Boundaries in practice
- **A public-holiday visit proves nothing about weekdays.** No activity on a building site that day does not tell you why it was idle, and says nothing about a Tuesday morning.
- **A phone decibel app is a relative comparison only.** It is not a calibrated measurement and not a test of sound insulation. Use it to compare two rooms in the same session, never to assert a level.
- **One visit is one sample.** Two visits at different hours are worth far more than one long one.

## Ten things only a visit can measure
1. The smell test: the corridor, the lift, the lobby, and the bin store — separately.
2. The lift's statutory inspection record: photograph it.
3. Three minutes with the window open and three with it shut, in the same room, at the same time.
4. Whether the parcel room accepts couriers other than the national postal service — ask, do not assume.
5. The walk from the station to the door after dark, on the route actually used.
6. Phone signal in the bedroom, on the user's own network.
7. How dark the bedroom actually gets: blinds down, curtains shut, mid-afternoon.
8. What is inside the utility cupboard: the meter, the heat interface unit, the ventilation unit, the stopcock.
9. A compass reading at each window, plus a photograph of any site works visible from it.
10. Whether the one named reason to go out (axis 12) is genuinely there and genuinely open.

## Before the visit: street imagery
Read the street from the pavement before you stand on it — see `18-street-view.md`. It settles which elevation the flat is on, what trades at ground level under the windows, how exposed a ground or lower-ground window is, whether the street is mid-build, and how many storeys the building opposite has. Everything it produces is class C and carries a capture date that is usually years old, so each item comes to the visit as a question in `viewing_day_checks[]`, never as an answer. It cannot replace the visit and it never grants a pass.

## Rules for the visit itself
- **Never sign on the viewing day.** A holding payment buys a night to sleep on it and a morning to check the scoresheet.
- Get in writing, before leaving home: the tariff or bills position, the deposit scheme and amount, the guarantor position, the appliance list, and the availability date.
- At most three flats in one area in one day; more than that and the observations blur together.
- Book any celebratory meal for after the viewings, not between them.

## The first 30 minutes after arriving (a short let or the real tenancy)
Before unpacking, in this order, and say so in the reply when someone has just arrived:
1. Photograph or film every room, existing damage included, with a timestamp and something for scale; then copy the evidence off the phone (cloud, email to yourself), today.
2. Smell the corridor, the bin store and the unit: musty or drain smells are the damp and the drainage the photos do not show.
3. Run the hot tap and the shower for a minute: hot water and pressure.
4. Check the internet is a fixed line (a router in the flat, not a dongle) and run one speed test.
5. Find the meter cupboard, the stopcock and the washing machine; note the meter readings.
6. That night, listen at the bedroom window with it open, then closed.
7. Ask in writing, the same day, the latest date the stay can be extended to.
Two strong signs of damp (smell plus visible mould, condensation inside the glass, a wet skirting) mean do not sleep in that room and message the host inside the platform before anything else.

## What goes into the report
Fields are from `references/report-schema.json`. A visit writes into an existing report; it does not create a candidate.
- `candidates[].viewing_day_checks[]` — each of the ten items, answered or explicitly recorded as not answered.
- `candidates[].axes[].finding` — the observation, with its four boundaries in the same sentence, and its evidence class. An observation is class C at best, never G.
- `candidates[].axes[].unknowns[]` — anything the visit was expected to settle and did not.
- `candidates[].landmines[]` — a defect the visit found, under its code, marked `reversible` where it is.
- `candidates[].photos_vs_reality_notes` — the gap between the listing photographs and the room.
- `candidates[].provenance_notes` — the date, time of day, day type and exact standing position, plus the standing rule that a visit may replace an assumption, lower a concern or trigger a withdrawal, and may never raise a verdict to PASS or release a hold.
- `candidates[].verdict.conditions[]` — a condition the visit satisfied may be struck; a condition may not be struck merely because nothing bad happened during one visit.

## Ground and lower-ground floors: the damp check (a caution, not a veto)
Many street-level and below-street flats are good homes. They fail in one specific way, damp, and it is invisible in photographs and in two-night reviews. Check, in this order, and photograph with a pen in frame for scale:
1. **Nose at the door.** Musty, earthy or "old carpet" smell on entry, before anything else.
2. **Wall corners and skirting.** Bubbling or flaking paint, dark spots, tide marks, salt bloom on plaster.
3. **Behind radiators and under windows.** Black mould, brown water staining, rust runs from pipes.
4. **Floorboards.** Blackened joints, edges lifting, a white haze on wood, a soft step: wood that has been wet.
5. **Windows.** Condensation on the inside in the morning, closed trickle vents, no extractor in bathroom or kitchen.
6. **Outside.** Where the external ground sits against the wall, blocked gullies, a light well full of leaves.
7. **Ask, politely:** when was the flat last damp-proofed or redecorated, and is there an extractor that runs on a humidistat. A landlord who answers with dates is a landlord who maintains.
What it means for the verdict: strong signs on two or more items = walk away from that flat; one weak sign = ask and re-view after rain. Not seen = say "not seen", not "no damp".

## Tone on the day
The agent or landlord showing you round is the person who will get you the keys. Ask everything on the list, write the answers down, and stay courteous; a defect you found is information for both sides, not an accusation.

