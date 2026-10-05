"""Measure what the high-level CEM actually searches over, without an environment.

Runs the artifact's own components -- `calibrate_latent_prior` for the search
box and `stable_worldmodel.solver.cem.CEMSolver` for the search itself -- so the
numbers describe the real planner rather than a reimplementation. The only thing
missing versus a full eval is the environment: `z_init` and `z_goal` come from
encoded dataset frames instead of a rollout, which is exactly what the offline
diagnostics do.

Two measurements:

* **cost ties** -- how many of the CEM candidates land on distinct costs. For the
  VQ checkpoints every candidate is snapped to a codebook entry inside
  `rollout_high`, so many candidates collapse onto the same cost and the elites
  are picked among ties.
* **search box** -- the width of the per-dimension quantile box. Note that
  `CEMSolver` never enforces it: it reads `action_space` only for the action
  dimension (`solver/cem.py:61-64`). The box is reported because its width tells
  us how far the calibration is from the ±3 clamp, not because it bounds the
  search.

Without `--dataset` the script falls back to the [-1, 1] box and says so. Since
the solver ignores the box either way, the tie counts come out identical; the
dataset only changes the reported box width.

**Info-dict ordering matters, and the artifact gets it wrong.**
`CEMSolver.solve` takes the environment count from the *first* value in the info
dict: ``total_envs = len(next(iter(info_dict.values())))``. The artifact's
`_plan_high` and `_plan_low` put the string ``planner_level`` first, so
``total_envs`` becomes ``len("high") == 4`` or ``len("low") == 3`` whatever the
real env count is. We therefore put the tensors first here. This is identical in
stable-worldmodel 0.1.0 and 0.1.1, so it is not a version we picked badly -- see
the note in docs/FINDINGS.md before running a full eval.

Usage:

    export PYTHONPATH="$PWD/code:$PWD/analysis"
    python analysis/measure_high_cem.py \
        --checkpoint checkpoints/pusht/vq/vq16/pusht_hi_lewm_vq16_epoch50_weights.ckpt \
        --dataset code/data/stablewm/pusht_expert_train.h5 \
        --num-samples 1500 --n-steps 20
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import torch

from hilewm_local import HDF5Columns, build_action_scaler, build_model
from hilewm_local.budgets import add_budget_args, apply_budget
from hilewm_local.results import record, recorded_run
from hilewm_local.swm_compat import cem_solver_class


class CostRecorder:
    """Forward `get_cost` to the model while logging every candidate batch."""

    def __init__(self, model: torch.nn.Module) -> None:
        self.model = model
        self.calls: list[torch.Tensor] = []

    def get_cost(self, info_dict: dict, action_candidates: torch.Tensor) -> torch.Tensor:
        cost = self.model.get_cost(info_dict, action_candidates)
        self.calls.append(cost.detach().cpu())
        return cost

    def parameters(self):  # CEMSolver reads the dtype from here
        return self.model.parameters()


def calibrated_box(model: torch.nn.Module, dataset_path: Path, latent_dim: int, seed: int) -> dict[str, np.ndarray]:
    """Run the artifact's own prior calibration on the real dataset."""
    from h_le_wm.planning.policies import calibrate_latent_prior

    dataset = HDF5Columns(dataset_path)
    process = build_action_scaler(dataset)
    # Values shipped in config/eval/hi_pusht.yaml.
    cfg = {
        "enabled": True,
        "num_chunks": 2048,
        "min_chunks_for_stats": 64,
        "chunk_len": 5,
        "lower_q": 5.0,
        "upper_q": 95.0,
        "margin_ratio": 0.05,
        "clamp_abs": 3.0,
        "fallback_abs": 1.0,
    }
    bounds = calibrate_latent_prior(model=model, dataset=dataset, cfg=cfg, process=process, seed=seed)
    dataset.close()
    return bounds


def run(args: argparse.Namespace) -> int:
    torch.set_grad_enabled(False)
    record(budget=apply_budget(args))
    model, spec = build_model(args.checkpoint)
    print(f"checkpoint : {Path(args.checkpoint).name}")
    print(f"spec       : {spec.describe()}")

    latent_dim = spec.latent_action_dim
    if args.dataset:
        path = Path(args.dataset)
        if not path.exists():
            print(f"\n!! dataset not found: {path}", file=sys.stderr)
            return 1
        bounds = calibrated_box(model, path, latent_dim, args.seed)
        low, high = np.asarray(bounds["low"]), np.asarray(bounds["high"])
        width = high - low
        print(f"prior      : calibrate_latent_prior on {path.name}, "
              f"{int(bounds['num_chunks'])} chunks of {int(bounds['chunk_len'])}")
        print(f"box width  : mean {width.mean():.3f}  min {width.min():.3f}  max {width.max():.3f}")
        print(f"box volume : log10 = {np.log10(width).sum():.1f}")
    else:
        low = -np.ones((latent_dim,), dtype=np.float32)
        high = np.ones((latent_dim,), dtype=np.float32)
        print("prior      : *** no dataset given, using the [-1, 1] fallback box ***")

    from gymnasium.spaces import Box

    n_envs = args.n_envs
    space = Box(
        low=np.broadcast_to(low[None, :], (n_envs, latent_dim)).copy(),
        high=np.broadcast_to(high[None, :], (n_envs, latent_dim)).copy(),
        shape=(n_envs, latent_dim),
        dtype=np.float32,
    )

    recorder = CostRecorder(model)
    CEMSolver = cem_solver_class()
    solver = CEMSolver(
        model=recorder,
        batch_size=1,
        num_samples=args.num_samples,
        var_scale=1.0,
        n_steps=args.n_steps,
        topk=args.topk,
        device="cpu",
        seed=args.seed,
    )
    solver.configure(
        action_space=space,
        n_envs=n_envs,
        config=SimpleNamespace(horizon=args.horizon, receding_horizon=1, action_block=1),
    )

    generator = torch.Generator().manual_seed(args.seed)
    # Tensors first: CEMSolver reads the env count off the first value, and a
    # leading string would make it len("high") == 4 instead of n_envs.
    info = {
        "z_init": torch.randn(n_envs, spec.embed_dim, generator=generator),
        "z_goal": torch.randn(n_envs, spec.embed_dim, generator=generator),
        "planner_level": "high",
    }
    print(f"\nrunning CEM: {args.num_samples} samples x {args.n_steps} steps, "
          f"horizon {args.horizon}, topk {args.topk}")
    solver.solve(info)

    print(f"\n{'CEM step':>9}  {'distinct costs':>15}  {'of':>6}  {'cand/cost':>10}")
    fractions = []
    for step, cost in enumerate(recorder.calls, start=1):
        flat = cost.reshape(cost.shape[0], -1)[0]
        total = int(flat.numel())
        distinct = int(torch.unique(flat).numel())
        fractions.append(distinct / total)
        if step <= args.show or step == len(recorder.calls):
            print(f"{step:>9}  {distinct:>15}  {total:>6}  {total / max(distinct, 1):>10.1f}")
    if fractions:
        mean_fraction = float(np.mean(fractions))
        print(f"\nmean distinct fraction over {len(fractions)} steps: {mean_fraction:.3f}")
        print(f"mean candidates per distinct cost           : {1 / max(mean_fraction, 1e-9):.1f}")
        record(
            headline=f"{spec.describe().split()[0]}: {1 / max(mean_fraction, 1e-9):.1f} candidates per distinct cost",
            latent_action_dim=latent_dim,
            is_vq=spec.is_vq,
            distinct_fraction_per_step=fractions,
            mean_distinct_fraction=mean_fraction,
            candidates_per_distinct_cost=1 / max(mean_fraction, 1e-9),
            used_calibrated_box=bool(args.dataset),
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--dataset", default=None, help="pusht_expert_train.h5; omit for the fallback box")
    add_budget_args(p)  # --goal-offset only selects the Table 5 budget here
    p.add_argument("--horizon", type=int, default=2)
    p.add_argument("--n-envs", type=int, default=1)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--show", type=int, default=5, help="how many leading CEM steps to print")
    return p


if __name__ == "__main__":
    _args = build_parser().parse_args()
    with recorded_run("measure_high_cem", _args, tag=Path(_args.checkpoint).stem):
        _code = run(_args)
    raise SystemExit(_code)
