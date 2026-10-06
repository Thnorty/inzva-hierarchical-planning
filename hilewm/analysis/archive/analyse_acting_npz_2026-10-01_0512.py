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
the index of the *nearest true future state* to where it ended -- the diagnostics' own
`nearest_future_offsets` idea applied to the final position. An episode that ends nearest
to future step 30 of 50 stopped short; one that ends nearest to step 49 and still failed
is a near miss, and the limit is then the environment's success criterion or the last
stage, not the controller's ability to track.

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
    args = parser.parse_args()

    with recorded_run("analyse_acting_npz", args, tag=args.tag):
        path = Path(args.npz)
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

        print(f"{n} episodes, {int(success.sum())} succeeded "
              f"({100.0 * success.mean():.1f} %), future horizon {horizon} steps\n")
        header = f"{'group':10s} {'n':>3s} {'MSE to goal':>12s} {'progress':>9s} {'nearest step':>13s}"
        print(header)
        print("-" * len(header))
        for name, mask in (("succeeded", success), ("failed", ~success), ("all", np.ones_like(success))):
            if not mask.any():
                continue
            print(f"{name:10s} {int(mask.sum()):3d} {np.median(to_goal[mask]):12.3f} "
                  f"{np.median(progress[mask]):9.2f} {np.median(nearest_step[mask]):13.1f}")

        if "oracle_stage_targets" in data.files:
            targets = data["oracle_stage_targets"]          # (B, stages, D)
            to_last = mse(final, targets[:, -1, :])
            print(f"\nMSE from the final latent to the last oracle stage target: "
                  f"median {np.median(to_last):.3f} "
                  f"(succeeded {np.median(to_last[success]):.3f}, "
                  f"failed {np.median(to_last[~success]):.3f})")

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
        print("\nReading: failures concentrated in 'stopped short' point at the low-level")
        print("planner; failures that reached the end of the trajectory and still failed")
        print("point at the success criterion or the final stage, not at tracking.")

        record("acting_npz_anatomy",
               npz=str(path), n_episodes=int(n), successes=int(success.sum()),
               success_rate=float(100.0 * success.mean()), future_horizon=int(horizon),
               mse_to_goal_median=float(np.median(to_goal)),
               mse_to_goal_median_success=float(np.median(to_goal[success])) if success.any() else None,
               mse_to_goal_median_failure=float(np.median(to_goal[~success])) if (~success).any() else None,
               progress_median=float(np.median(progress)),
               nearest_step_median=float(np.median(nearest_step)),
               nearest_step_median_success=float(np.median(nearest_step[success])) if success.any() else None,
               nearest_step_median_failure=float(np.median(nearest_step[~success])) if (~success).any() else None,
               reached_last_step=int(reached_end.sum()),
               reached_and_failed=int((reached_end & ~success).sum()),
               stopped_short_and_failed=int((~reached_end & ~success).sum()),
               manifest=str(args.write_manifest) if args.write_manifest else None)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
