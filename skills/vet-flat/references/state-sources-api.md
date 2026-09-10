Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# State sources: documents, facts and outputs

Read before `document.add`, `fact.record` or `output.record`. Set `PEA_SKILL` and `PEA_PROJECT` as in [state-api.md](state-api.md). Run this example once in an empty synthetic project; in existing work, read the complete context and reuse current IDs/revision.

Event fields are flat: `document.add` takes top-level `path`, `line_ranges` and `provenance`, never a nested `document` object. The path names an existing project file; the store creates its snapshot metadata. `fact.record` cites document IDs in `source_ids` and an exact source quote in `provenance`.

```python
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["PEA_SKILL"]) / "scripts"))
from session_state import SessionStore

project = Path(os.environ["PEA_PROJECT"])
store = SessionStore(project)
current = store.init("source-demo")

def apply(event):
    global current
    current = store.apply(event, expected_revision=current["revision"])

quote = "Estimated monthly bills: GBP 230; this is not a cap."
(project / "source.txt").write_text(quote + "\n", encoding="utf-8")
source = {"actor": "external", "source_id": "quote-demo", "quote": quote}
apply({"op": "document.add", "id": "quote-demo", "path": "source.txt",
       "line_ranges": [[1, 1]], "provenance": source})
apply({"op": "fact.record", "id": "bills-demo", "critical": True,
       "value": {"amount": 230, "unit": "GBP/month", "qualifier": "estimate, not a cap"},
       "source_ids": ["quote-demo"], "provenance": source})

apply({"op": "task.add", "id": "compare-demo", "title": "Verify the comparison",
       "acceptance": ["Check the saved quote and preserve its estimate qualifier."]})
draft = "Bills are estimated at GBP 230/month; verify the final quote."
(project / "comparison.md").write_text(draft + "\n", encoding="utf-8")
apply({"op": "document.add", "id": "comparison-doc", "path": "comparison.md",
       "line_ranges": [[1, 1]],
       "provenance": {"actor": "assistant", "source_id": "local-draft", "quote": draft}})
apply({"op": "output.record", "id": "comparison-output", "task_id": "compare-demo",
       "document_id": "comparison-doc", "decision_ids": [],
       "based_on_revision": current["revision"]})
packet = store.context(max_chars=32000)
print(json.dumps(packet, ensure_ascii=False, indent=2))
```

Read the entire final packet. The store computes `source_verified` and `verification_kind`; never supply them. A matching saved quote proves retention, not factual truth or user authority. Keep external claims and estimate qualifiers. For a replacement source, register a new document ID with `supersedes: "old-id"`; the old snapshot remains retrievable.

Use `output.record`, not `output.attach`: link a known task to a snapshotted output document. `decision_ids` refers to existing current decisions when applicable; an empty list does not validate a verdict. Registration leaves the task pending. After checking acceptance, `task.complete` needs `id`, current fact/document `evidence_ids` and `based_on_revision` from the latest state.
