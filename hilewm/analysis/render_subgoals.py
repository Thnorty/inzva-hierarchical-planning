"""Decode the subgoals the high level hands down, next to what they should be.

The visual counterpart of `measure_subgoal.py`. That script found the predicted
first waypoint sits *closer to the centre* of the frame distribution than a real
frame does (Mahalanobis² 128 against a chi²(192) median of 191) while being
*further from any individual frame*. That is the signature of regression to the
mean, so the prediction is expected to look like a blurred average of plausible
futures rather than a wrong-but-sharp state. This renders that claim.

Each row is one evaluated segment, and the columns are built so that probe error
and prediction error can be told apart:

1. `frame t` — the raw observation, no probe involved.
2. `probe(z_t)` — encode then decode the same frame. This is the probe's own
   fidelity ceiling; everything to the right is at best this sharp.
3. `probe(z_true)` — the true intermediate frame through the same round trip.
   What a perfect prediction would decode to.
4. `probe(expert ẑ_1)` — the expert's own macro-actions rolled through φ. The
   best this predictor can do on this segment.
5. `probe(CEM ẑ_1)` — what the planner actually sends to the low level.
6. `probe(z_goal)` — the goal, for context.

Column 3 is the reference for the metrics, not column 1, so the reported PSNR
and SSIM measure prediction error with the probe's blur divided out.

**Use `--probe phase_b`** (the default). Phase A is trained `true_only` and has
never seen a predicted latent, so decoding predictions with it conflates a bad
prediction with an out-of-distribution probe input. Phase B is `pred_exposed`.
Pass `--probe both` to see the difference.

Both probes were trained against the main PushT checkpoint, so read the
fixed-stride and VQ variants with care: they share the frozen encoder, but their
`high_pred_proj` is trained separately and their predictions may land somewhere
the probe was not exposed to.

Usage:

    export PYTHONPATH="$PWD/code:$PWD/analysis"
    python analysis/render_subgoals.py \\
        --checkpoint checkpoints/pusht/main/pusht_hi_lewm_epoch15_weights.ckpt \\
        --dataset code/data/stablewm/pusht_expert_train.h5 --rows 6
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from hilewm_local import HDF5Columns, build_action_scaler, build_model, decode_latents, load_decoder
from hilewm_local.patches import apply_cem_env_count_fix
from hilewm_local.probe import decoder_stats_source, probe_model_module
from hilewm_local.budgets import add_budget_args, apply_budget
from hilewm_local.results import record, recorded_run
from hilewm_local.swm_compat import cem_solver_class

import importlib.util
import sys

_spec = importlib.util.spec_from_file_location("_measure_support", Path(__file__).with_name("measure_support.py"))
_ms = importlib.util.module_from_spec(_spec)
sys.modules["_measure_support"] = _ms
_spec.loader.exec_module(_ms)

PROBES = {
    "phase_a": "checkpoints/pusht/probes/phase_a/pusht_decoder_probe_phase_a.pt",
    "phase_b": "checkpoints/pusht/probes/phase_b/pusht_decoder_probe_phase_b.pt",
}
COLUMNS = ["frame t", "probe(z_t)", "probe(z_true)", "probe(expert)", "probe(CEM)", "probe(z_goal)"]


def run(args) -> int:
    torch.set_grad_enabled(False)
    apply_cem_env_count_fix()
    record(budget=apply_budget(args))
    repo = Path(__file__).resolve().parents[1]

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
    spans = _ms.partition_total(goal_tok, args.horizon)
    total_raw, first_raw = goal_tok * group, spans[0] * group

    if args.draw is not None:
        # Reproduce audit draw K exactly: its 16 segments, its solver seed, its batch
        # size. The panel then shows the very subgoals the audit's numbers describe.
        n_solve, solver_seed = 16, 2000 + args.draw
        starts = np.sort(_ms.valid_starts(episode_ids, step_idx, total_raw + 1, n_solve,
                                          np.random.default_rng(solver_seed)))
    else:
        n_solve, solver_seed = args.rows, args.seed
        starts = np.sort(_ms.valid_starts(episode_ids, step_idx, total_raw + 1, args.rows,
                                          np.random.default_rng(args.seed)))

    px_t = data.get_row_data(starts, ["pixels"])["pixels"]
    px_true = data.get_row_data(starts + first_raw, ["pixels"])["pixels"]
    px_goal = data.get_row_data(starts + total_raw, ["pixels"])["pixels"]

    z_t = _ms.encode_frames(model, px_t)
    z_true = _ms.encode_frames(model, px_true)
    z_goal = _ms.encode_frames(model, px_goal)

    expert_macros = torch.stack(
        [
            _ms.encode_spans(model, action, scaler, starts + int(off) * group, spans[i], group)
            for i, off in enumerate(np.cumsum([0] + spans[:-1]))
        ],
        dim=1,
    )

    CEMSolver = cem_solver_class()
    from gymnasium.spaces import Box

    plan_config = SimpleNamespace(horizon=args.horizon, receding_horizon=1, action_block=1)
    space = Box(-1.0, 1.0, (n_solve, d_l), np.float32)
    info = {"z_init": z_t, "z_goal": z_goal, "planner_level": "high"}

    solver = CEMSolver(model=model, batch_size=args.batch_size, num_samples=args.num_samples,
                       var_scale=1.0, n_steps=args.n_steps, topk=args.topk, device="cpu", seed=solver_seed)
    solver.configure(action_space=space, n_envs=n_solve, config=plan_config)
    print(f"\nhigh CEM   : {n_solve} segments x {args.num_samples} samples x {args.n_steps} steps")
    cem_macros = torch.as_tensor(solver.solve(dict(info))["actions"]).reshape(n_solve, args.horizon, d_l)
    subgoals = {"expert": model.rollout_high(z_t, expert_macros)[:, 0, 0],
                "CEM": model.rollout_high(z_t, cem_macros)[:, 0, 0]}

    if args.with_empirical:
        if spec.is_vq:
            raise ValueError("--with-empirical is for continuous checkpoints (Hi-LeWM-C uses the main d32 model)")
        from h_le_wm.planning.policies import EmpiricalMacroActionSolver, build_empirical_macro_action_bank

        bank_cfg = {"enabled": True, "num_sequences": args.bank_size, "chunk_len": spans[0],
                    "residual_scale": args.residual_scale, "min_residual_std": 1.0e-3,
                    "return_top_candidates": 8, "encode_batch_size": 4096,
                    "stage_sampling": args.stage_sampling, "seed": args.bank_seed}
        bank = build_empirical_macro_action_bank(
            model=model, dataset=data, cfg=bank_cfg, high_horizon=args.horizon, high_action_block=1,
            process={"action": scaler}, seed=args.bank_seed)
        emp = EmpiricalMacroActionSolver(
            model=model, macro_bank=bank["actions"], batch_size=args.batch_size, num_samples=args.num_samples,
            var_scale=1.0, n_steps=args.n_steps, topk=args.topk, device="cpu", seed=solver_seed,
            residual_scale=args.residual_scale, min_residual_std=1.0e-3, return_top_candidates=8,
            stage_sampling=args.stage_sampling)
        emp.configure(action_space=space, n_envs=n_solve, config=plan_config)
        emp_macros = torch.as_tensor(emp.solve(dict(info))["actions"]).reshape(n_solve, args.horizon, d_l)
        subgoals["Hi-LeWM-C"] = model.rollout_high(z_t, emp_macros)[:, 0, 0]
        record(empirical_config={**bank_cfg, "lambda_res": args.residual_scale,
                                 "bank_shape": list(bank["actions"].shape)})

    # Only the first `rows` segments are drawn; with --draw the solve still covered all 16.
    if args.draw is not None:
        # Cross-check against the audit: over all 16 segments these medians must equal
        # the audit's recorded first-waypoint errors for the same draw, to the digit.
        for key, z in subgoals.items():
            full = float((z - z_true).pow(2).sum(-1).median())
            print(f"  audit cross-check, draw {args.draw}, all 16 segments: {key:<10} median ẑ1 error {full:8.2f}")
            record(**{f"audit_check_z1_error_{key}_16seg": full})
    if args.rows_near_median is not None:
        # A 16-row panel does not read on a slide, and taking the first N rows is
        # how the 6-row panels came to overstate plain CEM's failure by 2.7x
        # (FINDINGS, "the six rows shown are not representative of their draw").
        #
        # The obvious fix — take the N segments individually closest to the median —
        # does NOT work, and was tried first: on draw 0 it picked rows whose plain-CEM
        # median was 29.44 against the draw's 51.80, understating the failure by 1.76x.
        # Picking rows near the median one at a time says nothing about where the
        # median of the chosen subset lands.
        #
        # So select on the quantity that actually has to be representative: the
        # subset's own median. With 16 segments there are at most C(16,8)=12870
        # subsets, so the best one is found exactly by enumeration rather than
        # approximated. Score per planner column k (the expert is a reference, not
        # a planner), normalised by that column's median so a panel carrying both
        # plain CEM and Hi-LeWM-C is representative of both despite their different
        # scales:
        #   primary   max_k |median(subset_k) - median_k| / median_k   (worst column)
        #   tie-break mean_k mean_i |err_k(i) - median_k| / median_k   (a tight crop)
        from itertools import combinations

        # torch's .median() returns the LOWER of the two middle values on an even
        # count; numpy averages them. Every median in the audit records and in
        # FINDINGS is torch's, and on this draw the two differ by a lot (51.80 vs
        # 84.84 for plain CEM, because the 8th and 9th sorted errors are 51.8 and
        # 117.9). The crop has to represent the number we quote, so the selection
        # uses torch's convention throughout.
        def lmed(x: np.ndarray) -> float:
            return float(np.sort(x)[(len(x) - 1) // 2])

        planners = [k for k in subgoals if k != "expert"]
        errs = {k: (subgoals[k] - z_true).pow(2).sum(-1).numpy() for k in planners}
        meds = {k: lmed(errs[k]) for k in planners}
        n_pick = args.rows_near_median
        if not 1 <= n_pick <= n_solve:
            raise SystemExit(f"--rows-near-median must be between 1 and {n_solve}, got {n_pick}")
        best = None
        for subset in combinations(range(n_solve), n_pick):
            idx = list(subset)
            devs = [abs(lmed(errs[k][idx]) - meds[k]) / max(meds[k], 1e-12) for k in planners]
            tight = float(np.mean([np.mean(np.abs(errs[k][idx] - meds[k]) / max(meds[k], 1e-12))
                                   for k in planners]))
            key = (max(devs), tight)
            if best is None or key < best[0]:
                best = (key, idx)
        (worst_dev, tightness), show = best
        args.rows = len(show)
        print(f"\n  row selection: {args.rows} of {n_solve} segments, chosen by exact search over "
              f"{math.comb(n_solve, n_pick)} subsets")
        print(f"    criterion: minimise max over {planners} of "
              f"|median(subset) - median(draw)| / median(draw)")
        print(f"    chosen segment indices: {show}   (worst column off by {worst_dev:.1%})")
        for k in planners:
            chosen = lmed(errs[k][show])
            print(f"    {k:<10} median over chosen {chosen:8.2f}   over all {n_solve} {meds[k]:8.2f}"
                  f"   ({abs(chosen - meds[k]) / max(meds[k], 1e-12):.1%} off)")
            record(**{f"selection_{k}_median_chosen": chosen, f"selection_{k}_median_all": meds[k]})
        record(selected_rows=show, selection_worst_deviation=worst_dev,
               selection_tightness=tightness,
               selection_criterion="exact search: minimise max_k |median(subset_k) - median_k| / median_k, "
                                   "tie-broken by mean normalised deviation of the chosen rows")
    else:
        show = slice(0, args.rows)
    z_t, z_true, z_goal = z_t[show], z_true[show], z_goal[show]
    subgoals = {k: v[show] for k, v in subgoals.items()}
    for key in ("expert", *[k for k in subgoals if k != "expert"]):
        err = (subgoals[key] - z_true).pow(2).sum(-1)
        print(f"  first-waypoint error, {key:<10} median {float(err.median()):8.2f}  (shown rows)")
        record(**{f"z1_error_{key}": err.tolist()})

    raw_t = torch.from_numpy(px_t[show]).permute(0, 3, 1, 2).float() / 255.0
    probe_module = probe_model_module()
    out_dir = Path(args.out_dir) if args.out_dir else repo / "analysis" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    names = list(PROBES) if args.probe == "both" else [args.probe]
    for name in names:
        decoder, dspec = load_decoder(repo / PROBES[name])
        print(f"\nprobe {name}: {dspec.describe()}  (stats: {decoder_stats_source()})")

        columns = ["frame t", "probe(z_t)", "probe(z_true)"] + [f"probe({k})" for k in subgoals] + ["probe(z_goal)"]
        panels = [raw_t] + [decode_latents(decoder, z) for z in (z_t, z_true, *subgoals.values(), z_goal)]
        reference = panels[2]  # probe(z_true): prediction error with probe blur divided out
        print(f"{'against probe(z_true)':>22}  {'PSNR':>7}  {'SSIM':>7}")
        scored = [(f"probe({k})", 3 + i) for i, k in enumerate(subgoals)] + [("probe(z_t)", 1)]
        for label, idx in scored:
            psnr = probe_module.compute_psnr(panels[idx], reference)
            ssim = probe_module.compute_ssim(panels[idx], reference)
            print(f"{label:>22}  {float(psnr):>7.2f}  {float(ssim):>7.4f}")
            record(**{f"{name}_{label}_psnr": float(psnr), f"{name}_{label}_ssim": float(ssim)})

        grid = torch.stack(panels, dim=1).reshape(-1, *raw_t.shape[1:])
        suffix = f"_d{args.goal_offset}" + (f"_draw{args.draw}" if args.draw is not None else "")
        suffix += f"_{args.rows}rows"   # a 16-row render once silently replaced a 6-row one
        suffix += "-nearmedian" if args.rows_near_median is not None else ""
        suffix += "_hilewmc" if args.with_empirical else ""
        path = out_dir / f"subgoals_{Path(args.checkpoint).stem}_{name}{suffix}.png"
        probe_module.save_panel(path, probe_module.make_grid(grid, nrow=len(panels), padding=2))
        print(f"  saved {path}  ({args.rows} rows x {len(panels)} cols: {', '.join(columns)})")
        record(headline=f"{spec.describe().split()[0]} d_l={d_l}: decoded subgoal panel ({name})",
               **{f"{name}_figure": str(path.relative_to(repo))})

    data.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--probe", default="phase_b", choices=["phase_a", "phase_b", "both"])
    p.add_argument("--rows", type=int, default=6)
    p.add_argument("--rows-near-median", type=int, default=None,
                   help="draw the N segments closest to the draw's median first-waypoint error "
                        "instead of the first --rows; for slide crops. Needs --draw.")
    p.add_argument("--frame-skip", type=int, default=5)
    p.add_argument("--horizon", type=int, default=2)
    add_budget_args(p)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--out-dir", default=None)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--draw", type=int, default=None,
                   help="show audit draw K: its segments and its solver seed (2000+K), solved over all 16")
    p.add_argument("--with-empirical", action="store_true",
                   help="add a Hi-LeWM-C column (EmpiricalMacroActionSolver) next to plain CEM")
    p.add_argument("--residual-scale", type=float, default=0.1, help="Hi-LeWM-C lambda_res")
    p.add_argument("--bank-size", type=int, default=4096, help="Hi-LeWM-C bank size")
    p.add_argument("--stage-sampling", default="sequence", choices=["sequence", "independent"])
    p.add_argument("--bank-seed", type=int, default=42, help="matches the audit's bank seed")
    return p


if __name__ == "__main__":
    _args = build_parser().parse_args()
    _tag = f"{Path(_args.checkpoint).stem}_{_args.probe}_d{_args.goal_offset}"
    if _args.rows_near_median is not None and _args.draw is None:
        raise SystemExit("--rows-near-median needs --draw: the median it selects against is "
                         "the draw's own, over all 16 solved segments")
    _tag += (f"_draw{_args.draw}" if _args.draw is not None else "") + ("_hilewmc" if _args.with_empirical else "")
    _tag += f"_near{_args.rows_near_median}" if _args.rows_near_median is not None else ""
    with recorded_run("render_subgoals", _args, tag=_tag):
        _code = run(_args)
    raise SystemExit(_code)
