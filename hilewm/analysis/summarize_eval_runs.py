"""Interval estimates for every evaluation run in ``results/runs.csv``.

**Rebuilt 2026-10-05.** The original script was lost with the rest of the
teammate's working tree; this reimplements what docs/FINDINGS.md quotes from it:
success rate, standard error, Wilson and Clopper-Pearson 95 % intervals, and the
difference from the paper's number for the same cell. Checked against FINDINGS'
36.0 % entry: SE 6.8, Wilson 24.1-49.9, Clopper-Pearson 22.9-50.8, -2.7 against
the paper -- all to the digit.

Rows whose ``source`` starts with ``timing`` are listed but not estimated: they
ran a 10-step budget to measure solve time, and their rates mean nothing.

Usage:
    python analysis/summarize_eval_runs.py
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from compare_eval_runs import clopper_pearson, wilson
from hilewm_local.results import record, recorded_run

_REPO = Path(__file__).resolve().parent.parent

# Paper values for the same cell (CLAUDE.md, *Reference numbers from the paper*).
# Flat LeWM is implied by the paper's deltas, never quoted, so it is left out.
PAPER = {
    ("hi_online_plain_cem", 50): 38.7, ("hi_online_plain_cem", 75): 15.3,
    ("hi_online_empirical_macro", 50): 48.7, ("hi_online_empirical_macro", 75): 32.7,
    ("hi_staged_empirical_macro", 50): 64.0, ("hi_staged_empirical_macro", 75): 22.0,
    ("oracle_staged_hh2_lh2_steps100", 50): 73.3,
}


def main() -> int:
    with (_REPO / "results" / "runs.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    print(f"{'date':<11} {'variant':<38} {'d':>3} {'k/n':>6} {'rate':>6} {'SE':>5} "
          f"{'Wilson 95 %':>13} {'C-P 95 %':>13} {'paper':>6} {'diff':>6}")
    summary = []
    for r in rows:
        variant, d, n = r["planner_variant"], int(r["d"]), int(r["n_episodes"])
        rate = float(r["success_rate"])
        k = round(rate * n / 100)
        if r.get("source", "").startswith("timing"):
            print(f"{r['date']:<11} {variant:<38} {d:>3} {k:>2}/{n:<3} {'(timing run, not an estimate)':>40}")
            continue
        p = k / n
        se = math.sqrt(p * (1 - p) / n)
        wl, wh = wilson(k, n)
        cl, ch = clopper_pearson(k, n)
        paper = PAPER.get((variant, d))
        diff = f"{rate - paper:+.1f}" if paper is not None else ""
        note = "  *" if r.get("source", "").startswith("text-only") else ""
        print(f"{r['date']:<11} {variant:<38} {d:>3} {k:>2}/{n:<3} {100 * p:>5.1f}% {100 * se:>5.1f} "
              f"{100 * wl:>5.1f} - {100 * wh:<5.1f} {100 * cl:>5.1f} - {100 * ch:<5.1f} "
              f"{paper if paper is not None else '':>6} {diff:>6}{note}")
        summary.append({"date": r["date"], "variant": variant, "d": d, "passed": k, "n": n,
                        "rate": 100 * p, "se": 100 * se, "wilson_95": [100 * wl, 100 * wh],
                        "clopper_pearson_95": [100 * cl, 100 * ch], "paper": paper,
                        "source": r.get("source", "")})
    if any(s["source"].startswith("text-only") for s in summary):
        print("\n* no surviving record; the rate is from docs/FINDINGS.md")
    record(headline=f"{len(summary)} runs summarised", runs=summary)
    return 0


if __name__ == "__main__":
    with recorded_run("summarize_eval_runs", None):
        _code = main()
    raise SystemExit(_code)
