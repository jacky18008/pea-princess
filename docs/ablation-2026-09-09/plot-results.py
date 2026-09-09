#!/usr/bin/env python3
"""Render saved descriptive results; no network or model invocation."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "ablation-results.json").read_text())
assert data["complete"]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "svg.hashsalt": "pea-princess-ablation-2026-09-09"})
labels = {"raw_full": "Direct full documents", "full": "Full context", "prose": "Automatic prose",
          "state": "State: both metadata types", "state_no_sources": "State: no source metadata",
          "state_no_updates": "State: no replacement metadata", "state_neither": "State: neither metadata type",
          "summary": "Summary only", "lexical": "Lexical retrieval", "adaptive": "Model-selected retrieval", "oracle": "Oracle documents (diagnostic)"}
fig, axes = plt.subplots(2, 2, figsize=(15, 9), gridspec_kw={"width_ratios": [1.2, 1]})
for index, experiment in enumerate(("rental", "retrieval")):
    rows = [r for r in data["arms"] if r["experiment"] == experiment]
    left, right = axes[index]
    positions = range(len(rows))
    answer = [r["answer_tokens"] for r in rows]
    generation = [r["dependency_tokens"] for r in rows]
    left.barh(positions, answer, color="#2868a9", label="Answer / selection calls")
    left.barh(positions, generation, left=answer, color="#e7a744", label="Required memory / summary generation")
    names = [labels[r["arm"]] if not (experiment == "retrieval" and r["arm"] == "full") else "Full documents + summary" for r in rows]
    left.set_yticks(list(positions), names)
    left.invert_yaxis()
    left.set_xlabel("Processed tokens per standalone arm pipeline (thousands)")
    left.xaxis.set_major_formatter(FuncFormatter(lambda value, _: "%.0fk" % (value / 1000)))
    baseline = next(r for r in rows if r["arm"] == ("full" if experiment == "rental" else "raw_full"))
    left.axvline(baseline["standalone_pipeline_tokens"], color="#555555", linestyle="--", linewidth=1)
    maximum = max(r["standalone_pipeline_tokens"] for r in rows)
    left.set_xlim(0, maximum * 1.28)
    for y, row in enumerate(rows):
        left.text(row["standalone_pipeline_tokens"] + maximum * .018, y,
                  "%+.1f%%" % row["pipeline_change_percent_vs_baseline"], va="center", fontsize=9)
    right.barh(positions, [r["finding_coverage_percent"] for r in rows], color="#54a38a", height=.62, label="Required findings (primary judge)")
    right.scatter([r["scalar_accuracy_percent"] for r in rows], list(positions), color="#273444", marker="D", s=28, label="Exact scalar checks", zorder=3)
    right.set_yticks(list(positions), [""] * len(rows))
    right.invert_yaxis()
    right.set_xlim(0, 114)
    right.set_xticks([0, 25, 50, 75, 100])
    right.set_xlabel("Coverage / accuracy (%)")
    for y, row in enumerate(rows):
        right.text(102, y, "crit: %d" % row["critical_misses"], va="center", fontsize=9,
                   color="#a52b36" if row["critical_misses"] else "#555555")
    title = "Rental: 3 cases × 2 turns × 2 repeats" if experiment == "rental" else "Retrieval: 3 cases × 2 lengths"
    left.set_title(title + " — cost", loc="left", fontweight="bold")
    right.set_title("Quality; critical omissions shown separately", loc="left", fontweight="bold")
    left.grid(axis="x", alpha=.15)
    right.grid(axis="x", alpha=.15)
    left.set_axisbelow(True)
    right.set_axisbelow(True)
for axis, anchor in ((axes[0, 0], (.185, .935)), (axes[0, 1], (.625, .935))):
    handles, legend_labels = axis.get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="upper left", bbox_to_anchor=anchor, frameon=False, fontsize=9)
fig.suptitle("Context ablations: whole-pipeline cost and observed quality", x=.03, ha="left", fontsize=17, fontweight="bold")
fig.text(.03, .014, "Shared generation is charged once per standalone pipeline; arm totals overlap. Cost panels exclude judges/calibration.\nCritical counts are rubric omissions, not necessarily wrong actions; primary labels and source reviews remain separate.\nSmall synthetic study, not statistical equivalence or billing. Exact scalar scores also include formatting mismatches.", fontsize=9, color="#555555")
fig.subplots_adjust(left=.185, right=.98, bottom=.13, top=.835, wspace=.04, hspace=.6)
(HERE / "figures").mkdir(exist_ok=True)
for suffix in ("png", "svg"):
    metadata = {"Date": "2026-09-09"} if suffix == "svg" else None
    output = HERE / "figures" / ("cost-quality." + suffix)
    fig.savefig(output, dpi=180, facecolor="white", metadata=metadata)
    if suffix == "svg":
        output.write_text("\n".join(line.rstrip() for line in output.read_text().splitlines()) + "\n")
plt.close(fig)
print(HERE / "figures/cost-quality.png")
