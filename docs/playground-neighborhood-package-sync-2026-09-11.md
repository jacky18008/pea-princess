# Public neighborhood package sync — 2026-09-11

The local test lab now uses the complete current public `pea-princess` package,
including the street/depth scanner and its modelled-noise dependency. Previously,
the running lab retained an older public ZIP while the source checkout had moved
on. Updating the controller and UI did not update the separately pinned actor
package. A later ZIP on disk had another defect: its scanner imported `noise`
inside `scan()`, but the ZIP omitted `noise.py`.

## Version evidence

| Artifact | ZIP SHA-256 prefix | Finding |
| --- | --- | --- |
| Audited conversation and previous running lab | `cc5b7886a04f` | 99 files; older scanner, without the new street/depth interface. Its instructions already routed area questions to the scanner. |
| Later on-disk ZIP, before this repair | `ce20f8885e45` | 99 files; newer scanner, missing its local `noise.py` dependency. Actual isolated invocation raised `ModuleNotFoundError` before retrieval. |
| Rebuilt and deployed public ZIP | `9c38d31caad8` | 100 files; every member matches the reviewed checkout, including the latest scanner and `noise.py`. |

Full deployed ZIP SHA-256:
`9c38d31caad8b036e3eaf49607fb6a3a3d196e65ae3fb835fbaef9fd0887afb7`.

The package was built in an isolated checkout at `5990d94`, based on `c79e463`.
The packaging fix was applied to the main checkout as `0245af5`. Verified public
artifacts were copied as one rollback-capable publication; unrelated `dist/`
contents were preserved. The new runtime is
`20260911T225150Z-de7c1921b839`, with manifest SHA-256
`27ea7dd04c9283f19f2842205469f8a8c3003a796ba000d5d97b02081f7c115b`.

The missing dependency belongs to the later ZIP. It **does not explain** why the
audited conversation, which used the older ZIP, never attempted a scan.

## What the conversation shows

The private Terra conversation contained two completed calls, one attempt each.
It used eight shell commands, with no recorded web searches or `area_scan`
invocations. There was no scanner execution failure in that conversation.
The commands mainly read instructions, attempted PDF extraction, and calculated
price/area differences. The scanner routing was present in the supplied prompt;
the model also printed relevant reference instructions through its shell tools.

The user's first-step focus was rent, bedrooms and area. Quietness remained an
active preference, but the next input only supplied documents. The absence of a
scan in these two turns is therefore insufficient to diagnose a neighborhood
research capability failure. A focused follow-up is needed to test that behavior.

Measured processed tokens were 123,232 and 102,038: 225,270 total. Recorded
instruction-reading outputs account for at least 334,722 characters. This is
evidence of repeated document loading, not a measurement of how many tokens a
future change will save. Tool count by itself does not measure research progress.

This older export lacks explicit per-call execution settings. `standard` was the
skill default and the frozen controller configured `low`; neither should be
retroactively presented as a recorded provider-confirmed per-call setting. The
updated UI records settings for new sessions and shows unknown values for older
records where appropriate.

## Repair and verification

`tools/build_dist.py` now checks static local imports before writing any release
artifact. It inspects imports inside functions, aliases, packages and local
transitive dependencies. A present local dependency omitted from the public
allowlist stops the build; it is not silently added. Existing release bytes remain
unchanged on failure. This is not a Python dependency solver: dynamic imports,
arbitrary `sys.path` changes, and wholly absent external modules are outside its
scope.

Verification completed:

- The existing offline suite: 2,543 tests, 17 skipped, passed. The eight new
  dependency tests passed separately, together with 12 existing packaging tests.
- The rebuilt archive has exactly the expected 100 members and their source
  bytes match the reviewed checkout.
- The archive was safely extracted to a temporary directory. `scan()` ran in
  isolated Python for lite, standard and deep with all source calls stubbed.
  Nested imports succeeded; every mode returned explicit missing evidence and
  no sources. This deliberately does not test source availability or facts.
- The frozen agent prompt includes the current scanner routing and permits
  execution of the shipped public scripts.
- The live catalog and refreshed browser show the new public ZIP and default
  research depth `standard`, reasoning effort `low`.
- All 24 preexisting session files retained their exact bytes across restart.

No native model or live source-retrieval experiment was run for this repair.
No new claim about answer quality, model compliance, or token savings is made.

## Next acceptance case

Use **用新版重測** to create a separate run from retained human inputs and document
snapshots; the original remains unchanged. After its initial comparison, add an
explicit neighborhood request, for example:

> 接著比較這兩間所在街道的安靜程度、主要道路、鐵路、夜間場所與附近施工。
> 請查公開資料，不找新房源；說明哪些已查到、哪些仍不能判斷。

Review the actual scanner calls, street/depth arguments, returned sources and
gaps, then the answer. A useful answer must distinguish area evidence from noise
inside the specific bedroom. Check that repeated reference reads and redundant
source queries have decreased before claiming a cost improvement. The current
package contains script-first and no-reread guidance, but prompt instructions do
not guarantee tool selection by every model.

Private exports, raw traces, failure reproduction, test logs, package smoke and
deployment receipts remain in the ignored local audit directory. They are not
included in the public ZIP or this document.
