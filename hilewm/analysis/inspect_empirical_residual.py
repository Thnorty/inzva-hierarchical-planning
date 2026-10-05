"""How many Hi-LeWM-C candidates are pure bank samples, per CEM iteration?

Reading `EmpiricalMacroActionSolver.solve` (`h_le_wm/planning/policies.py`,
lines 397-426) says line 412, ``residual[:, 0] = 0.0``, zeroes the residual of
sample index 0 only — one candidate per environment per iteration, out of
``num_samples``. This checks that by measuring rather than reading.

Nothing in the artifact is modified. The solver instance is observed from
outside: its bound ``_gather_base_actions`` is wrapped to capture each
iteration's bank anchors, and the model it scores against is wrapped to capture
each iteration's candidates. Their difference is the residual the solver added,
exactly.

Per iteration it reports, summed over environments:

* candidates whose residual is exactly zero — pure bank samples;
* candidates whose residual is merely tiny, below 1e-3 and 1e-2 in norm;
* how many of the top-k elites are pure bank samples;
* the residual scale the solver is using, estimated from the noised candidates.

Usage:
    export PYTHONPATH="$PWD/code:$PWD/analysis"
    python analysis/inspect_empirical_residual.py --dataset code/data/stablewm/pusht_expert_train.h5
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from hilewm_local import HDF5Columns, build_action_scaler, build_model
from hilewm_local.budgets import add_budget_args, apply_budget
from hilewm_local.results import record, recorded_run

_REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("_measure_support", Path(__file__).with_name("measure_support.py"))
_ms = importlib.util.module_from_spec(_spec)
sys.modules["_measure_support"] = _ms
_spec.loader.exec_module(_ms)


class CandidateTap:
    """Stands in for the model: records every candidate batch, then scores it."""

    def __init__(self, model) -> None:
        self.model = model
        self.candidates: list[torch.Tensor] = []
        self.costs: list[torch.Tensor] = []

    def get_cost(self, info_dict, candidates):
        cost = self.model.get_cost(info_dict, candidates)
        self.candidates.append(candidates.detach().clone())
        self.costs.append(cost.detach().clone())
        return cost

    def parameters(self):
        return self.model.parameters()


def run(args) -> int:
    torch.set_grad_enabled(False)
    record(budget=apply_budget(args))
    from gymnasium.spaces import Box
    from h_le_wm.planning.policies import EmpiricalMacroActionSolver, build_empirical_macro_action_bank

    model, spec = build_model(_REPO / "checkpoints/pusht/main/pusht_hi_lewm_epoch15_weights.ckpt",
                              with_encoder=True)
    d = spec.latent_action_dim
    data = HDF5Columns(args.dataset)
    scaler = build_action_scaler(data)
    cfg = {"enabled": True, "num_sequences": args.bank_size, "chunk_len": 5,
           "residual_scale": args.residual_scale, "min_residual_std": 1.0e-3,
           "return_top_candidates": 8, "encode_batch_size": 4096,
           "stage_sampling": args.stage_sampling, "seed": args.seed}
    bank = build_empirical_macro_action_bank(model=model, dataset=data, cfg=cfg, high_horizon=2,
                                             high_action_block=1, process=scaler, seed=args.seed)

    episode_ids = np.asarray(data.get_col_data("episode_idx"))
    step_idx = np.asarray(data.get_col_data("step_idx"))
    seg = np.sort(_ms.valid_starts(episode_ids, step_idx, 51, 16, np.random.default_rng(2000)))[: args.n_envs]
    z_init = _ms.encode_frames(model, data.get_row_data(seg, ["pixels"])["pixels"])
    z_goal = _ms.encode_frames(model, data.get_row_data(seg + 50, ["pixels"])["pixels"])

    tap = CandidateTap(model)
    solver = EmpiricalMacroActionSolver(
        model=tap, macro_bank=bank["actions"], batch_size=args.n_envs, num_samples=args.num_samples,
        var_scale=1.0, n_steps=args.n_steps, topk=args.topk, device="cpu", seed=2000,
        residual_scale=args.residual_scale, min_residual_std=1.0e-3,
        return_top_candidates=8, stage_sampling=args.stage_sampling,
    )
    bases: list[torch.Tensor] = []
    original_gather = solver._gather_base_actions

    def gather_and_record(bank_tensor, base_idx):
        base = original_gather(bank_tensor, base_idx)
        bases.append(base.detach().clone())
        return base

    solver._gather_base_actions = gather_and_record  # instance only; the class is untouched
    solver.configure(action_space=Box(-1.0, 1.0, (args.n_envs, d), np.float32), n_envs=args.n_envs,
                     config=SimpleNamespace(horizon=2, receding_horizon=1, action_block=1))
    out = solver.solve({"z_init": z_init, "z_goal": z_goal, "planner_level": "high"})

    assert len(bases) == len(tap.candidates) == args.n_steps, (len(bases), len(tap.candidates))
    n_envs, n_samples = args.n_envs, args.num_samples
    print(f"\n{args.n_envs} environments x {n_samples} candidates x {args.n_steps} iterations, "
          f"lambda_res={args.residual_scale}, stage_sampling={args.stage_sampling}")
    print(f"{'iter':>4} {'exactly 0':>10} {'< 1e-3':>7} {'< 1e-2':>7} {'noised':>7}  "
          f"{'pure in top-k':>13}  {'residual std':>12} {'|residual mean|':>15}")
    rows = []
    for it, (base, cand, cost) in enumerate(zip(bases, tap.candidates, tap.costs), 1):
        residual = cand - base                                    # (envs, samples, horizon, dim)
        norm = residual.flatten(2).norm(dim=-1)                   # (envs, samples)
        exact = int((norm == 0).sum())
        tiny3 = int((norm < 1e-3).sum())
        tiny2 = int((norm < 1e-2).sum())
        top = torch.topk(cost, k=args.topk, dim=1, largest=False).indices
        pure_in_top = int((torch.gather(norm, 1, top) == 0).sum())
        noised = residual[:, 1:]                                  # sample 0 is the zeroed one
        std_est = float(noised.std(dim=1).mean())
        mean_est = float(noised.mean(dim=1).abs().mean())
        rows.append({"iter": it, "exact_zero": exact, "below_1e-3": tiny3, "below_1e-2": tiny2,
                     "noised": n_envs * n_samples - exact, "pure_in_topk": pure_in_top,
                     "residual_std": std_est, "abs_residual_mean": mean_est})
        if it <= 5 or it % 10 == 0 or it == args.n_steps:
            print(f"{it:>4} {exact:>10} {tiny3:>7} {tiny2:>7} {n_envs * n_samples - exact:>7}  "
                  f"{pure_in_top:>6} / {args.topk * n_envs:<5}  {std_est:>12.4f} {mean_est:>15.4f}")

    total_exact = sum(r["exact_zero"] for r in rows)
    total = n_envs * n_samples * args.n_steps
    final = torch.as_tensor(out["actions"])                       # best candidate ever seen, per env
    final_is_bank = [bool((bank_row := torch.as_tensor(bank["actions"])) is not None and
                          torch.isclose(bank_row, final[e]).flatten(1).all(dim=1).any())
                     for e in range(n_envs)]
    print(f"\npure bank candidates over the whole solve: {total_exact} of {total} "
          f"({100 * total_exact / total:.3f}%) — {total_exact // (n_envs * args.n_steps)} per environment per iteration")
    print(f"returned action is an exact bank sequence: {sum(final_is_bank)} of {n_envs} environments")
    record(headline=f"{total_exact // (n_envs * args.n_steps)} pure-bank candidate per env per iteration "
                    f"of {n_samples}", per_iteration=rows, total_pure=total_exact, total_candidates=total,
           returned_is_bank=final_is_bank, n_envs=n_envs)
    data.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", required=True)
    p.add_argument("--n-envs", type=int, default=4)
    p.add_argument("--residual-scale", type=float, default=0.1)
    p.add_argument("--bank-size", type=int, default=4096)
    p.add_argument("--stage-sampling", default="sequence", choices=["sequence", "independent"])
    p.add_argument("--seed", type=int, default=42)
    add_budget_args(p)
    return p


if __name__ == "__main__":
    _args = build_parser().parse_args()
    with recorded_run("inspect_empirical_residual", _args, tag=f"d{_args.goal_offset}_{_args.stage_sampling}"):
        _code = run(_args)
    raise SystemExit(_code)
