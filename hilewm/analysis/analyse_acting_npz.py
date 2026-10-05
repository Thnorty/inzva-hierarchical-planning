"""Per-episode anatomy of an acting-diagnostic run: did the agent stop short or miss?

The acting diagnostics report means. The question they do not answer is whether a failed
episode ended **far from the target** (the low-level planner could not get there) or
**near it** (it got there and the task still did not register as solved). The saved
`.npz` has everything needed for that, per episode, with no GPU and no rerun:
`final_latent`, `goal_latent`, `start_latent`, `future_latents` and
`episode_successes`.

    python analysis/analyse_acting_npz.py path/to/oracle_subgoal_acting_...npz
    python analysis/analyse_acting_npz.py ...npz --write-manifest out_episodes.tsv

`--write-manifest` emits the per-episode TSV that `analysis/compare_eval_runs.py` pairs
on, in the same format `h_le_wm/eval/hierarchical.py:246` writes for the eval path
(`eval_index`, `episode_id`, `start_step`, `status`, `video_path`). The acting
diagnostics do not write one themselves, so without this the only way to pair an acting
run against another run is to build the file by hand. `episodes_idx`, `start_steps` and
`episode_successes` are all in the npz, so this is a format conversion with no inference
in it.

For every episode it computes the latent MSE from where the agent ended to the goal, and
both the *distance to* and the index of the nearest true future state to where it ended --
the diagnostics' own `nearest_future_offsets` idea applied to the final position.

The distance has to be read before the index. Every episode has a nearest future step,
including one that ended nowhere near the expert's path, where the index is the least-bad
match and means nothing. So failures are also split three ways: **off the path** (the
nearest future state is further than a given fraction of the start-to-goal distance) says
the agent was steered somewhere the expert never went, which indicts the subgoal; **on the
path, stopped short** indicts the low-level planner; **on the path, reached the end**
indicts the success criterion or the final stage rather than the controller's ability to
track.

That split is reported across thresholds, because it is threshold-dependent and a single
cut would hide the fact. Rest a reading on `progress` and `MSE there`, which need no
threshold; use the sweep to see whether a categorical claim survives one.

`future_index_for_offset` (`hi_acting_diagnostics.py:1124`) maps an offset in environment
steps to `offset - 1`, so index i corresponds to step i+1; this script reports steps.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from hilewm_local.results import record, recorded_run


def mse(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return ((a - b) ** 2).mean(axis=-1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("npz")
    parser.add_argument("--tag", default="")
    parser.add_argument("--write-manifest", default=None, metavar="PATH",
                        help="also write the per-episode TSV that compare_eval_runs.py pairs on")
    parser.add_argument("--on-path-frac", type=float, default=0.25, metavar="F",
                        help="an episode counts as near the expert's path when its nearest "
                             "future state is within F x the start-to-goal distance "
                             "(default 0.25)")
    args = parser.parse_args()

    # Schema check before anything is recorded. `low_level_reality_gap` saves no
    # `final_latent` and no single `episode_successes`: it runs one acting loop per
    # offset block and stores `offset_<k>_episode_successes` instead
    # (`hi_acting_diagnostics.py:1289`). There is no "where the agent ended" for that
    # kind, so this analysis does not apply to it and neither does a manifest.
    path = Path(args.npz)
    present = set(np.load(path).files)
    required = {"final_latent", "goal_latent", "start_latent", "future_latents",
                "episode_successes"}
    missing = sorted(required - present)
    if missing:
        print(f"{path.name}\narrays: {', '.join(sorted(present))}\n")
        print(f"skipping: this npz has no {', '.join(missing)}.")
        print("Per-episode anatomy needs a single final state and one success flag per")
        print("episode; an experiment that stores per-offset successes has neither.")
        return 0

    with recorded_run("analyse_acting_npz", args, tag=args.tag):
        data = np.load(path)
        print(f"{path.name}\narrays: {', '.join(sorted(data.files))}\n")

        final, goal, start = data["final_latent"], data["goal_latent"], data["start_latent"]
        future = data["future_latents"]                    # (B, T, D)
        success = np.asarray(data["episode_successes"]).astype(bool)
        n, horizon = success.size, future.shape[1]

        to_goal = mse(final, goal)
        from_start = mse(start, goal)
        progress = 1.0 - to_goal / np.maximum(from_start, 1e-12)   # 1 = arrived, 0 = no move

        # Nearest true future state to where the agent actually ended.
        distances = ((final[:, None, :] - future) ** 2).mean(axis=-1)   # (B, T)
        nearest_step = distances.argmin(axis=1) + 1
        # The argmin's *value*, not just its index. Without it the index cannot be
        # read: an episode whose final state is far from the whole trajectory still
        # has a nearest step, and it means nothing. Compare this against `MSE to
        # goal` -- if both are large the agent left the expert's path altogether,
        # rather than stopping somewhere along it.
        nearest_mse = distances.min(axis=1)

        print(f"{n} episodes, {int(success.sum())} succeeded "
              f"({100.0 * success.mean():.1f} %), future horizon {horizon} steps\n")
        header = (f"{'group':10s} {'n':>3s} {'MSE to goal':>12s} {'progress':>9s} "
                  f"{'nearest step':>13s} {'MSE there':>10s}")
        print(header)
        print("-" * len(header))
        for name, mask in (("succeeded", success), ("failed", ~success), ("all", np.ones_like(success))):
            if not mask.any():
                continue
            print(f"{name:10s} {int(mask.sum()):3d} {np.median(to_goal[mask]):12.3f} "
                  f"{np.median(progress[mask]):9.2f} {np.median(nearest_step[mask]):13.1f} "
                  f"{np.median(nearest_mse[mask]):10.3f}")

        stage_target_stats = None
        if "oracle_stage_targets" in data.files:
            targets = data["oracle_stage_targets"]          # (B, stages, D)
            to_last = mse(final, targets[:, -1, :])
            print(f"\nMSE from the final latent to the last oracle stage target: "
                  f"median {np.median(to_last):.3f} "
                  f"(succeeded {np.median(to_last[success]):.3f}, "
                  f"failed {np.median(to_last[~success]):.3f})")
            stage_target_stats = {
                "median": float(np.median(to_last)),
                "median_success": float(np.median(to_last[success])) if success.any() else None,
                "median_failure": float(np.median(to_last[~success])) if (~success).any() else None}

        if args.write_manifest:
            # Same columns and order as write_episode_manifest
            # (h_le_wm/eval/hierarchical.py:246). video_path is empty: the diagnostics
            # record no videos, and compare_eval_runs.py does not read the column.
            episodes_idx = np.asarray(data["episodes_idx"]).reshape(-1)
            start_steps = np.asarray(data["start_steps"]).reshape(-1)
            if not (episodes_idx.size == start_steps.size == n):
                raise SystemExit(
                    f"cannot write a manifest: {n} successes against "
                    f"{episodes_idx.size} episode ids and {start_steps.size} start steps")
            manifest = Path(args.write_manifest)
            manifest.parent.mkdir(parents=True, exist_ok=True)
            with manifest.open("w") as fh:
                fh.write("eval_index\tepisode_id\tstart_step\tstatus\tvideo_path\n")
                for index, (episode, step, ok) in enumerate(
                        zip(episodes_idx, start_steps, success)):
                    fh.write(f"{index}\t{int(episode)}\t{int(step)}\t"
                             f"{'PASS' if ok else 'FAIL'}\t\n")
            print(f"\nmanifest -> {manifest} ({n} episodes, "
                  f"{int(success.sum())} PASS)")

        reached_end = nearest_step >= horizon - 1
        print(f"\nepisodes whose final state is nearest the last future step: "
              f"{int(reached_end.sum())}/{n}")
        print(f"   of those, succeeded: {int((reached_end & success).sum())}")
        print(f"   of those, failed:    {int((reached_end & ~success).sum())}")
        print(f"failed episodes that stopped short (nearest step < {horizon - 1}): "
              f"{int((~reached_end & ~success).sum())}")

        # The index above is only meaningful for an episode that ended *near* the
        # expert's path. Split the failures by whether they did, using the
        # start-to-goal distance as the unit -- the same scale `progress` uses.
        #
        # The split is reported at several thresholds on purpose. A single cut turns a
        # graded difference into a categorical one, and a sweep on 2026-10-01 showed
        # exactly that: generated and oracle failures separate at 0.25 and 0.50 and are
        # indistinguishable at 0.10, because the cut at 0.25 happens to fall between
        # their median distances. The threshold-free quantities above -- `progress` and
        # `MSE there` -- are what the reading should rest on.
        failed = ~success
        fracs = sorted({0.10, 0.25, 0.50, args.on_path_frac})
        print(f"\nfailures split by whether they stayed near the expert's path, at "
              f"several thresholds")
        print("(threshold = fraction of the start-to-goal distance; the split is "
              "threshold-dependent,")
        print(" so read it as a sweep, not as three counts):\n")
        header = (f"{'threshold':>9s} {'off the path':>13s} {'stopped short':>14s} "
                  f"{'reached the end':>16s}")
        print(header)
        print("-" * len(header))
        splits = {}
        for frac in fracs:
            on_path = nearest_mse <= frac * from_start
            off = int((failed & ~on_path).sum())
            short = int((failed & on_path & ~reached_end).sum())
            end = int((failed & on_path & reached_end).sum())
            splits[f"{frac:g}"] = {"off_path": off, "stopped_short": short,
                                   "reached_end": end}
            marker = "  <- --on-path-frac" if frac == args.on_path_frac else ""
            print(f"{frac:9.2f} {off:13d} {short:14d} {end:16d}{marker}")
        print("\nReading: 'stopped short' points at the low-level planner, 'reached the end'")
        print("at the success criterion or the final stage, and 'off the path' at the")
        print("subgoal -- the agent was steered somewhere the expert never went. Read the")
        print("'MSE there' column above before any of them: a nearest step is reported for")
        print("every episode, including ones nowhere near the trajectory.")

        record("acting_npz_anatomy",
               npz=str(path), n_episodes=int(n), successes=int(success.sum()),
               success_rate=float(100.0 * success.mean()), future_horizon=int(horizon),
               mse_to_goal_median=float(np.median(to_goal)),
               mse_to_goal_median_success=float(np.median(to_goal[success])) if success.any() else None,
               mse_to_goal_median_failure=float(np.median(to_goal[~success])) if (~success).any() else None,
               progress_median=float(np.median(progress)),
               progress_median_success=float(np.median(progress[success])) if success.any() else None,
               progress_median_failure=float(np.median(progress[~success])) if (~success).any() else None,
               nearest_step_median=float(np.median(nearest_step)),
               nearest_step_median_success=float(np.median(nearest_step[success])) if success.any() else None,
               nearest_step_median_failure=float(np.median(nearest_step[~success])) if (~success).any() else None,
               nearest_mse_median=float(np.median(nearest_mse)),
               nearest_mse_median_success=float(np.median(nearest_mse[success])) if success.any() else None,
               nearest_mse_median_failure=float(np.median(nearest_mse[~success])) if (~success).any() else None,
               on_path_frac=float(args.on_path_frac),
               reached_last_step=int(reached_end.sum()),
               reached_and_failed=int((reached_end & ~success).sum()),
               stopped_short_and_failed=int((~reached_end & ~success).sum()),
               failure_split_by_threshold=splits,
               last_stage_target_distance=stage_target_stats,
               manifest=str(args.write_manifest) if args.write_manifest else None)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
