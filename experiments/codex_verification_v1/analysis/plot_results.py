#!/usr/bin/env python3
"""Render figures only from the completed, audited 200-task development batch.

No model calls, synthetic measurements, confidence-interval invention, or writes to
the experiment inputs. P0 is charged once; other resource bars are review tasks only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches, ticker

ROOT = Path(__file__).resolve().parents[1]
PROCS = ("P0", "P1", "P3", "P7", "P8")
REVIEWS = PROCS[1:]
COLORS = {"P0": "#263E58", "P1": "#68879B", "P3": "#22848A", "P7": "#C56C42", "P8": "#927AAB"}
LABELS = {"P0": "Initial decision", "P1": "Free re-check", "P3": "Source verification", "P7": "+ Rule conditions", "P8": "+ Generic re-check"}
SUBTITLE = "Synthetic computational pilot  |  4 case families"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def close(a: float, b: float) -> bool:
    return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-12)


def load_completed_data() -> tuple[dict, list[dict], dict]:
    """Fail closed before creating any figure if input is absent/incomplete/inconsistent."""
    base = ROOT / "analysis" / "dev"
    paths = [base / "summary.json", base / "scored_runs.csv", base / "integrity_audit.json"]
    for p in paths:
        require(p.is_file(), f"Required completed-data artifact is missing: {p}")
    summary = json.loads(paths[0].read_text())
    rows = list(csv.DictReader(paths[1].open(encoding="utf-8", newline="")))
    audit = json.loads(paths[2].read_text())
    require(summary.get("phase") == "dev", "Only the development phase is accepted")
    require(summary.get("planned_tasks") == 200, "Expected exactly 200 planned tasks")
    require(summary.get("complete_tasks") == 200, "The 200-task batch is not fully completed")
    require(summary.get("planned_groups") == 40 and summary.get("complete_groups") == 40,
            "Expected 40 fully completed shared-first groups")
    require(summary.get("passed_integrity") is True, "Summary integrity gate did not pass")
    require(audit.get("phase") == "dev", "Audit belongs to another phase")
    for k in ("record_errors", "unusual_item_types", "duplicate_session_ids"):
        require(k in audit and not audit[k], f"Audit issue in {k}")
    require(len(rows) == 200, "Scored CSV must contain exactly 200 rows")
    require(all(r.get("status") == "complete" for r in rows), "Scored CSV has incomplete tasks")
    require(all(r.get("correct") in ("0", "1") for r in rows), "Invalid binary correctness")
    require(all(r.get("procedure") in PROCS for r in rows), "Unexpected procedure")
    require(Counter(r["procedure"] for r in rows) == Counter({p: 40 for p in PROCS}),
            "Expected 40 tasks per procedure")
    require(len({(r["group_id"], r["procedure"]) for r in rows}) == 200, "Duplicate group/procedure rows")
    families = sorted({r["family_id"] for r in rows})
    require(len(families) == 4, "Expected four case families")
    require(Counter(r["family_id"] for r in rows) == Counter({f: 50 for f in families}),
            "Expected 50 tasks per family")
    groups: dict[str, dict] = defaultdict(dict)
    for r in rows:
        groups[r["group_id"]][r["procedure"]] = r
    require(len(groups) == 40 and all(set(g) == set(PROCS) for g in groups.values()),
            "The paired group matrix is incomplete")
    for gid, g in groups.items():
        first_hashes = {g[p].get("first_sha256") for p in REVIEWS}
        require(len(first_hashes) == 1 and bool(next(iter(first_hashes))),
                f"Reviews do not share a first-response hash: {gid}")
        require(len({(r["item_id"], r["family_id"], r["state"], r["advice"], r["repeat"]) for r in g.values()}) == 1,
                f"Inconsistent group identity: {gid}")
    wrong = [g for g in groups.values() if g["P0"]["state"] != "missing" and g["P0"]["correct"] == "0"]
    right = [g for g in groups.values() if g["P0"]["state"] != "missing" and g["P0"]["correct"] == "1"]
    for p in PROCS:
        s = summary["procedures"][p]
        rr = [r for r in rows if r["procedure"] == p]
        correct = sum(int(r["correct"]) for r in rr)
        require(s["planned"] == len(rr) == s["complete"] == 40, f"Summary sample count mismatch: {p}")
        require(s["correct"] == correct and close(s["accuracy"], correct / 40), f"Summary accuracy mismatch: {p}")
        require(s["natural_first_errors"] == len(wrong), f"First-error count mismatch: {p}")
        require(s["first_correct_present"] == len(right), f"First-correct count mismatch: {p}")
        if p != "P0":
            repaired = sum(int(g[p]["correct"]) for g in wrong)
            damaged = sum(1 - int(g[p]["correct"]) for g in right)
            require(s["repaired"] == repaired and s["damaged"] == damaged, f"Transition count mismatch: {p}")
            require((s["repair_rate"] is None if not wrong else close(s["repair_rate"], repaired / len(wrong))),
                    f"Repair rate / NA mismatch: {p}")
            require((s["damage_rate"] is None if not right else close(s["damage_rate"], damaged / len(right))),
                    f"Damage rate / NA mismatch: {p}")
        known = [r for r in rr if r.get("input_tokens", "") != "" and r.get("output_tokens", "") != ""]
        require(s["usage_known_tasks"] == len(known), f"Usage availability mismatch: {p}")
        for field in ("input_tokens", "output_tokens"):
            total = sum(int(r[field]) for r in known)
            require(total == s[field], f"Token sum mismatch: {p}/{field}")
    return summary, rows, {str(p.relative_to(ROOT)): sha256(p) for p in paths}


def setup_style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 12,
        "axes.titleweight": "semibold", "axes.labelsize": 10, "xtick.labelsize": 10,
        "ytick.labelsize": 9, "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#C5CCD2", "axes.labelcolor": "#24323D", "text.color": "#24323D",
        "xtick.color": "#425463", "ytick.color": "#425463", "grid.color": "#E4E9ED",
        "grid.linewidth": 0.7, "axes.axisbelow": True, "svg.fonttype": "none", "pdf.fonttype": 42,
        "figure.facecolor": "white", "savefig.facecolor": "white",
    })


def title(fig, text: str, subtitle: str = SUBTITLE) -> None:
    fig.text(0.045, 0.955, text, fontsize=18, fontweight="bold", va="top")
    fig.text(0.045, 0.905, subtitle, fontsize=10.5, color="#596B78", va="top")


def footer(fig, text: str) -> None:
    fig.text(0.045, 0.035, text, fontsize=9, color="#596B78", va="bottom", linespacing=1.4)


def box(ax, x, y, w, h, headline, detail, color, *, fill="#F5F8FA") -> None:
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.018",
                                 linewidth=1.3, edgecolor=color, facecolor=fill, zorder=3)
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h * .68, headline, ha="center", va="center", fontsize=12,
            fontweight="bold", color=color, zorder=4)
    ax.text(x + w / 2, y + h * .30, detail, ha="center", va="center", fontsize=9.5,
            linespacing=1.5, zorder=4)


def arrow(ax, start, end, *, color="#8B9AA6") -> None:
    ax.annotate("", xy=end, xytext=start,
                arrowprops={"arrowstyle": "-|>", "color": color, "lw": 1.25,
                            "shrinkA": 3, "shrinkB": 5, "mutation_scale": 12}, zorder=2)


def design_figure(summary: dict):
    fig = plt.figure(figsize=(14, 6.8))
    title(fig, "One first answer, four independent reviews")
    ax = fig.add_axes([.04, .17, .92, .67]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    box(ax, .018, .37, .19, .27, "Fictional dossier", "4 families × 5 states\n× 2 advice versions", "#445B70")
    box(ax, .277, .37, .17, .27, "P0", "40 initial answers\nSaved once; hash fixed", COLORS["P0"])
    arrow(ax, (.21, .505), (.27, .505))
    ys = [.77, .55, .33, .11]
    for p, y in zip(REVIEWS, ys):
        box(ax, .545, y, .205, .145, p, LABELS[p], COLORS[p], fill="#FAFBFC")
        arrow(ax, (.451, .505), (.535, y + .073))
        arrow(ax, (.76, y + .073), (.83, .505))
    box(ax, .835, .34, .145, .33, "Rule scoring", "Fixed answer key\nPaired by family\nNo LLM judge", "#445B70")
    ax.text(.548, .985, "Fresh context for each review", fontsize=10, color="#596B78", va="top")
    ax.text(.365, .255, "Identical first-answer text\nNo reviews see each other", ha="center", va="top",
            fontsize=9.5, color="#596B78", linespacing=1.5)
    footer(fig, f"{summary['planned_groups']} shared-first groups; {summary['complete_tasks']}/{summary['planned_tasks']} tasks completed. "
                "All actors and rules are synthetic.\nThe unit of inference is the case family; variants and repeated roles are not independent human participants.")
    return fig


def percent_axis(ax, ylabel: str) -> None:
    ax.set_ylim(0, 112); ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0", "25", "50", "75", "100"])
    ax.set_ylabel(ylabel); ax.grid(axis="y")
    ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)


def count_bars(ax, procs, numerators, denominators, ylabel) -> None:
    percent_axis(ax, ylabel)
    ax.set_xticks(range(len(procs)), procs)
    values = [100 * n / d if d else None for n, d in zip(numerators, denominators)]
    if all(v is None for v in values):
        ax.set_yticks([]); ax.set_ylabel(""); ax.grid(False)
        ax.text(.5, .60, "Not estimable", transform=ax.transAxes, ha="center", fontsize=17, fontweight="semibold")
        ax.text(.5, .42, "No eligible first answers\nDenominator = 0; not a 0% rate", transform=ax.transAxes,
                ha="center", fontsize=10, color="#596B78", linespacing=1.5)
        return
    for x, (p, n, d, value) in enumerate(zip(procs, numerators, denominators, values)):
        if value is None:
            ax.text(x, 50, "NA", ha="center", fontsize=12, color="#596B78")
            continue
        ax.bar(x, value, width=.64, color=COLORS[p], edgecolor="white", linewidth=.8,
               hatch="//" if p == "P8" else None)
        if value == 0: ax.scatter([x], [0], marker="_", color=COLORS[p], s=200, linewidths=2, zorder=4)
        ax.text(x, value + 3, f"{n}/{d}", ha="center", va="bottom", fontsize=10, fontweight="semibold")


def results_figure(summary: dict):
    fig, axes = plt.subplots(1, 3, figsize=(14, 6.4))
    fig.subplots_adjust(left=.055, right=.98, bottom=.22, top=.77, wspace=.36)
    title(fig, "Decision accuracy and revision outcomes")
    s = summary["procedures"]
    axes[0].set_title("a  Final accuracy", loc="left", pad=18)
    count_bars(axes[0], PROCS, [s[p]["correct"] for p in PROCS], [s[p]["planned"] for p in PROCS], "Correct decisions (%)")
    axes[1].set_title("b  Natural-error repair", loc="left", pad=18)
    count_bars(axes[1], REVIEWS, [s[p]["repaired"] for p in REVIEWS],
               [s[p]["natural_first_errors"] for p in REVIEWS], "Incorrect → correct (%)")
    axes[2].set_title("c  Correct answers changed to wrong", loc="left", pad=18, fontsize=11)
    count_bars(axes[2], REVIEWS, [s[p]["damaged"] for p in REVIEWS],
               [s[p]["first_correct_present"] for p in REVIEWS], "Correct → incorrect (%)")
    footer(fig, "Labels show observed counts. Panels b–c use evidence-present cases and the same P0 first answers.\n"
                "Descriptive pilot only: no inferential intervals are shown; variants within a family are dependent.")
    return fig


def resources_figure(summary: dict):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.4))
    fig.subplots_adjust(left=.07, right=.975, bottom=.25, top=.77, wspace=.26)
    title(fig, "Recorded token use by task type")
    s = summary["procedures"]
    for ax, field, heading in zip(axes, ("input_tokens", "output_tokens"), ("a  Input tokens", "b  Output tokens")):
        ax.set_title(heading, loc="left", pad=16)
        ax.set_xticks(range(5), PROCS); ax.set_ylabel("Recorded tokens")
        ax.grid(axis="y"); ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x / 1000:g}k" if x >= 1000 else f"{x:g}"))
        known = [s[p]["usage_known_tasks"] == s[p]["planned"] for p in PROCS]
        vals = [s[p][field] if k else None for p, k in zip(PROCS, known)]
        maximum = max([v for v in vals if v is not None] or [1])
        ax.set_ylim(0, max(1, maximum * 1.18))
        for x, (p, v) in enumerate(zip(PROCS, vals)):
            if v is None:
                ax.text(x, maximum * .45, "NA\nusage incomplete", ha="center", fontsize=9, color="#596B78")
                continue
            ax.bar(x, v, color=COLORS[p], width=.62, edgecolor="white", linewidth=.8,
                   hatch="//" if p == "P8" else None)
            ax.text(x, v + maximum * .025, f"{v:,}", ha="center", va="bottom", fontsize=9.5, fontweight="semibold")
    footer(fig, "P0 records the first response once. P1/P3/P7/P8 bars contain review-task tokens only, including logged attempts.\n"
                "These are recorded token counts, not FLOPs, monetary charges, or human workload. Missing usage is never treated as zero.")
    return fig


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Validate source artifacts without writing figures")
    args = parser.parse_args()
    try:
        summary, rows, input_hashes = load_completed_data()
        if args.check_only:
            print(json.dumps({"ready": True, "tasks": len(rows), "families": 4, "input_sha256": input_hashes}, indent=2))
            return 0
        setup_style()
        out = ROOT / "figures"; out.mkdir(exist_ok=True)
        products = []
        with tempfile.TemporaryDirectory(prefix=".render_", dir=out) as temp:
            staging = Path(temp)
            for name, build in (("fig1_design", design_figure), ("fig2_results", results_figure), ("fig3_resources", resources_figure)):
                fig = build(summary)
                try:
                    for ext in ("svg", "png", "pdf"):
                        p = staging / f"{name}.{ext}"
                        fig.savefig(p, dpi=300, bbox_inches="tight", pad_inches=.16)
                        products.append(p.name)
                finally:
                    plt.close(fig)
            for relative, expected in input_hashes.items():
                require(sha256(ROOT / relative) == expected, "Input changed while rendering; staged figures were not published")
            manifest = {"generated_utc": datetime.now(timezone.utc).isoformat(),
                        "source_phase": "dev", "tasks": 200, "families": 4,
                        "input_sha256": input_hashes, "script_sha256": sha256(Path(__file__)),
                        "matplotlib": matplotlib.__version__,
                        "outputs": {name: sha256(staging / name) for name in products},
                        "synthetic_data": "Actual model responses to synthetic dossiers; no fabricated measurements",
                        "uncertainty_display": "Descriptive counts only; no confidence intervals",
                        "visual_review": "pending"}
            for name in products:
                (staging / name).replace(out / name)
            (out / "figure_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"rendered": products, "output_dir": str(out), "visual_review": "pending"}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Refusing to render: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
