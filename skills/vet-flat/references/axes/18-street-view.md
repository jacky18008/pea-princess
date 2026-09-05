Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# 18 — Street-level imagery

## Purpose
The closest thing to a viewing before the viewing. A photograph taken from the pavement outside settles in one minute things that no register holds: which elevation the flat is on, what is at ground level under the windows, how much sky the building opposite takes, and whether the street is mid-build.
This is not a scored axis and it never produces a verdict of its own. It feeds axes 4, 6, 9, 12 and 14, and it is always class **C**, always dated.

## The three routes, in order
1. **Google Street View Static API, with the user's own key.** Best London coverage and the only route that gives a machine-readable capture date. Needs `GOOGLE_MAPS_KEY` in `.env` and a Google Cloud project with billing attached. The coverage/date check is free; images are billed past a free monthly allowance. Use when the user has a key, or is willing to make one (about five minutes; `scripts/streetview.py check` prints the steps).
2. **Mapillary, with the user's own free token.** Crowd-sourced, CC BY-SA 4.0, no billing account. Coverage in London is patchy and skewed to main roads and cycled routes, but it is free, it sometimes carries a *newer* date than Street View, and a second date on the same street is worth having. Use when there is no Google key, or as the cheap second opinion.
3. **The user's own screenshots.** Always available, costs nothing, works in a sandbox with no network. Ask once, with the other manual items (see `inputs.md`), for four views plus the capture date. Use when there are no keys, when the runtime has no network, or when the user would rather not enable billing.
Never take Street View images off the maps.google.com website with a fetch tool. That is scraping, the terms forbid it by name, and the API exists precisely so you do not have to.

## Commands
```
python3 scripts/streetview.py check     --lat <lat> --lng <lng>          # free: is there a pano, and how old
python3 scripts/streetview.py fetch     --lat <road lat> --lng <road lng> --out sv/ \
                                        --toward-lat <building lat> --toward-lng <building lng>
python3 scripts/streetview.py mapillary --lat <lat> --lng <lng> --radius 60
python3 scripts/streetview.py brief                                      # the checklist, to hand to the user
```
`--lat/--lng` on `fetch` is the **camera** point — the road. `--toward-*` is the **building**. The tool computes the heading from the first toward the second and then takes three more views 90° apart, so one run gives you the building, the street both ways, and whatever faces the flat across the road. Get them the wrong way round and you photograph the far pavement.

## What to read from the imagery
**1. Which facade, and what it faces.** Work out which elevation the windows are on: street, courtyard, or side return — then ask the agent in those words. Note the road class and width, lanes, bus lane, and the distance from the wall to the kerb. Note a bus stop, taxi rank, loading bay or coach drop outside the door. Note what trades at ground level under and beside the windows: pub, bar, late food, off-licence, vape shop, shisha, launderette, gym extract. Note where the refuse store opens.
**2. Ground and lower-ground exposure.** Sill height against the pavement — can someone standing outside see in? Light well or area: deep, narrow, full of leaves? Railings, grilles, frosted glass, permanently closed blinds; steps down to the door and where surface water would go.
**3. Construction.** Hoarding, scaffolding, crane, site cabin, wheel wash, gantry, trench, temporary lights — on either side of the street. A hoarding with a developer's name and a planning reference on it is free evidence: take the reference straight to `planning.py`.
**4. Vacant units.** Count the shuttered, whitewashed, to-let or boarded shop fronts on the parade. Report it as a count on a date, never as a verdict on the neighbourhood.
**5. What blocks the sky.** Count the storeys of the building opposite and of anything behind it. Take the distance from `roads.py near` → `obstruction_candidates`, and check the photograph agrees with the tagged height — OSM heights are frequently missing or wrong, and a picture is the cheapest correction there is. Then the angle: `atan(height / distance)` from the window. Over `obstruction_angle_kill_deg` from a low floor is the almost-no-light case in axis 9. Say which height you used, tagged or counted.
**6. Signs of how the block is managed.** Bins stored or standing on the pavement. Graffiti and fly-posting on the entrance, recent or painted over. The entry phone and door: taped, propped, broken, replaced. Communal windows, planting, lighting, the front path. A managing agent's board gives you a name for `company.py`.
**7. The capture date against the building's age.** Read the date **first**, before anything else in the frame. Compare it with the build year from the EPC or Land Registry. A new build whose imagery predates completion shows a hoarding or a car park — that is the camera being old, not the flat being fictional. Where several panoramas exist, step back through the older ones: the change between two dates often says more than either one.

## How to write the finding
- Evidence class **C**, always. A photograph is a third party's observation of one street on one day.
- Every sentence carries the capture date: *"as of the July 2023 imagery, the ground-floor windows sit about 1 m above the pavement behind railings."* Never write it in the present tense.
- Say which route produced it (API / Mapillary / user screenshot) and put the URL or image id in `sources[]`.
- Anything that can change within a year — hoardings, shop fronts, bins, scaffolding, a vacant unit — is a **lead to confirm on the day**, not a fact. Put it in `viewing_day_checks[]`.
- If the newest imagery is more than about three years old, say so in the finding and downgrade everything read from it to a lead.
- Imagery can replace an assumption or raise a question. It can never grant a pass, never grant "quiet", never grant "safe". Same rule as axis 14.

## What NOT to infer
- **Never anything about the people in the frame.** Not their appearance, ethnicity, nationality, age, occupation or apparent circumstances; not how many there are; not what they are doing. Faces are blurred for a reason. This is out of bounds with no exception, and it is not a housing judgement in any case.
- **Not crime.** Crime comes from `crime.py` and data.police.uk. A photograph of a street on one afternoon is evidence about nothing on this subject.
- **Not who the neighbours are**, how well off anyone is, or what "kind of area" it is. Read the fabric and the ground-floor uses, not the residents.
- **Not noise, smell or damp.** You can see a *source* — a pub, an extract, a main road, a bin store — and that is a thing to check on the day. The photograph does not tell you what it sounds like or smells like.
- **Not a parked vehicle, a van, or a shop's customers.** These are not evidence of anything.
- Do not read a single frame as a trend. One panorama is one moment; two dates are a trend.

## Privacy and storage
- Do not keep the images past the session. The Google terms forbid caching Google Maps Content, with one exception: the **panorama ID**, which may be stored indefinitely. Keep the pano id, the capture date and your written finding; delete the JPEGs when the run ends.
- If the user wants their own copy, that is the user's decision — say so plainly, and let them save the files themselves rather than the agent archiving them.
- `manifest.json` from `streetview.py fetch` redacts the API key from every URL it records, because a manifest is exactly the kind of file that gets pasted into a chat. Check it before sharing anyway.
- Never send imagery, coordinates or a key to any third-party service that was not asked for.

## Attribution when an image appears in a report
- **Google**: the returned image carries the Google wordmark — keep it visible and do not crop it. Reproducing it means following the Google Maps attribution requirements (https://developers.google.com/maps/documentation/streetview/policies). Print the capture date beside it.
- **Mapillary**: CC BY-SA 4.0. Credit the contributor shown in `creator`, show the Mapillary logo, and link back to the image page.
- **A user's own screenshot**: mark it `provenance: user_supplied` with the date they took it, and it still carries the underlying provider's attribution.

## Traps
- **The date is the whole finding.** An undated observation from imagery is worthless and slightly dangerous, because it reads as current.
- **Google's camera stands in the road, not at the window.** What the panorama sees is not what floor 6 sees. Use it for the ground plane and the facing building; use the floor plan and axis 9 for the light.
- **`ZERO_RESULTS` is a coverage gap, not a quiet street.** Private roads, gated courtyards, pedestrian estates and new developments frequently have none. Record the exact query in `not_found[]` and fall through to the next route.
- **Mapillary thumbnails are signed and expire.** Open them in the same session or ask the user to; do not save the URL and expect it to work tomorrow.
- **Four views is a facade, not a survey.** If you want more angles, that is what the viewing is for.
