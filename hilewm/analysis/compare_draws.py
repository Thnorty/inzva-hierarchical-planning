"""Paired comparisons across the 10-draw audits.

Every `audit_dimensionality.py --checks draws` run seeds its segment draws with
``2000 + k``, and the segment sampler depends only on the dataset and that seed.
So draw *k* uses the **same 16 segments** in every variant and at every budget:
the audits are paired by construction. Comparing medians with overlapping
ranges throws that away; a paired sign test uses it.

Two questions:

1. **Across variants at the paper budget** — does restricting the search reduce
   exploitation? For each pair, count the draws where A exploits more than B, and
   report an exact two-sided sign test.
2. **Across budgets for one variant** — did doubling the high-level iterations
   (20 -> 40) change the result? The original 20-iteration run predated JSON
   recording and survived only as a 1-decimal text log, so the test compared
   both sides at one decimal and dropped exact ties. That log was lost with the
   old working tree; the run was regenerated on 2026-10-05 as a full record, so
   the test now also runs at full precision. Both are printed.

Records are found by content, not by timestamp (changed 2026-10-05, when every
record was regenerated under a new name): the newest record whose file name
matches the run and whose resolved budget is the one the comparison needs.

Reads only files under `results/`; runs no model.

Usage:
    python analysis/compare_draws.py
"""

from __future__ import annotations

import json
from itertools import combinations
from math import comb
from pathlib import Path

import numpy as np

try:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
    from hilewm_local.results import record
except Exception:  # noqa: BLE001
    def record(**_):
        pass

_REPO = Path(__file__).resolve().parents[1]
_AUDIT = _REPO / "results" / "audit_dimensionality"


def _find(*patterns: str, n_steps: int | None = 40) -> str:
    """Newest audit record matching one of `patterns` at the given high-level budget."""
    hits = []
    for pattern in patterns:
        for path in _AUDIT.glob(pattern):
            if n_steps is not None:
                budget = json.loads(path.read_text(encoding="utf-8"))["metrics"].get("budget", {})
                if budget.get("resolved", {}).get("n_steps") != n_steps:
                    continue
            hits.append(path)
    if not hits:
        raise SystemExit(f"no audit record matches {patterns} at n_steps={n_steps}; "
                         "regenerate it with audit_dimensionality.py (docs/RECONSTRUCTION.md)")
    return max(hits, key=lambda p: p.name).relative_to(_REPO).as_posix()


RECORDS_40 = [_find("*_draws_vq16_vq128_d50.json"), _find("*_draws_d32_d8_d50.json")]
RECORD_20 = _find("*_draws_d32_d8_d50.json", n_steps=20)
# Hi-LeWM-C run, which also re-ran d32 with the extended metrics (1-NN, first-waypoint error).
RECORD_HILEWM_C = _find("*_draws_hilewm_c_d32_lam0.1_d50.json", "*_draws_hilewm_c_d32_d50.json")
# lambda_res sweep, 6 draws each (seeds 2000-2005). lambda_res 0.1 comes from RECORD_HILEWM_C.
RECORD_SPECTRUM = _find("*_spectrum_estimators_d32_d8_fs32_d50.json", n_steps=None)
RECORD_FS32 = _find("*_draws_fs32_d50.json")
RECORDS_LAMBDA = {lam: _find(f"*_draws_hilewm_c_lam{lam:g}_d50.json") for lam in (0.05, 0.3, 1.0)}
ORDER = ["d32", "d8", "vq128", "vq16"]  # least to most restricted search


def sign_test(wins: int, losses: int) -> float:
    """Exact two-sided sign test, ties already removed."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def load_40() -> dict[str, dict[str, list[float]]]:
    out: dict[str, dict[str, list[float]]] = {}
    for rel in RECORDS_40:
        record = json.loads((_REPO / rel).read_text())
        assert record["metrics"]["budget"]["resolved"]["n_steps"] == 40, rel
        for key, value in record["metrics"].items():
            if key.startswith("draws_"):
                out[key.removeprefix("draws_")] = value
    return out


def load_20() -> dict[str, list[float]]:
    """Per-draw exploitation at 20 high-level iterations, at full precision."""
    metrics = json.loads((_REPO / RECORD_20).read_text(encoding="utf-8"))["metrics"]
    out = {tag: metrics[f"draws_{tag}"]["exploitation"] for tag in ("d32", "d8")}
    for tag, values in out.items():
        assert len(values) == 10, (tag, len(values))
    return out


def describe(values: list[float]) -> str:
    a = np.asarray(values)
    return f"median x{np.median(a):5.1f}   range x{a.min():.1f}-x{a.max():.1f}"


def paired(a: list[float], b: list[float]) -> tuple[int, int, int, float]:
    wins = sum(x > y for x, y in zip(a, b))
    losses = sum(x < y for x, y in zip(a, b))
    ties = len(a) - wins - losses
    return wins, losses, ties, sign_test(wins, losses)


def main() -> int:
    d40 = load_40()
    d20 = load_20()

    print("=" * 78)
    print("PAPER BUDGET (d=50: 1500 samples x 40 steps, topk 10), 10 paired draws")
    print("=" * 78)
    print(f"{'variant':>7}  {'exploitation':<34} {'support':<30} {'CEM wins':>8}")
    for tag in ORDER:
        r = d40[tag]
        print(f"{tag:>7}  {describe(r['exploitation']):<34} {describe(r['support']):<30} "
              f"{np.median(r['cem_wins']):>7.0%}")

    print("\nPaired sign tests on exploitation — does A exploit more than B on the same segments?")
    print(f"{'A':>7} vs {'B':<7} {'A>B':>4} {'A<B':>4} {'tie':>4}  {'p (two-sided)':>13}  median of A/B")
    for a, b in combinations(ORDER, 2):
        w, l, t, p = paired(d40[a]["exploitation"], d40[b]["exploitation"])
        ratio = np.median(np.asarray(d40[a]["exploitation"]) / np.asarray(d40[b]["exploitation"]))
        flag = "  *" if p < 0.05 else ""
        print(f"{a:>7} vs {b:<7} {w:>4} {l:>4} {t:>4}  {p:>13.4f}  x{ratio:.2f}{flag}")

    print("\nBUDGET EFFECT: 20 -> 40 high-level iterations, same segments")
    print("(both sides rounded to 1 decimal, as the original comparison had to be)")
    print(f"{'variant':>7}  {'at 20':<28} {'at 40':<28} {'40>20':>6} {'40<20':>6} {'tie':>4}  {'p':>7}")
    budget = {}
    for tag in ("d32", "d8"):
        # Compare at matched precision: the original 20-iteration values only
        # existed to one decimal, so both sides are rounded the same way before
        # pairing. This reproduces the comparison FINDINGS reports.
        at40 = [round(v, 1) for v in d40[tag]["exploitation"]]
        at20 = [round(v, 1) for v in d20[tag]]
        w, l, t, p = paired(at40, at20)
        print(f"{tag:>7}  {describe(d20[tag]):<28} {describe(d40[tag]['exploitation']):<28} "
              f"{w:>6} {l:>6} {t:>4}  {p:>7.4f}{'  *' if p < 0.05 else ''}")
        budget[f"{tag}_1_decimal"] = {"wins_40": w, "wins_20": l, "ties": t, "p": p}
    print("(full precision, possible since the 20-iteration run was regenerated as a record)")
    for tag in ("d32", "d8"):
        w, l, t, p = paired(d40[tag]["exploitation"], d20[tag])
        print(f"{tag:>7}  {'':<28} {'':<28} {w:>6} {l:>6} {t:>4}  {p:>7.4f}{'  *' if p < 0.05 else ''}")
        budget[f"{tag}_full_precision"] = {"wins_40": w, "wins_20": l, "ties": t, "p": p}
    record(budget_effect=budget, records={"paper_budget": RECORDS_40, "iterations_20": RECORD_20,
                                          "hilewm_c": RECORD_HILEWM_C, "spectrum": RECORD_SPECTRUM,
                                          "fs32": RECORD_FS32,
                                          "lambda": {str(k): v for k, v in RECORDS_LAMBDA.items()}})
    compare_hilewm_c(d40)
    compare_lambda_sweep()
    compare_geometry()
    compare_fs32(d40)
    return 0


def compare_geometry() -> None:
    """How many dimensions each encoder uses, under one stated definition.

    An earlier table in FINDINGS mixed two definitions for d32 — dimensions above
    an eigenvalue of 0.4 (8) and dimensions after the largest spectral gap (25) —
    and the two did not add up to 32. Both are printed here, side by side, so the
    one quoted can be named.
    """
    rec = json.loads((_REPO / RECORD_SPECTRUM).read_text())["metrics"]
    print("\n" + "=" * 78)
    print("GEOMETRY — used vs near-empty dimensions, two explicit definitions")
    print("=" * 78)
    print(f"{'variant':>7} {'d_l':>4}  {'gap after':>9} {'drop':>6}  {'before':>6} {'after':>6} "
          f"{'tail var':>9}   {'>0.4':>5} {'<=0.4':>6} {'tail var':>9}   {'smallest':>9}")
    out = {}
    for tag in ("d32", "d8", "fs32"):
        ev = np.asarray(rec[f"spectrum_{tag}"])
        total = ev.sum()
        gap = int(np.argmax(ev[:-1] / ev[1:]))            # index of the last "used" dim
        before, after = gap + 1, len(ev) - gap - 1
        tail_gap = ev[gap + 1:].sum() / total
        above = int((ev > 0.4).sum())
        tail_thr = ev[ev <= 0.4].sum() / total
        print(f"{tag:>7} {len(ev):>4}  {gap + 1:>9} {ev[gap] / ev[gap + 1]:>5.1f}x  {before:>6} {after:>6} "
              f"{tail_gap:>8.2%}   {above:>5} {len(ev) - above:>6} {tail_thr:>8.2%}   {ev[-1]:>9.1e}"
              f"   cond {ev[0] / ev[-1]:.1e}")
        out[tag] = {"gap_after_dim": gap + 1, "used_by_gap": before, "empty_by_gap": after,
                    "tail_variance_by_gap": float(tail_gap), "above_0.4": above,
                    "below_0.4": len(ev) - above, "tail_variance_below_0.4": float(tail_thr),
                    "condition_number": float(ev[0] / ev[-1])}
    record(geometry=out)


def compare_fs32(d40: dict[str, dict[str, list[float]]]) -> None:
    """Separate d_l from the waypoint strategy.

    d32 is random_sorted with 5 waypoints at d_l=32; fs32 is fixed stride 5 with 4
    waypoints at d_l=32; "d8" is fixed stride 5 with 4 waypoints at d_l=8. So
    fs32 vs d32 changes only the strategy, fs32 vs d8 only d_l. All three were
    trained with the 5-token span the macro-actions here use.
    """
    fs = json.loads((_REPO / RECORD_FS32).read_text())["metrics"]
    assert fs["budget"]["resolved"]["n_steps"] == 40
    fs = fs["draws_fs32"]
    d32_full = json.loads((_REPO / RECORD_HILEWM_C).read_text())["metrics"]["draws_d32"]
    d8 = d40["d8"]

    print("\n" + "=" * 78)
    print("fs32 — separating d_l from the waypoint strategy (10 paired draws, paper budget)")
    print("=" * 78)
    print(f"{'metric':<34} {'d32':>10} {'fs32':>10} {'d8':>10}")
    for label, key, unit in (("support, Mahalanobis² ratio", "support", "x"),
                             ("support, 1-NN ratio", "support_nn", "x"),
                             ("exploitation ratio", "exploitation", "x"),
                             ("solver beats expert", "cem_wins", "%"),
                             ("first-waypoint error, solver", "z1_error_cem", ""),
                             ("first-waypoint error, expert", "z1_error_expert", "")):
        def cell(src):
            if key not in src:
                return "—"
            v = float(np.median(src[key]))
            return f"{v:.0%}" if unit == "%" else (f"x{v:.2f}" if unit == "x" else f"{v:.2f}")
        print(f"{label:<34} {cell(d32_full):>10} {cell(fs):>10} {cell(d8):>10}")

    print("\nPaired sign tests (same segments):")
    print(f"{'comparison':<44} {'support':>13} {'exploitation':>13} {'wins':>13} {'ẑ1 error':>13}")
    for label, a, b in (("strategy: d32 vs fs32  (both d_l=32)", d32_full, fs),
                        ("d_l:      fs32 vs d8   (both fixed stride)", fs, d8)):
        cells = []
        for key in ("support", "exploitation", "cem_wins", "z1_error_cem"):
            if key not in a or key not in b:
                cells.append("—")
                continue
            w, l, ties, p = paired(a[key], b[key])
            cells.append(f"{w}/{w + l + ties} p={p:.3f}")
        print(f"{label:<44} " + " ".join(f"{c:>13}" for c in cells))
    print("  (read each cell as: draws where the first-named variant is higher)")


def compare_lambda_sweep() -> None:
    """How Hi-LeWM-C's behaviour depends on lambda_res, the residual scale.

    Every condition is compared on the **same six draws** (seeds 2000-2005): the
    sweep ran six, so the lambda_res 0.1 and plain-CEM runs, which have ten, are
    cut to their first six. Mixing a 10-draw median with 6-draw medians would
    compare different segment sets.
    """
    n = 6
    base = json.loads((_REPO / RECORD_HILEWM_C).read_text())["metrics"]
    conditions: dict[str, dict[str, list[float]]] = {}
    for lam, rel in sorted(RECORDS_LAMBDA.items()):
        rec = json.loads((_REPO / rel).read_text())
        assert rec["metrics"]["budget"]["resolved"]["n_steps"] == 40, rel
        assert abs(rec["metrics"]["empirical_config_hilewm_c"]["lambda_res"] - lam) < 1e-12, rel
        conditions[f"lambda {lam:g}"] = {k: v[:n] for k, v in rec["metrics"]["draws_hilewm_c"].items()}
    conditions["lambda 0.1"] = {k: v[:n] for k, v in base["draws_hilewm_c"].items()}
    order = ["lambda 0.05", "lambda 0.1", "lambda 0.3", "lambda 1"]
    conditions["plain CEM"] = {k: v[:n] for k, v in base["draws_d32"].items()}

    # Pairing check: the expert's error depends only on the segments, never on the solver.
    ref = np.asarray(conditions["plain CEM"]["z1_error_expert"])
    assert all(np.allclose(c["z1_error_expert"], ref) for c in conditions.values()), "segments differ"

    print("\n" + "=" * 78)
    print(f"LAMBDA_RES SWEEP — Hi-LeWM-C on the d32 checkpoint, {n} paired draws (2000-2005)")
    print("=" * 78)
    print("pairing check: expert first-waypoint error identical in every condition — same segments")
    print(f"\n{'condition':<12} {'support MD²':>12} {'support 1-NN':>13} {'exploitation':>13} "
          f"{'CEM wins':>9} {'expl > 1':>9} {'ẑ1 error':>9}")
    for name in order + ["plain CEM"]:
        c = conditions[name]
        above = sum(v > 1 for v in c["exploitation"])
        print(f"{name:<12} {'x%.1f' % np.median(c['support']):>12} {'x%.2f' % np.median(c['support_nn']):>13} "
              f"{'x%.2f' % np.median(c['exploitation']):>13} {np.median(c['cem_wins']):>8.0%} "
              f"{above:>6}/{n:<2} {np.median(c['z1_error_cem']):>9.2f}")
    print(f"{'expert':<12} {'':>12} {'':>13} {'':>13} {'':>9} {'':>9} {np.median(ref):>9.2f}")

    def test(a_name, b_name, key, higher_is="a"):
        a, b = conditions[a_name][key], conditions[b_name][key]
        w, l, t_, p = paired(a, b)
        return w, l, t_, p

    print(f"\nAdjacent lambda values — does the larger lambda_res go further? (sign test, {n} draws)")
    print(f"{'pair':<26} {'support':>14} {'exploitation':>14} {'ẑ1 error':>14}")
    for lo, hi in zip(order, order[1:]):
        cells = []
        for key in ("support", "exploitation", "z1_error_cem"):
            w, l, t_, p = test(hi, lo, key)
            cells.append(f"{w}/{n} p={p:.3f}")
        print(f"{hi + ' > ' + lo:<26} {cells[0]:>14} {cells[1]:>14} {cells[2]:>14}")

    print(f"\nEvery lambda value against plain CEM — does plain CEM go further? (sign test, {n} draws)")
    print(f"{'pair':<26} {'support':>14} {'exploitation':>14} {'ẑ1 error':>14}")
    for name in order:
        cells = []
        for key in ("support", "exploitation", "z1_error_cem"):
            w, l, t_, p = test("plain CEM", name, key)
            cells.append(f"{w}/{n} p={p:.3f}")
        print(f"{'plain CEM > ' + name:<26} {cells[0]:>14} {cells[1]:>14} {cells[2]:>14}")
    print(f"\n(the smallest p a {n}-draw sign test can give is {sign_test(n, 0):.3f})")
    record(lambda_sweep={name: {k: float(np.median(v)) for k, v in conditions[name].items()}
                         for name in order + ["plain CEM"]})


def compare_hilewm_c(d40: dict[str, dict[str, list[float]]]) -> None:
    """Hi-LeWM-C against plain CEM on the same checkpoint and the same segments.

    The cleanest comparison in the project: identical model, identical 16
    segments per draw, identical budget. Only the high-level search differs —
    `EmpiricalMacroActionSolver` over a bank of real action sequences versus
    unconstrained `CEMSolver`.
    """
    record = json.loads((_REPO / RECORD_HILEWM_C).read_text())
    assert record["metrics"]["budget"]["resolved"]["n_steps"] == 40
    emp = record["metrics"]["draws_hilewm_c"]
    cem = record["metrics"]["draws_d32"]
    cfg = record["metrics"]["empirical_config_hilewm_c"]

    print("\n" + "=" * 78)
    print("Hi-LeWM-C vs plain CEM — same d32 checkpoint, same segments, only the search differs")
    print("=" * 78)
    print(f"Hi-LeWM-C: lambda_res={cfg['lambda_res']}, bank {cfg['bank_shape']}, "
          f"stage_sampling={cfg['stage_sampling']} ({cfg['source']})")

    # Reproducibility: this run's d32 must match the earlier paper-budget d32 run exactly.
    old = d40["d32"]
    for key in ("support", "exploitation", "cem_wins"):
        same = np.allclose(old[key], cem[key], rtol=0, atol=1e-9)
        print(f"  reproducibility, d32 {key:<13}: {'identical to the earlier record' if same else 'DIFFERS'}")
        assert same, f"d32 {key} did not reproduce"
    same_expert = np.allclose(emp["z1_error_expert"], cem["z1_error_expert"], rtol=0, atol=1e-9)
    print(f"  pairing check, expert ẑ1 error identical across solvers: {same_expert}")

    rows = (("support, Mahalanobis² ratio", "support", "x"),
            ("support, 1-NN ratio", "support_nn", "x"),
            ("exploitation ratio", "exploitation", "x"),
            ("segments where the solver beats the expert", "cem_wins", "%"),
            ("first-waypoint error, solver", "z1_error_cem", ""),
            ("first-waypoint error, expert", "z1_error_expert", ""))

    def fmt(v, unit):
        return f"{v:.0%}" if unit == "%" else (f"x{v:.2f}" if unit == "x" else f"{v:.2f}")

    print(f"\n{'metric':<44} {'Hi-LeWM-C':>11} {'plain CEM':>11}   {'CEM > C':>7}  {'p':>7}")
    for label, key, unit in rows:
        a, b = np.asarray(emp[key]), np.asarray(cem[key])
        w, l, ties, p = paired(list(b), list(a))       # does plain CEM exceed Hi-LeWM-C?
        print(f"{label:<44} {fmt(np.median(a), unit):>11} {fmt(np.median(b), unit):>11}   "
              f"{w:>2}/{w + l + ties:<4} {p:>7.4f}{'  *' if p < 0.05 else ''}")

    below = sum(v < 1 for v in emp["exploitation"])
    print(f"\nHi-LeWM-C exploitation below x1 (predicted cost worse than the expert's): {below} of 10 draws")
    ratio_to_expert = np.median(np.asarray(emp["z1_error_cem"]) / np.asarray(emp["z1_error_expert"]))
    ratio_cem = np.median(np.asarray(cem["z1_error_cem"]) / np.asarray(cem["z1_error_expert"]))
    print(f"first-waypoint error relative to the expert, median over draws: "
          f"Hi-LeWM-C x{ratio_to_expert:.1f}, plain CEM x{ratio_cem:.1f}")
    print(f"solve time per draw, median: Hi-LeWM-C {np.median(emp['solve_seconds']):.0f}s, "
          f"plain CEM {np.median(cem['solve_seconds']):.0f}s")


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(_REPO / "analysis"))
    from hilewm_local.results import record, recorded_run  # noqa: F401

    with recorded_run("compare_draws", None, tag="d50_paired"):
        code = main()
    raise SystemExit(code)
