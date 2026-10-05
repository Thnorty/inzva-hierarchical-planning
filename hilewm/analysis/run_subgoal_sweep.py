"""Run `measure_subgoal.py` across planner variants and segment draws.

Why a script rather than a shell loop: this sweep is ~11 hours and every number
it produces is meant for the interim presentation, so it has to be resumable and
it has to record what it did. Each sub-run records itself through
`measure_subgoal`'s own `recorded_run`, and this script adds an index of which
(variant, draw) pairs it completed.

**Draws are the outer loop, variants the inner one.** The paired sign tests that
carry every claim in FINDINGS need the same segments under every variant, so a
sweep that is stopped early must leave complete draws rather than complete
variants: stopping after draw 3 gives four paired draws for all five variants,
which is usable, while variant-outer would give five finished variants and
nothing to pair the rest against.

Draw *k* is `--seed 2000+k`, which is exactly `audit_dimensionality.py --checks
draws` draw *k*, so these records pair with the existing audit records too.

Resume is by content, not by file name: a (variant, draw) counts as done only if
a record exists whose args match and whose metrics contain the reachability keys
at the paper budget. A run that crashed halfway, or one made with
`--skip-reachability`, does not count.

Usage:

    export PYTHONPATH="$PWD/code:$PWD/analysis"
    python analysis/run_subgoal_sweep.py \\
        --dataset code/data/stablewm/pusht_expert_train.h5 --draws 6
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent

# name -> (checkpoint, --solver). "hilewm_c" is the main checkpoint searched by
# the empirical-macro solver, matching audit_dimensionality.py's naming.
VARIANTS: dict[str, tuple[str, str]] = {
    "d32": ("checkpoints/pusht/main/pusht_hi_lewm_epoch15_weights.ckpt", "cem"),
    "hilewm_c": ("checkpoints/pusht/main/pusht_hi_lewm_epoch15_weights.ckpt", "empirical"),
    "d8": ("checkpoints/pusht/fixed_stride_dim8/pusht_hi_lewm_fixed_stride_dim8_epoch15_weights.ckpt", "cem"),
    "vq128": ("checkpoints/pusht/vq/vq128/pusht_hi_lewm_vq128_epoch50_weights.ckpt", "cem"),
    "vq16": ("checkpoints/pusht/vq/vq16/pusht_hi_lewm_vq16_epoch50_weights.ckpt", "cem"),
}

RECORDS = _REPO / "results" / "measure_subgoal"
# Reachability is the point of the sweep, so a record without it is not "done".
REQUIRED_METRICS = ("reach_cem_residual", "reach_true_residual", "exploitation_ratio")


def completed(checkpoint: str, solver: str, seed: int, goal_offset: int, num_eval: int) -> Path | None:
    """The record for this cell if a complete paper-budget one exists."""
    if not RECORDS.is_dir():
        return None
    for path in sorted(RECORDS.glob("*.json")):
        try:
            rec = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        args = rec.get("args", {})
        metrics = rec.get("metrics", {})
        if (args.get("checkpoint") == checkpoint and args.get("solver", "cem") == solver
                and args.get("seed") == seed and args.get("goal_offset") == goal_offset
                and args.get("num_eval") == num_eval
                and metrics.get("budget", {}).get("source") == "paper Table 5"
                and all(k in metrics for k in REQUIRED_METRICS)):
            return path
    return None


def latest_record(before: set[Path]) -> Path | None:
    """Whichever record appeared that was not there before the sub-run."""
    return next(iter(sorted(set(RECORDS.glob("*.json")) - before)), None)


def main(args) -> int:
    names = [n.strip() for n in args.variants.split(",") if n.strip()]
    unknown = [n for n in names if n not in VARIANTS]
    if unknown:
        raise SystemExit(f"unknown variants {unknown}; known: {sorted(VARIANTS)}")

    seeds = [args.start_seed + k for k in range(args.draws)]
    cells = [(seed, name) for seed in seeds for name in names]  # draw-outer

    todo, skipped = [], []
    for seed, name in cells:
        ckpt, solver = VARIANTS[name]
        done = None if args.no_resume else completed(ckpt, solver, seed, args.goal_offset, args.num_eval)
        (skipped if done else todo).append((seed, name, done))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    index = _REPO / "results" / "subgoal_sweep" / f"{stamp}_index.jsonl"
    index.parent.mkdir(parents=True, exist_ok=True)

    print(f"variants   : {', '.join(names)}")
    print(f"draws      : {args.draws} (seeds {seeds[0]}-{seeds[-1]}), d={args.goal_offset}, "
          f"{args.num_eval} segments")
    print(f"cells      : {len(cells)} total, {len(skipped)} already recorded, {len(todo)} to run")
    for seed, name, done in skipped:
        print(f"  skip  draw {seed - args.start_seed} {name:<9} -> {done.name}")
    eta = timedelta(seconds=int(len(todo) * args.estimate_seconds))
    print(f"estimate   : {args.estimate_seconds / 60:.0f} min per cell -> {eta} "
          f"(done about {(datetime.now() + eta).strftime('%H:%M on %d %b')})")
    print(f"index      : {index.relative_to(_REPO)}")
    if args.dry_run:
        print("\n--dry-run: nothing launched")
        return 0

    env_note = "PYTHONPATH must contain code/ and analysis/ (this process inherits it)"
    print(f"\n{env_note}\n")
    started = time.time()
    failures = 0
    for i, (seed, name, _) in enumerate(todo, start=1):
        ckpt, solver = VARIANTS[name]
        cmd = [sys.executable, "-u", str(_REPO / "analysis" / "measure_subgoal.py"),
               "--checkpoint", ckpt, "--dataset", args.dataset,
               "--solver", solver, "--seed", str(seed),
               "--num-eval", str(args.num_eval), "--goal-offset", str(args.goal_offset)]
        head = f"[{i}/{len(todo)}] draw {seed - args.start_seed} ({seed})  {name}  solver={solver}"
        print(f"\n{'=' * 78}\n{head}\n{'=' * 78}", flush=True)
        before = set(RECORDS.glob("*.json")) if RECORDS.is_dir() else set()
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=_REPO)
        elapsed = time.time() - t0
        record_path = latest_record(before)
        if proc.returncode != 0:
            failures += 1
        with index.open("a") as fh:
            fh.write(json.dumps({
                "variant": name, "checkpoint": ckpt, "solver": solver, "seed": seed,
                "draw": seed - args.start_seed, "goal_offset": args.goal_offset,
                "num_eval": args.num_eval, "returncode": proc.returncode,
                "seconds": round(elapsed, 1),
                "record": record_path.name if record_path else None,
                "finished": datetime.now().isoformat(timespec="seconds"),
            }) + "\n")
        state = "ok" if proc.returncode == 0 else f"FAILED rc={proc.returncode}"
        remaining = timedelta(seconds=int((len(todo) - i) * (time.time() - started) / i))
        print(f"\n-- {head}: {state} in {elapsed / 60:.1f} min; "
              f"{len(todo) - i} cells left, about {remaining} to go", flush=True)

    total = timedelta(seconds=int(time.time() - started))
    print(f"\nsweep done in {total}, {len(todo) - failures}/{len(todo)} ok, "
          f"{failures} failed. Index: {index.relative_to(_REPO)}")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", default="code/data/stablewm/pusht_expert_train.h5")
    p.add_argument("--variants", default=",".join(VARIANTS),
                   help=f"comma-separated from {sorted(VARIANTS)}")
    p.add_argument("--draws", type=int, default=6,
                   help="six is the floor for an exact paired sign test to reach p=0.031")
    p.add_argument("--start-seed", type=int, default=2000,
                   help="draw k is seed start+k, matching audit_dimensionality.py")
    p.add_argument("--goal-offset", type=int, default=50)
    p.add_argument("--num-eval", type=int, default=16)
    p.add_argument("--estimate-seconds", type=float, default=1400.0,
                   help="per-cell estimate for the ETA only (measured: ~23 min at d=50)")
    p.add_argument("--no-resume", action="store_true", help="re-run cells that already have a record")
    p.add_argument("--dry-run", action="store_true")
    return p


if __name__ == "__main__":
    raise SystemExit(main(build_parser().parse_args()))
