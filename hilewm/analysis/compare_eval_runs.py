"""Paired comparison of two runs from their per-episode manifests.

**Rebuilt 2026-10-05.** The original script was lost with the rest of the
teammate's working tree; this is a reimplementation from what docs/FINDINGS.md
says it did, not a recovered copy. It was checked against every paired result
FINDINGS quotes whose manifests survived: the -2.0 / 9:10 / p = 1.00 for
Hi-LeWM-C, and the +22.0 / 17:6 / p = 0.0347, +12.0 / 11:5 / p = 0.21 and
+34.0 / 22:5 / p = 0.0015 at the paper budget all come out to the digit.

A manifest is the artifact's ``*_episodes.tsv`` (``eval_index, episode_id,
start_step, status, video_path``), or one written by ``analyse_acting_npz.py
--write-manifest``. Two runs are paired only if they evaluated the **same
episodes from the same start steps in the same order**; anything else is refused,
because a paired test on mismatched episodes is silently wrong. ``--unpaired``
gives Fisher's exact test instead, which needs only the two rates.

Direction: the difference is **B minus A**, and "discordant b : c" means
*B passed and A failed* : *A passed and B failed*, the form FINDINGS uses.

Usage:

    python analysis/compare_eval_runs.py A_episodes.tsv B_episodes.tsv --tag name
    python analysis/compare_eval_runs.py A.tsv B.tsv --tag name --unpaired
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
from pathlib import Path

from scipy.stats import beta, fisher_exact

from hilewm_local.results import record, recorded_run

_REPO = Path(__file__).resolve().parent.parent


def load_manifest(path: Path) -> list[tuple[str, str, bool]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    statuses = {r["status"] for r in rows}
    if not statuses <= {"PASS", "FAIL"}:
        raise SystemExit(f"{path}: unexpected status values {sorted(statuses - {'PASS', 'FAIL'})}")
    # The eval prints every outcome twice (FINDINGS); a manifest built from that
    # stdout without deduplicating would hold each eval_index twice.
    indices = [r["eval_index"] for r in rows]
    if len(set(indices)) != len(indices):
        raise SystemExit(f"{path}: duplicate eval_index rows -- deduplicate the manifest first")
    return [(r["episode_id"], r["start_step"], r["status"] == "PASS") for r in rows]


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    lo = 0.0 if k == 0 else beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alpha / 2, k + 1, n - k)
    return float(lo), float(hi)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar: a binomial test on the discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def main(args: argparse.Namespace) -> int:
    a_path, b_path = Path(args.a), Path(args.b)
    a, b = load_manifest(a_path), load_manifest(b_path)
    ka, kb = sum(p for *_, p in a), sum(p for *_, p in b)
    na, nb = len(a), len(b)
    name_a, name_b = args.name_a or a_path.stem, args.name_b or b_path.stem

    print(f"A  {name_a}: {ka}/{na} = {100 * ka / na:.1f} %")
    print(f"B  {name_b}: {kb}/{nb} = {100 * kb / nb:.1f} %")
    for label, k, n in (("A", ka, na), ("B", kb, nb)):
        lo, hi = wilson(k, n)
        print(f"   {label} Wilson 95 %: {100 * lo:.1f} - {100 * hi:.1f}")

    _, p_fisher = fisher_exact([[kb, nb - kb], [ka, na - ka]])
    print(f"\nunpaired: difference {100 * (kb / nb - ka / na):+.1f} points, Fisher exact p = {p_fisher:.4f}")
    metrics = {
        "a": {"manifest": str(a_path), "sha256_16": sha256(a_path), "passed": ka, "n": na},
        "b": {"manifest": str(b_path), "sha256_16": sha256(b_path), "passed": kb, "n": nb},
        "unpaired_difference_points": 100 * (kb / nb - ka / na),
        "fisher_exact_p": p_fisher,
    }

    if args.unpaired:
        record(headline=f"{name_a} -> {name_b}: {100 * (kb / nb - ka / na):+.1f} unpaired, "
                        f"Fisher p={p_fisher:.4f}", paired=False, **metrics)
        return 0

    keys_a = [(e, s) for e, s, _ in a]
    keys_b = [(e, s) for e, s, _ in b]
    if keys_a != keys_b:
        mismatched = sum(x != y for x, y in zip(keys_a, keys_b)) + abs(na - nb)
        raise SystemExit(
            f"refusing to pair: the manifests differ at {mismatched} episode slot(s). "
            "Pass --unpaired for Fisher's exact test on the rates alone.")

    both = sum(pa and pb for (*_, pa), (*_, pb) in zip(a, b))
    b_only = sum(pb and not pa for (*_, pa), (*_, pb) in zip(a, b))
    a_only = sum(pa and not pb for (*_, pa), (*_, pb) in zip(a, b))
    neither = na - both - b_only - a_only
    n = na
    diff = (b_only - a_only) / n
    se = math.sqrt((b_only + a_only) - (b_only - a_only) ** 2 / n) / n
    lo, hi = diff - 1.959964 * se, diff + 1.959964 * se
    p_mcnemar = mcnemar_exact(b_only, a_only)

    print(f"\npaired on {n} identical episodes:")
    print(f"{'':>14}{'B pass':>8}{'B fail':>8}")
    print(f"{'A pass':>14}{both:>8}{a_only:>8}")
    print(f"{'A fail':>14}{b_only:>8}{neither:>8}")
    print(f"\npaired difference {100 * diff:+.1f} points (95 % Wald {100 * lo:+.1f} to {100 * hi:+.1f})")
    print(f"discordant {b_only} : {a_only} (B only : A only), McNemar exact p = {p_mcnemar:.4f}")

    record(headline=f"{name_a} -> {name_b}: {100 * diff:+.1f}, {b_only}:{a_only}, McNemar p={p_mcnemar:.4f}",
           paired=True, table={"both_pass": both, "b_only": b_only, "a_only": a_only, "both_fail": neither},
           paired_difference_points=100 * diff, wald_95_points=[100 * lo, 100 * hi],
           mcnemar_exact_p=p_mcnemar, **metrics)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("a", help="manifest of the baseline run (A)")
    p.add_argument("b", help="manifest of the compared run (B)")
    p.add_argument("--tag", required=True, help="name for the record, e.g. subgoal_effect_at_paper_budget")
    p.add_argument("--name-a", default=None)
    p.add_argument("--name-b", default=None)
    p.add_argument("--unpaired", action="store_true", help="Fisher's exact test only; no episode matching")
    return p


if __name__ == "__main__":
    _args = build_parser().parse_args()
    with recorded_run("compare_eval_runs", _args, tag=_args.tag):
        _code = main(_args)
    raise SystemExit(_code)
