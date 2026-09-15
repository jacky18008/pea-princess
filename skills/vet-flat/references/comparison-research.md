Part of Pea Princess by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Compare supplied homes with open-data research

Use this one route when a person has supplied two or more listing extracts and
asks you to compare transport or the surrounding streets. It replaces the
overlapping inputs, street, commute and full-flat routes for **this turn**.
The person's scope controls the work: do not open commercial listing links,
look for new homes, contact an agent or arrange a viewing unless separately
requested. A listing extract is a reported claim, not an independently verified
rent, availability, area or floor plan.

1. State in one useful sentence which difference you are checking and why it
   matters. Compare the supplied rents, beds and areas immediately. Keep
   “quiet would be nice” as a preference, and “about 45 minutes, can discuss”
   as a negotiable target. Neither is a hard rejection or permission to book.
2. For a known street and full postcode, run
   `python3 <skill>/scripts/area_scan.py --postcode "<postcode>" --street "<street>"`.
   An outward code plus a mapped street is supported, but the resulting point
   is a **street midpoint**, not the unknown home. Run once per distinct street
   and use saved results on later turns. If the named street lookup fails, a
   full-postcode-only scan may give a weaker sample; disclose the changed point
   and never label it an exact-home result. Inspect the returned `scan_status`,
   coverage and per-source failures. Road/rail Lden and Lnight are **outdoor
   models**; different maps or points cannot establish bedroom quietness.
3. For the person's stated destination and arrival time, run
   `python3 <skill>/scripts/commute.py journey --from "<postcode or supported street point>" --to "<destination>" --arrive "<HH:MM>" --date next-weekday --plans all,rail,bus`.
   If TfL replies with HTTP 300, use the relevant exact stop ID from its
   `toLocationDisambiguation` response as `--to` and run the same query once.
   Distinguish a rail station from a bus station with a similar name; ask the
   person if the destination itself is unclear. Do not search the web for an
   unrelated postcode or substitute arbitrary coordinates. State origin and
   endpoint, date/time, route estimate, missing waits and any door buffer.
   Save the JSON receipt for each candidate. Before ranking on the commute or
   sending a draft, run the offline source audit with the person's **named**
   endpoint (a stop ID alone does not prove where each returned route ends):
   `python3 <skill>/scripts/commute_compare.py --candidate A=/path/to/a.json --candidate B=/path/to/b.json --target-endpoint "London Bridge Rail Station" --origin A="postcode point" --origin B="street midpoint" --draft /path/to/draft.txt`.
   Compare every successful target-endpoint option, including returned
   alternatives, on the same destination, date, arrival time and door buffer.
   Read the audit's `plans` rows even when its status is `review_required`:
   routes to another station remain visible, and a timed-out mode is unknown,
   not evidence that no route exists. Correct `correction_required` findings;
   inspect `review_required` findings and source receipts yourself. In
   particular, a shorter all-mode journey to an Underground station must not
   erase a rail journey to the requested Rail station or justify a blanket
   “only A has buffer / B almost misses 9:00” claim. Preserve each origin's
   precision in the final comparison. If there is no shell or the checker did
   not run, compare the saved plan rows manually and say machine checking was
   unavailable. A third-party host cannot guarantee that this helper executes
   before its model sends a reply; a host-owned acceptance harness can run it
   before accepting that reply. Literal draft cues are narrow, so a clean
   checker result still needs human review of the actual claim and source.
4. Explain the tradeoff in ordinary language. Keep reported advert facts,
   public-data estimates and unknown property-specific facts separate. Ask at
   most one question that would change which home to investigate next; continue
   research that does not depend on the answer. “Can consider a viewing” is not
   “ready to book”; only the person can give the latter instruction.

Use the scripts' `--help` for command syntax. Read implementation source only
when an actual command error requires debugging; reading whole modules is not
part of flat research. If the person later asks to **save** the comparison or
changes a condition, use `references/boundary-turn.md` for that turn and require
its `save_gate.py` receipt before saying the comparison and TODOs were saved.
Before the final reply use the SKILL's conversation-quality and reply checker.
