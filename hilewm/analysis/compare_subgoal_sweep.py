"""Paired analysis of the `measure_subgoal` sweep: five variants, six draws.

`run_subgoal_sweep.py` runs `measure_subgoal.py` for every (variant, draw) at
the paper's d=50 budget. Draw *k* is seed 2000+k and the segment sampler depends
only on the dataset and that seed, so **every variant sees the same 16 segments
in draw k** — the same pairing `compare_draws.py` exploits for the audit records,
extended here to the four axis-2 measurements the audits never carried:
first-waypoint error, subgoal realism, and reachability.

This supersedes the single-draw, 20-iteration per-variant tables in FINDINGS
("Axis 2 across all four variants"), which STATUS flags as provisional and warns
must not be presented as established.

Reads only files under `results/`; runs no model.

Usage:
    python analysis/compare_subgoal_sweep.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "analysis"))
from hilewm_local.results import record, recorded_run  # noqa: E402

# Reuse the audit comparison's exact sign test rather than writing a second one.
_spec = importlib.util.spec_from_file_location("_compare_draws", Path(__file__).with_name("compare_draws.py"))
_cd = importlib.util.module_from_spec(_spec)
sys.modules["_compare_draws"] = _cd
_spec.loader.exec_module(_cd)
sign_test, paired = _cd.sign_test, _cd.paired

RECORDS = _REPO / "results" / "measure_subgoal"

# variant -> (checkpoint stem, solver). Mirrors run_subgoal_sweep.VARIANTS.
VARIANTS = {
    "d32": ("pusht_hi_lewm_epoch15_weights.ckpt", "cem"),
    "hilewm_c": ("pusht_hi_lewm_epoch15_weights.ckpt", "empirical"),
    "d8": ("pusht_hi_lewm_fixed_stride_dim8_epoch15_weights.ckpt", "cem"),
    "vq128": ("pusht_hi_lewm_vq128_epoch50_weights.ckpt", "cem"),
    "vq16": ("pusht_hi_lewm_vq16_epoch50_weights.ckpt", "cem"),
}

# metric key -> (label, unit, higher value means). "worse" only labels the print.
METRICS = {
    "exploitation_ratio": ("exploitation (expert cost / solver cost)", "x", "more exploitation"),
    "cem_beats_expert_fraction": ("solver beats expert", "%", "more wins"),
    "first_waypoint_error_cem": ("first-waypoint error ‖ẑ_1 − z_true‖²", "", "worse subgoal"),
    "realism_cem_md2": ("subgoal Mahalanobis² vs real frames", "", "further from centre"),
    "realism_cem_nn": ("subgoal distance to nearest real frame", "", "less realistic"),
    "reach_cem_relative": ("reach error, relative", "", "harder to reach"),
}
# Per-variant references that are not comparable across checkpoints but matter
# for reading the rows: the model's accuracy floor and the best achievable subgoal.
REFERENCES = {
    "expert_terminal_cost_median": "model accuracy floor (expert cost)",
    "first_waypoint_error_expert": "best achievable subgoal (expert ẑ_1)",
    "reach_true_relative": "reach error for a true waypoint",
    # Without these the realism rows cannot be read: the claim is that the subgoal
    # sits *closer to the centre* of the frame distribution than a real frame does
    # (regression to the mean), which is only visible against the true waypoint's
    # own Mahalanobis² and nearest-frame distance.
    "realism_true_md2": "true waypoint Mahalanobis² (the realistic value)",
    "realism_true_nn": "true waypoint distance to nearest real frame",
}


def audit_exploitation() -> dict[str, dict[int, float]]:
    """Per-draw exploitation from the paper-budget audit records, for cross-checking.

    Two traps this avoids. The lambda_res sweep records also carry a `hilewm_c`
    block, so anything with residual_scale != 0.1 must be excluded or it silently
    overwrites the comparable run. And the older d8/VQ records predate the 1-NN
    and first-waypoint columns, so a fixed column index misreads them: the
    exploitation value is instead taken as the token before the `beats` percentage,
    which is stable across both table layouts.
    """
    out: dict[str, dict[int, float]] = {}
    for path in sorted((_REPO / "results" / "audit_dimensionality").glob("*draws*d50.json")):
        rec = json.loads(path.read_text())
        args, metrics = rec["args"], rec["metrics"]
        if metrics.get("budget", {}).get("resolved", {}).get("n_steps") != 40:
            continue
        if args.get("residual_scale", 0.1) != 0.1 or args.get("draws", 0) < 6:
            continue
        for block in rec["stdout"].split("\n--- ")[1:]:
            tag = block.split()[0]
            for line in block.splitlines():
                tokens = line.split()
                if not tokens or not tokens[0].isdigit():
                    continue
                pct = [i for i, t in enumerate(tokens) if t.endswith("%")]
                if pct:
                    out.setdefault(tag, {})[int(tokens[0])] = float(tokens[pct[0] - 1].rstrip("x"))
    return out


def cross_check(data: dict[str, dict[int, dict]], draws: list[int]) -> bool:
    """Every sweep cell must reproduce the audit's exploitation for the same draw.

    The audit prints one decimal, so the tolerance is half a unit in the last place.
    This is the only independent check available for d8, VQ-128 and VQ-16, whose
    audit records predate first-waypoint recording — their subgoal columns cannot
    be checked this way, but the shared high-level search can.
    """
    audit = audit_exploitation()
    print("\ncross-check against the audit records (exploitation, same draw):")
    rows, bad, missing = 0, 0, 0
    for name in data:
        for d in draws:
            got = data[name][d]["exploitation_ratio"]
            want = audit.get(name, {}).get(d)
            if want is None:
                missing += 1
                continue
            rows += 1
            if abs(want - round(got, 1)) >= 0.051:
                bad += 1
                print(f"  MISMATCH {name} draw {d}: audit {want}, sweep {got:.2f}")
    verdict = "PASS" if bad == 0 else "FAIL"
    print(f"  {rows - bad}/{rows} cells reproduce the audit to one decimal -> {verdict}"
          + (f"; {missing} cells have no audit row" if missing else ""))
    record(cross_check_cells=rows, cross_check_mismatches=bad,
           cross_check_missing=missing, cross_check_pass=bad == 0)
    return bad == 0


def load() -> dict[str, dict[int, dict]]:
    """variant -> draw -> metrics, from the complete paper-budget records."""
    out: dict[str, dict[int, dict]] = {name: {} for name in VARIANTS}
    for path in sorted(RECORDS.glob("*.json")):
        rec = json.loads(path.read_text())
        args, metrics = rec.get("args", {}), rec.get("metrics", {})
        if metrics.get("budget", {}).get("source") != "paper Table 5":
            continue
        if "reach_cem_relative" not in metrics or args.get("num_eval") != 16:
            continue
        stem = Path(args.get("checkpoint", "")).name
        solver = args.get("solver", "cem")
        for name, (want_stem, want_solver) in VARIANTS.items():
            if stem == want_stem and solver == want_solver:
                draw = args["seed"] - 2000
                if draw in out[name]:
                    raise SystemExit(
                        f"two complete records for {name} draw {draw}; "
                        f"remove the stale one before comparing ({path.name})"
                    )
                out[name][draw] = metrics
    return out


def column(data: dict[str, dict[int, dict]], name: str, key: str, draws: list[int]) -> list[float]:
    return [data[name][d][key] for d in draws]


def fmt(values: list[float], unit: str) -> str:
    a = np.asarray(values, dtype=float)
    if unit == "%":
        return f"{np.median(a):.0%} ({a.min():.0%}-{a.max():.0%})"
    if unit == "x":
        return f"x{np.median(a):.2f} (x{a.min():.2f}-x{a.max():.2f})"
    return f"{np.median(a):.2f} ({a.min():.2f}-{a.max():.2f})"


def main() -> int:
    data = load()
    missing = {n: sorted(set(range(6)) - set(d)) for n, d in data.items() if len(d) < 6}
    if missing:
        print(f"warning: incomplete variants {missing}; comparing the draws they share")
    shared = sorted(set.intersection(*(set(d) for d in data.values())))
    if not shared:
        raise SystemExit("no draw is present for every variant")
    print(f"variants   : {', '.join(data)}")
    print(f"draws      : {shared} (seeds {[2000 + d for d in shared]}), d=50, 16 segments each")
    print("budget     : paper Table 5 (high 1500x40 topk 10, low 900x30 topk 150)")
    record(draws=shared, variants=sorted(data), n_segments=16)

    # Pairing check: the expert reference must be identical for the two variants
    # that share the d32 checkpoint, on every shared draw. If it is not, the runs
    # are not paired and nothing below is valid.
    a = column(data, "d32", "first_waypoint_error_expert", shared)
    b = column(data, "hilewm_c", "first_waypoint_error_expert", shared)
    ok = all(abs(x - y) < 1e-9 for x, y in zip(a, b))
    print(f"\npairing check: expert ẑ_1 identical for d32 and hilewm_c on all "
          f"{len(shared)} draws -> {'PASS' if ok else 'FAIL'}")
    record(pairing_check_d32_hilewm_c=bool(ok))
    if not ok:
        print("  d32      :", [round(v, 4) for v in a])
        print("  hilewm_c :", [round(v, 4) for v in b])
    cross_check(data, shared)

    print("\n" + "=" * 100)
    print(f"PER-VARIANT MEDIANS over {len(shared)} paired draws (range in brackets)")
    print("=" * 100)
    for key, (label, unit, _) in METRICS.items():
        print(f"\n{label}")
        for name in data:
            values = column(data, name, key, shared)
            print(f"  {name:<10} {fmt(values, unit):>28}")
            record(**{f"{name}__{key}": values})

    print("\n" + "-" * 100)
    print("Per-variant references (NOT comparable across checkpoints — each model has its own scale)")
    print("-" * 100)
    for key, label in REFERENCES.items():
        print(f"\n{label}")
        for name in data:
            values = column(data, name, key, shared)
            print(f"  {name:<10} {fmt(values, ''):>28}")
            record(**{f"{name}__{key}": values})

    # Within-variant, so it is comparable across checkpoints even though the two
    # quantities it divides are not: how far the planner's subgoal sits from the
    # best this representation could do on the same segments. ~1 means the planner
    # is at its representation's ceiling and the ceiling is what limits it.
    print("\n" + "-" * 100)
    print("Achieved / achievable subgoal error, per draw, then median "
          "(1.0 = at this representation's ceiling)")
    print("-" * 100)
    for name in data:
        got = column(data, name, "first_waypoint_error_cem", shared)
        floor = column(data, name, "first_waypoint_error_expert", shared)
        ratios = [g / f for g, f in zip(got, floor)]
        print(f"  {name:<10} {fmt(ratios, 'x'):>28}")
        record(**{f"{name}__subgoal_vs_ceiling": ratios})

    print("\n" + "=" * 100)
    print(f"PAIRED SIGN TESTS, same segments, n={len(shared)} draws (floor p=0.031 at n=6)")
    print("=" * 100)
    for key, (label, unit, higher) in METRICS.items():
        print(f"\n{label}  —  'A>B' counts draws where A has the higher value ({higher})")
        print(f"  {'A vs B':<22} {'A>B':>6} {'ties':>5} {'p':>7}   {'median A/B':>11}")
        for x, y in combinations(data, 2):
            va, vb = column(data, x, key, shared), column(data, y, key, shared)
            wins, losses, ties, p = paired(va, vb)
            ratios = [a / b for a, b in zip(va, vb) if b != 0]
            star = " *" if p <= 0.05 else ""
            print(f"  {x + ' vs ' + y:<22} {str(wins) + '/' + str(wins + losses):>6} {ties:>5} "
                  f"{p:>7.3f}   {np.median(ratios):>10.2f}x{star}")
            record(**{f"sign__{key}__{x}_vs_{y}": {"wins": wins, "losses": losses, "ties": ties,
                                                   "p": p, "median_ratio": float(np.median(ratios))}})
    return 0


if __name__ == "__main__":
    with recorded_run("compare_subgoal_sweep", None, tag="d50_paired_5variants"):
        _code = main()
    raise SystemExit(_code)
