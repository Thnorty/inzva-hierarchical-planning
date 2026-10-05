"""Rebuild ``results/runs.csv``, the evaluation-run table, from surviving records.

**Written 2026-10-05.** The original ``results/runs.csv`` was lost with the rest
of the teammate's working tree. This regenerates it from the files that
survived, and every rate comes from a record, never from prose:

* ``results/colab/runs_rows.csv`` -- the rows the Colab notebook appended to
  Drive at the end of each eval, which is what ``runs.csv`` was built from;
* the per-episode manifests in ``results/colab/manifests/``, which must agree
  with any rate they cover (checked, and the script stops if they do not);
* the acting diagnostics' JSON in ``results/colab/acting/``.

Two kinds of row are flagged rather than silently mixed in, in a ``source``
column the original did not have:

* ``timing`` -- the 4- and 50-episode runs at ``eval.eval_budget=10`` (their
  overrides are in ``code/outputs/2026-09-26/``). They measured solve time, and
  their success rates (0/4, 1/50) mean nothing;
* ``text-only`` -- the first oracle run at 50 steps (60.0 %, 2026-09-27). Its
  manifest and JSON are gone; the number survives only in docs/FINDINGS.md. It is
  listed so the table is complete, and so nobody mistakes the surviving 58.0 %
  rerun for the run FINDINGS' 2026-09-27 comparisons used.

Dates for the acting runs come from the FINDINGS entries that report them; the
files' own timestamps are Drive copy times in another timezone.

The acting JSON records ``eval_budget`` as 50 even for the ``--max-steps 100``
runs, because ``run_diagnostics.py`` overrides the loop budget without touching
that field. The budget is therefore read from the ``budget100`` file-name suffix.

Usage:
    python analysis/rebuild_runs_csv.py            # writes results/runs.csv
    python analysis/rebuild_runs_csv.py --check    # compare, do not write
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
COLAB = _REPO / "results" / "colab"
OUT = _REPO / "results" / "runs.csv"

FIELDS = ["date", "git_commit", "checkpoint", "planner_variant", "d", "seed",
          "n_episodes", "success_rate", "config_path", "source"]
CKPT = "pusht/main/pusht_hi_lewm_epoch15_object.ckpt"

# runs_rows.csv planner_variant -> manifest that must agree with it
EVAL_MANIFESTS = {
    "hi_online_plain_cem": "hi_online_d50_seed42_n50__hi_pusht_d50_seed42_episodes.tsv",
    "hi_online_empirical_macro": "hi_c_seed42_d50_seed42_n50__hi_pusht_d50_seed42_episodes.tsv",
}

# acting JSON stem -> (date of the FINDINGS entry, planner_variant)
ACTING = {
    "oracle_subgoal_acting_d50_hh2_lh5_seed42": ("2026-09-27", "oracle_staged_hh2_lh5_steps50"),
    "generated_subgoal_acting_d50_hh2_lh2_seed42": ("2026-09-27", "generated_staged_hh2_lh2_steps50"),
    "generated_subgoal_acting_d50_hh1_lh2_seed42": ("2026-09-27", "generated_staged_hh1_lh2_steps50"),
    "oracle_subgoal_acting_d50_hh2_lh2_budget50_seed42": ("2026-10-01", "oracle_staged_hh2_lh2_steps50_rerun"),
    "oracle_subgoal_acting_d50_hh2_lh2_budget100_seed42": ("2026-10-01", "oracle_staged_hh2_lh2_steps100"),
    "generated_subgoal_acting_d50_hh2_lh2_budget100_seed42": ("2026-10-01", "generated_staged_hh2_lh2_steps100"),
}


def manifest_rate(name: str) -> tuple[int, int]:
    with (COLAB / "manifests" / name).open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    return sum(r["status"] == "PASS" for r in rows), len(rows)


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    with (COLAB / "runs_rows.csv").open(newline="") as handle:
        for r in csv.DictReader(handle):
            variant = r["planner_variant"]
            if variant in EVAL_MANIFESTS:
                k, n = manifest_rate(EVAL_MANIFESTS[variant])
                if abs(100 * k / n - float(r["success_rate"])) > 0.01 or n != int(r["n_episodes"]):
                    raise SystemExit(f"{variant}: runs_rows says {r['success_rate']} %, manifest {k}/{n}")
                source = f"colab runs_rows.csv; manifest agrees ({k}/{n})"
            else:
                source = "colab runs_rows.csv; no manifest survives, so it cannot be paired"
            rows.append({**r, "source": source})

    for stem, (date, variant) in ACTING.items():
        meta = json.loads((COLAB / "acting" / f"{stem}.json").read_text())
        rate = round(float(meta["success_rate"]), 1)
        manifest = f"{stem}_episodes.tsv"
        k, n = manifest_rate(manifest)
        if abs(100 * k / n - rate) > 0.01:
            raise SystemExit(f"{stem}: JSON says {rate} %, manifest {k}/{n}")
        budget = 100 if "budget100" in stem else 50
        rows.append({
            "date": date, "git_commit": "unknown", "checkpoint": CKPT, "planner_variant": variant,
            "d": str(meta["goal_offset_steps"]), "seed": str(meta["seed"]),
            "n_episodes": str(meta["num_eval"]), "success_rate": f"{rate:.1f}",
            "config_path": f"analysis/run_diagnostics.py --experiment-kind {meta['experiment_kind']} "
                           f"--high-horizon {meta['high_horizon']} --low-horizon {meta['low_horizon']}"
                           + (" --max-steps 100" if budget == 100 else ""),
            "source": f"colab acting JSON; manifest agrees ({k}/{n})",
        })

    rows.append({
        "date": "2026-09-27", "git_commit": "unknown", "checkpoint": CKPT,
        "planner_variant": "oracle_staged_hh2_lh2_steps50", "d": "50", "seed": "42",
        "n_episodes": "50", "success_rate": "60.0",
        "config_path": "analysis/run_diagnostics.py --experiment-kind oracle_subgoal_acting "
                       "--high-horizon 2 --low-horizon 2",
        "source": "text-only: docs/FINDINGS.md; manifest and JSON lost",
    })

    for run, n in (("probe_d50_seed42_n4", 4), ("scale_d50_seed42_n50", 50)):
        k, m = manifest_rate(f"{run}__hi_pusht_d50_seed42_episodes.tsv")
        assert m == n, run
        rows.append({
            "date": "2026-09-26", "git_commit": "unknown", "checkpoint": CKPT,
            "planner_variant": "hi_online_plain_cem", "d": "50", "seed": "42",
            "n_episodes": str(n), "success_rate": f"{100 * k / n:.1f}",
            "config_path": "config/eval/hi_pusht.yaml+paper_table5_overrides+eval.eval_budget=10",
            "source": "timing: 10-step budget, solve-time measurement only; the rate is meaningless",
        })

    return sorted(rows, key=lambda r: (r["date"], r["planner_variant"]))


def render(rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="report whether runs.csv is current; do not write")
    args = parser.parse_args()
    text = render(build_rows())
    if args.check:
        current = OUT.read_text() if OUT.exists() else ""
        print("runs.csv is current" if current == text else "runs.csv differs from the records")
        return 0 if current == text else 1
    OUT.write_text(text, newline="\n")
    print(text)
    print(f"wrote {OUT.relative_to(_REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
