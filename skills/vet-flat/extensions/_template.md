Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# <Name of the check, e.g. "Walk to the climbing wall">

verdict: shared   # `shared` = this add-on never changes the verdict code; `mine` = it may, and the report says so

## Purpose
One or two sentences: what you want to know about every candidate, and why it matters to you.

## Source and licence
Where the number comes from (an open data set, a public page you open yourself, your own
measurement) and under what terms. No listing sites, no review sites.

## How to get the number
Either the manual steps ("open X, search the postcode, read the figure") or a script call:
`python3 extensions/<name>.py --postcode <postcode>` printing one JSON object with
`source_url`, `retrieved_at`, `ok`, `evidence_class` and the value.

## How to read it
What is good, what is bad, what is unknown; the threshold in your own words. Say what the
number cannot tell you.

## What goes into the report
One line per candidate under **Personal add-ons**, with the value, the date and the source,
labelled `(personal add-on: <this file>)`; plus at most one question for the viewing day.
