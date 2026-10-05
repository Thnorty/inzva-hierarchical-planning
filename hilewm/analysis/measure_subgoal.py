"""Is the subgoal the high level hands down a good control target?

The second axis of the diagnosis. `measure_support.py` asks whether the
*macro-action* is in the support of the training data; this asks whether the
*waypoint it produces* is something the low level can and should chase. The two
come apart: fixed-stride d_l=8 and both VQ variants search in-support and still
do not win, so support alone does not explain the results.

Four measurements, all on the same CEM run:

1. **Model exploitation.** Compare the terminal cost CEM achieves,
   ‖ẑ_H − z_goal‖², with the cost of the expert's own macro-actions on the same
   segment. The expert's actions provably reach the goal, so the model believing
   CEM's plan is better than the expert's is the model being exploited, and the
   ratio measures by how much.

2. **Cost/subgoal mismatch.** With `horizon: 2`, `get_cost_high` scores the
   *last* predicted waypoint (`h_le_wm/models/jepa.py:469-471`) while the subgoal
   handed to the low level is the *first* (`h_le_wm/planning/policies.py:822`).
   We correlate the optimised terminal cost against the first waypoint's error
   versus the true intermediate frame. A weak or positive correlation means the
   objective does not select good subgoals.

3. **Subgoal realism.** Distance from the predicted first waypoint to a cloud of
   encoded real frames, against the same distance for true frames. A subgoal that
   is not a plausible observation cannot be reached whatever the controller does.

4. **Reachability.** Run the low-level CEM toward the predicted subgoal and
   toward the true intermediate waypoint, and compare how close each gets under
   the model's own low-level rollout. Separates "bad subgoal" from
   "unreachable subgoal".

Usage:

    export PYTHONPATH="$PWD/code:$PWD/analysis"
    python analysis/measure_subgoal.py \\
        --checkpoint checkpoints/pusht/main/pusht_hi_lewm_epoch15_weights.ckpt \\
        --dataset code/data/stablewm/pusht_expert_train.h5

`--solver empirical` runs the same four measurements with Hi-LeWM-C's
`EmpiricalMacroActionSolver` instead of plain CEM, on the same checkpoint and
the same segments, so the pair is controlled. `--seed 2000+k` reproduces
`audit_dimensionality.py --checks draws` draw *k* under either solver.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from hilewm_local import HDF5Columns, build_action_scaler, build_model
from hilewm_local.patches import apply_cem_env_count_fix
from hilewm_local.budgets import add_budget_args, apply_budget
from hilewm_local.results import record, recorded_run
from hilewm_local.swm_compat import cem_solver_class

import importlib.util
import sys

_spec = importlib.util.spec_from_file_location("_measure_support", Path(__file__).with_name("measure_support.py"))
_ms = importlib.util.module_from_spec(_spec)
sys.modules["_measure_support"] = _ms
_spec.loader.exec_module(_ms)

encode_frames = _ms.encode_frames
encode_spans = _ms.encode_spans
valid_starts = _ms.valid_starts
partition_total = _ms.partition_total


def pct(x: torch.Tensor, q: float) -> float:
    return float(x.quantile(q))


def run(args) -> int:
    torch.set_grad_enabled(False)
    apply_cem_env_count_fix()
    record(budget=apply_budget(args), solver=args.solver)

    model, spec = build_model(args.checkpoint, with_encoder=True)
    d_l = spec.latent_action_dim
    print(f"checkpoint : {Path(args.checkpoint).name}")
    print(f"spec       : {spec.describe()}")

    data = HDF5Columns(args.dataset)
    scaler = build_action_scaler(data)["action"]
    action = np.asarray(data.get_col_data("action"))
    episode_ids = np.asarray(data.get_col_data("episode_idx"))
    step_idx = np.asarray(data.get_col_data("step_idx"))

    group = spec.macro_input_dim // action.shape[1]
    goal_tok = max(1, math.ceil(args.goal_offset / args.frame_skip))
    spans = partition_total(goal_tok, args.horizon)
    total_raw = goal_tok * group
    first_raw = spans[0] * group
    print(f"spans      : d={args.goal_offset} -> {spans} tokens per stage; "
          f"first subgoal is {first_raw} primitive steps in, goal is {total_raw}")

    rng = np.random.default_rng(args.seed)
    starts = np.sort(valid_starts(episode_ids, step_idx, total_raw + 1, args.num_eval, rng))

    z_init = encode_frames(model, data.get_row_data(starts, ["pixels"])["pixels"])
    z_goal = encode_frames(model, data.get_row_data(starts + total_raw, ["pixels"])["pixels"])
    z_true1 = encode_frames(model, data.get_row_data(starts + first_raw, ["pixels"])["pixels"])

    expert_macros = torch.stack(
        [
            encode_spans(model, action, scaler, starts + int(off) * group, spans[i], group)
            for i, off in enumerate(np.cumsum([0] + spans[:-1]))
        ],
        dim=1,
    )  # (N, horizon, d_l)

    CEMSolver = cem_solver_class()
    from gymnasium.spaces import Box

    empirical = args.solver == "empirical"
    label = "Hi-LeWM-C" if empirical else "CEM"
    if empirical:
        # Mirrors audit_dimensionality.py's empirical branch exactly, so a run at
        # --seed 2000+k reproduces that script's draw k. Note the two seeds are
        # different things there and stay different here: the bank is built once
        # from --bank-seed (the audit's args.seed, 42), while the solver is seeded
        # per draw. Folding them together would silently change every number.
        from h_le_wm.planning.policies import (
            EmpiricalMacroActionSolver,
            build_empirical_macro_action_bank,
        )

        if spec.is_vq:
            raise ValueError(
                "--solver empirical is only defined for the continuous checkpoints: the bank holds "
                "unquantised macro-actions and rollout_high would quantise them. Untested, so refused."
            )
        if len(set(spans)) != 1:
            raise ValueError(
                f"--solver empirical needs one chunk_len for the bank, but d={args.goal_offset} splits "
                f"into unequal stages {spans}. Generalise the bank per stage before running this."
            )
        bank_cfg = {
            "enabled": True,
            "num_sequences": args.bank_size,
            "chunk_len": spans[0],
            "residual_scale": args.residual_scale,
            "min_residual_std": 1.0e-3,
            "return_top_candidates": 8,
            "encode_batch_size": 4096,
            "stage_sampling": args.stage_sampling,
            "seed": args.bank_seed,
        }
        bank = build_empirical_macro_action_bank(
            model=model, dataset=data, cfg=bank_cfg, high_horizon=args.horizon, high_action_block=1,
            process={"action": scaler}, seed=args.bank_seed,
        )
        record(empirical_config={
            **bank_cfg,
            "lambda_res": args.residual_scale,
            "bank_shape": list(bank["actions"].shape),
            "raw_macro_len": int(bank["raw_macro_len"]),
            "source": "shipped config/eval/hi_pusht.yaml defaults unless overridden",
        })
        print(f"\nbank       : {bank['actions'].shape[0]} sequences x {args.horizon} stages x {d_l} "
              f"(raw_macro_len {int(bank['raw_macro_len'])}), lambda_res={args.residual_scale}, "
              f"stage_sampling={args.stage_sampling}, bank seed {args.bank_seed}")
        solver = EmpiricalMacroActionSolver(
            model=model, macro_bank=bank["actions"], batch_size=args.batch_size,
            num_samples=args.num_samples, var_scale=1.0, n_steps=args.n_steps, topk=args.topk,
            device="cpu", seed=args.seed, residual_scale=args.residual_scale,
            min_residual_std=1.0e-3, return_top_candidates=8, stage_sampling=args.stage_sampling,
        )
    else:
        solver = CEMSolver(
            model=model, batch_size=args.batch_size, num_samples=args.num_samples,
            var_scale=1.0, n_steps=args.n_steps, topk=args.topk, device="cpu", seed=args.seed,
        )

    solver.configure(
        action_space=Box(-1.0, 1.0, (args.num_eval, d_l), np.float32),
        n_envs=args.num_eval,
        config=SimpleNamespace(horizon=args.horizon, receding_horizon=1, action_block=1),
    )
    print(f"\nhigh search: {label}, {args.num_eval} segments x {args.num_samples} samples "
          f"x {args.n_steps} steps")
    out = solver.solve({"z_init": z_init, "z_goal": z_goal, "planner_level": "high"})
    cem_macros = torch.as_tensor(out["actions"]).reshape(args.num_eval, args.horizon, d_l)

    cem_roll = model.rollout_high(z_init, cem_macros)[:, 0]        # (N, horizon, D)
    exp_roll = model.rollout_high(z_init, expert_macros)[:, 0]

    cem_terminal = (cem_roll[:, -1] - z_goal).pow(2).sum(-1)
    exp_terminal = (exp_roll[:, -1] - z_goal).pow(2).sum(-1)

    print("\n=== 1. model exploitation: predicted terminal cost ‖ẑ_H − z_goal‖² ===")
    print(f"  {label + ' selected macro-actions':<32}: median {cem_terminal.median():9.2f}   p90 {pct(cem_terminal, .9):9.2f}")
    print(f"  {'expert macro-actions':<32}: median {exp_terminal.median():9.2f}   p90 {pct(exp_terminal, .9):9.2f}")
    ratio = exp_terminal.median() / cem_terminal.median()
    print(f"  -> the model believes {label}'s plan beats the expert's by x{float(ratio):.1f}")
    beat = float((cem_terminal < exp_terminal).float().mean())
    print(f"  -> {label} 'beats' the expert on {beat:.0%} of segments")
    record(
        headline=f"{spec.describe().split()[0]} d_l={d_l} ({label}): "
                 f"exploitation x{float(ratio):.1f}, wins {beat:.0%}",
        expert_terminal_cost_median=float(exp_terminal.median()),
        cem_terminal_cost_median=float(cem_terminal.median()),
        exploitation_ratio=float(ratio),
        cem_beats_expert_fraction=beat,
    )

    print("\n=== 2. cost/subgoal mismatch ===")
    first_err = (cem_roll[:, 0] - z_true1).pow(2).sum(-1)
    exp_first_err = (exp_roll[:, 0] - z_true1).pow(2).sum(-1)
    record(first_waypoint_error_cem=float(first_err.median()),
           first_waypoint_error_expert=float(exp_first_err.median()))
    print(f"  first-waypoint error vs the true frame:")
    print(f"    {label + ' subgoal':<17}: median {first_err.median():9.2f}")
    print(f"    {'expert':<17}: median {exp_first_err.median():9.2f}")
    if args.num_eval >= 4:
        def pearson(x: torch.Tensor, y: torch.Tensor) -> float:
            a, b = x - x.mean(), y - y.mean()
            return float((a * b).sum() / (a.norm() * b.norm() + 1e-12))

        def ranks(x: torch.Tensor) -> torch.Tensor:
            """Average ranks, so ties do not bias the correlation."""
            order = x.argsort()
            r = torch.empty_like(x)
            r[order] = torch.arange(len(x), dtype=x.dtype)
            _, inverse, counts = x.unique(return_inverse=True, return_counts=True)
            if int(counts.max()) > 1:  # average the ranks within each tie group
                sums = torch.zeros(len(counts), dtype=x.dtype).index_add_(0, inverse, r)
                r = (sums / counts)[inverse]
            return r

        corr = pearson(cem_terminal, first_err)
        # Both quantities are heavy-tailed — terminal cost's p90 is ~10x its
        # median — so a Pearson r is set by a few extreme segments. Spearman is
        # the estimator to read; Pearson is kept because earlier runs reported it.
        spear = pearson(ranks(cem_terminal), ranks(first_err))
        # |r| at p=0.05, two-sided, from the normal approximation to Fisher's z.
        crit = 1.96 / (args.num_eval - 3) ** 0.5
        print(f"  corr(terminal cost, first-waypoint error): "
              f"Spearman {spear:+.3f}   Pearson {corr:+.3f}")
        record(cost_subgoal_corr=corr, cost_subgoal_spearman=spear,
               cost_subgoal_corr_crit_p05=crit)
        verdict = "significant" if abs(spear) > crit else "NOT significant"
        print(f"    (n={args.num_eval}: |r| > {crit:.2f} is significant at p=0.05; "
              f"Spearman is {verdict}.")
        print("     Positive r means lower cost goes with a better subgoal, i.e. the")
        print("     horizon-2 objective is not actively selecting bad subgoals.)")

    print("\n=== 3. subgoal realism: distance to encoded real frames ===")
    ref_rows = np.sort(rng.choice(len(action) - 1, size=args.num_frames, replace=False))
    frames = torch.cat(
        [
            encode_frames(model, data.get_row_data(ref_rows[i : i + 256], ["pixels"])["pixels"])
            for i in range(0, len(ref_rows), 256)
        ]
    )
    mu = frames.mean(0)
    cf = frames - mu
    cov = (cf.T @ cf) / (frames.shape[0] - 1) + 1e-4 * torch.eye(frames.shape[1])
    inv = torch.linalg.pinv(cov)

    def md2(x):
        c = x - mu
        return torch.einsum("bi,ij,bj->b", c, inv, c)

    def nn(x):
        return torch.cdist(x, frames).min(dim=1).values

    print(f"  reference: {frames.shape[0]} encoded frames in R^{frames.shape[1]}")
    print(f"{'population':>21}  {'Mahalanobis² median':>20}  {'nearest frame median':>21}")
    # The record key is explicit, not derived from the display name: the solver row
    # is always "cem" whichever search produced it, so records stay comparable
    # across --solver. Which search it was is in the record's `solver` field.
    for name, key, pts in [("true waypoint", "true", z_true1),
                           (f"{label} subgoal ẑ_1", "cem", cem_roll[:, 0]),
                           ("expert-rolled ẑ_1", "expert-rolled", exp_roll[:, 0])]:
        print(f"{name:>21}  {float(md2(pts).median()):>20.2f}  {float(nn(pts).median()):>21.3f}")
        record(**{f"realism_{key}_md2": float(md2(pts).median()),
                  f"realism_{key}_nn": float(nn(pts).median())})

    if not args.skip_reachability:
        print("\n=== 4. reachability under the low-level model ===")
        low_block = args.frame_skip
        low_dim = action.shape[1] * low_block
        low_solver = CEMSolver(
            model=model, batch_size=args.batch_size, num_samples=args.low_samples,
            var_scale=1.0, n_steps=args.low_steps, topk=args.low_topk, device="cpu", seed=args.seed,
        )
        low_solver.configure(
            action_space=Box(-1.0, 1.0, (args.num_eval, action.shape[1]), np.float32),
            n_envs=args.num_eval,
            config=SimpleNamespace(horizon=spans[0], receding_horizon=1, action_block=low_block),
        )
        z_hist = z_init.unsqueeze(1)
        a_hist = torch.zeros(args.num_eval, 1, low_dim)
        print(f"  low CEM: {args.low_samples} samples x {args.low_steps} steps, horizon {spans[0]}")
        for name, key, target in [(f"{label} subgoal", "cem", cem_roll[:, 0]),
                                  ("true waypoint", "true", z_true1)]:
            res = low_solver.solve({"z_hist": z_hist, "a_hist": a_hist,
                                    "z_subgoal": target, "planner_level": "low"})
            acts = torch.as_tensor(res["actions"]).unsqueeze(1)
            reached = model.rollout_low(z_hist, a_hist, acts)[:, 0, -1]
            err = (reached - target).pow(2).sum(-1)
            rel = err / target.pow(2).sum(-1).clamp_min(1e-6)
            print(f"    -> {name:<16} residual ‖ẑ_low − target‖² median {float(err.median()):9.2f}"
                  f"   relative {float(rel.median()):7.3f}")
            record(**{f"reach_{key}_residual": float(err.median()), f"reach_{key}_relative": float(rel.median())})

    data.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--frame-skip", type=int, default=5)
    p.add_argument("--horizon", type=int, default=2)
    p.add_argument("--num-eval", type=int, default=16)
    p.add_argument("--num-frames", type=int, default=1024)
    add_budget_args(p, low=True)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--skip-reachability", action="store_true")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--solver", default="cem", choices=["cem", "empirical"],
                   help="high-level search: 'cem' = plain Hi-LeWM, 'empirical' = Hi-LeWM-C")
    p.add_argument("--residual-scale", type=float, default=0.1,
                   help="Hi-LeWM-C lambda_res (shipped default 0.1)")
    p.add_argument("--bank-size", type=int, default=4096,
                   help="Hi-LeWM-C empirical bank size (shipped default 4096)")
    p.add_argument("--stage-sampling", default="sequence", choices=["sequence", "independent"],
                   help="Hi-LeWM-C bank sampling (shipped default sequence)")
    p.add_argument("--bank-seed", type=int, default=42,
                   help="seed for the Hi-LeWM-C bank only, kept separate from --seed so that "
                        "--seed 2000+k reproduces audit_dimensionality.py's draw k (which builds "
                        "the bank once from its own args.seed, 42)")
    return p


if __name__ == "__main__":
    _args = build_parser().parse_args()
    # The seed is in the file name because a sweep writes one record per draw and
    # they would otherwise differ only by timestamp — the same trap render_subgoals.py
    # hit with its row count.
    _tag = (Path(_args.checkpoint).stem
            + ("_hilewm_c" if _args.solver == "empirical" else "")
            + f"_d{_args.goal_offset}_seed{_args.seed}")
    with recorded_run("measure_subgoal", _args, tag=_tag):
        _code = run(_args)
    raise SystemExit(_code)
