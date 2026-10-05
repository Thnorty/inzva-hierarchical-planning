"""Does the high-level CEM leave the support of the training macro-actions?

This is diagnosis step 2, and after the retraction recorded in docs/FINDINGS.md it is
the main test of the paper's hypothesis: the search box the planner computes is
never enforced by `CEMSolver`, so the search really is unconstrained.

Everything is measured in the macro-action latent space R^d_l, against a
reference cloud of macro-actions encoded from the training set. The recipe
follows the artifact exactly (`calibrate_latent_prior` and the authors'
`build_macro_reference`): normalise actions with the eval-time `StandardScaler`,
take contiguous spans that do not cross an episode boundary, group `frame_skip`
primitive actions into one token, and encode with `model.encode_macro_actions`.

Three populations are compared against that cloud:

* **expert** -- macro-actions the expert actually took on the evaluated segments.
  In-support by construction, and also the right answer, so this is the scale
  everything else is read against.
* **cem** -- what the high-level CEM selects, running the artifact's real solver
  on real `z_init`/`z_goal` encoded from dataset frames.
* **prior** -- the solver's step-one draws, N(0, I), before any optimisation.
  Shows how much of the gap is the search and how much is where it starts.

Metrics per population: squared Mahalanobis distance to the reference
distribution, and Euclidean distance to the nearest reference neighbour.

**Mahalanobis² is whitened by each model's own reference covariance, so it is
comparable only within a checkpoint, against that checkpoint's expert row.**
Read the ratios, never the raw numbers, across checkpoints.

**VQ needs care.** `VQActionEncoder.forward` returns the *quantised* latent, so
the reference cloud and the expert row are codebook entries and their mutual
nearest-neighbour distance is 0 by construction. The solver, meanwhile, searches
continuous R^d_l and `rollout_high` quantises only inside the rollout, so its raw
output is not a codebook entry. Comparing the two directly is apples to oranges.
For VQ checkpoints we therefore also report `cem-q`, the selected vectors put
through `quantize_macro_actions_for_planning` -- what the predictor actually
consumes -- plus a code-usage comparison, which is the diagnostic that carries
information once every candidate is in-support by construction.

Usage:

    export PYTHONPATH="$PWD/code:$PWD/analysis"
    python analysis/measure_support.py \\
        --checkpoint checkpoints/pusht/main/pusht_hi_lewm_epoch15_weights.ckpt \\
        --dataset code/data/stablewm/pusht_expert_train.h5 \\
        --goal-offset 50
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

IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)


def partition_total(total: int, parts: int) -> list[int]:
    """Split a goal span into per-stage token counts, as the artifact does."""
    base, rem = divmod(total, parts)
    out = [base + (1 if i >= parts - rem and rem > 0 else 0) for i in range(parts)]
    if any(x <= 0 for x in out):
        raise ValueError(f"cannot split {total} tokens into {parts} positive spans")
    return out


def valid_starts(episode_ids, step_idx, span: int, n: int, rng) -> np.ndarray:
    """Chunk starts that stay inside one episode (the artifact's condition)."""
    bad = episode_ids[1:] != episode_ids[:-1]
    bad |= (step_idx[1:] - step_idx[:-1]) != 1
    transitions = span - 1
    csum = np.cumsum(np.concatenate(([0], bad.astype(np.int64))))
    window_bad = csum[transitions:] - csum[:-transitions]
    ok = np.nonzero(window_bad == 0)[0].astype(np.int64)
    if ok.size == 0:
        raise ValueError("no chunk start stays within an episode")
    return ok[rng.choice(ok.size, size=n, replace=ok.size < n)]


@torch.inference_mode()
def encode_spans(model, action, scaler, starts, span_tokens: int, group: int) -> torch.Tensor:
    """Encode raw action spans into macro-action latents."""
    raw_span = span_tokens * group
    raw = np.stack([action[s : s + raw_span] for s in starts], axis=0)
    b, length, dim = raw.shape
    norm = scaler.transform(raw.reshape(-1, dim)).reshape(b, span_tokens, dim * group)
    chunks = torch.from_numpy(norm.astype(np.float32))
    mask = torch.ones(chunks.shape[:2], dtype=torch.bool)
    return model.encode_macro_actions(chunks, mask)


@torch.inference_mode()
def encode_frames(model, pixels: np.ndarray) -> torch.Tensor:
    """Dataset frames (B, H, W, C) uint8 -> waypoint latents (B, D)."""
    x = torch.from_numpy(pixels).permute(0, 3, 1, 2).float().div_(255.0)
    x = (x - IMAGENET_MEAN) / IMAGENET_STD
    return model.encode({"pixels": x.unsqueeze(1)}, encode_actions=False)["emb"][:, -1]


def summarise(name: str, points: torch.Tensor, mean, inv_cov, cloud) -> dict:
    centered = points - mean
    md2 = torch.einsum("bi,ij,bj->b", centered, inv_cov, centered)
    nn = torch.cdist(points, cloud).min(dim=1).values
    return {
        "name": name,
        "n": int(points.shape[0]),
        "md2_median": float(md2.median()),
        "md2_p90": float(md2.quantile(0.90)),
        "nn_median": float(nn.median()),
        "nn_p90": float(nn.quantile(0.90)),
    }


def run(args) -> int:
    torch.set_grad_enabled(False)
    apply_cem_env_count_fix()
    record(budget=apply_budget(args))

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
    span_tokens = spans[0]
    if len(set(spans)) != 1:
        print(f"note       : uneven stage spans {spans}, using {span_tokens} for the reference")
    print(f"spans      : d={args.goal_offset} -> {goal_tok} tokens -> {spans} per stage "
          f"({span_tokens * group} primitive steps each, group={group})")

    rng = np.random.default_rng(args.seed)
    ref_starts = valid_starts(episode_ids, step_idx, span_tokens * group, args.num_reference, rng)
    cloud = encode_spans(model, action, scaler, ref_starts, span_tokens, group)
    mean = cloud.mean(dim=0)
    centered = cloud - mean
    cov = (centered.T @ centered) / max(1, cloud.shape[0] - 1)
    cov = cov + 1e-4 * torch.eye(d_l)
    inv_cov = torch.linalg.pinv(cov)
    print(f"reference  : {cloud.shape[0]} training macro-actions in R^{d_l}")

    # Evaluation segments: a full goal span inside one episode.
    total_raw = goal_tok * group
    seg_starts = valid_starts(episode_ids, step_idx, total_raw + 1, args.num_eval, rng)
    z_init = encode_frames(model, data.get_row_data(np.sort(seg_starts), ["pixels"])["pixels"])
    z_goal = encode_frames(model, data.get_row_data(np.sort(seg_starts) + total_raw, ["pixels"])["pixels"])

    # Expert macro-actions on those same segments, one per stage.
    expert = torch.cat(
        [
            encode_spans(model, action, scaler, np.sort(seg_starts) + offset * group, span_tokens, group)
            for offset in np.cumsum([0] + spans[:-1])
        ],
        dim=0,
    )

    CEMSolver = cem_solver_class()
    solver = CEMSolver(
        model=model, batch_size=args.batch_size, num_samples=args.num_samples,
        var_scale=1.0, n_steps=args.n_steps, topk=args.topk, device="cpu", seed=args.seed,
    )
    from gymnasium.spaces import Box

    solver.configure(
        action_space=Box(-1.0, 1.0, (args.num_eval, d_l), np.float32),
        n_envs=args.num_eval,
        config=SimpleNamespace(horizon=args.horizon, receding_horizon=1, action_block=1),
    )
    print(f"\nrunning CEM: {args.num_eval} segments x {args.num_samples} samples x {args.n_steps} steps")
    out = solver.solve({"z_init": z_init, "z_goal": z_goal, "planner_level": "high"})
    selected = torch.as_tensor(out["actions"]).reshape(-1, d_l)

    prior = torch.randn(args.num_eval * args.horizon, d_l, generator=torch.Generator().manual_seed(args.seed))

    populations = [("expert", expert), ("cem", selected)]
    if spec.is_vq:
        populations.append(("cem-q", model.quantize_macro_actions_for_planning(selected.unsqueeze(0)).squeeze(0)))
    populations.append(("prior", prior))

    print(f"\n{'population':>10}  {'n':>5}  {'Mahalanobis^2':>22}  {'nearest neighbour':>22}")
    print(f"{'':>10}  {'':>5}  {'median':>10} {'p90':>11}  {'median':>10} {'p90':>11}")
    rows = [summarise(name, points, mean, inv_cov, cloud) for name, points in populations]
    for r in rows:
        print(f"{r['name']:>10}  {r['n']:>5}  {r['md2_median']:>10.2f} {r['md2_p90']:>11.2f}  "
              f"{r['nn_median']:>10.3f} {r['nn_p90']:>11.3f}")

    base = rows[0]
    print("\nrelative to expert (median, comparable only within this checkpoint):")
    for r in rows[1:]:
        md_ratio = r["md2_median"] / base["md2_median"] if base["md2_median"] else float("nan")
        nn_ratio = r["nn_median"] / base["nn_median"] if base["nn_median"] else float("inf")
        nn_text = f"x{nn_ratio:.1f}" if math.isfinite(nn_ratio) else f"{r['nn_median']:.3f} vs 0"
        print(f"  {r['name']:>6}: Mahalanobis^2 x{md_ratio:.1f}, nearest neighbour {nn_text}")

    record(
        headline=(f"{spec.describe().split()[0]} d_l={d_l}: CEM/expert Mahalanobis² "
                  f"x{rows[1]['md2_median'] / base['md2_median']:.1f}"),
        populations=rows,
        spec=spec.describe(),
        num_reference=int(cloud.shape[0]),
        goal_offset=args.goal_offset,
    )

    if spec.is_vq:
        report_code_usage(model, expert, selected, cloud)

    data.close()
    return 0


def report_code_usage(model, expert, selected, cloud) -> None:
    """Once every candidate is in-support by construction, ask *which* code."""
    encoder = model.latent_action_encoder
    idx = {
        "reference": encoder.latents_to_codes(cloud),
        "expert": encoder.latents_to_codes(expert),
        "cem": encoder.latents_to_codes(model.quantize_macro_actions_for_planning(selected.unsqueeze(0)).squeeze(0)),
    }
    n_codes = int(encoder.num_codes)
    print(f"\ncode usage over {n_codes} codes:")
    print(f"{'population':>10}  {'distinct':>8}  {'perplexity':>10}  {'top code share':>14}")
    for name, codes in idx.items():
        counts = torch.bincount(codes.flatten(), minlength=n_codes).float()
        probs = counts / counts.sum()
        nz = probs[probs > 0]
        perplexity = float(torch.exp(-(nz * nz.log()).sum()))
        print(f"{name:>10}  {int((counts > 0).sum()):>8}  {perplexity:>10.1f}  {float(probs.max()):>13.1%}")

    ref_used = set(idx["reference"].flatten().tolist())
    cem_codes = idx["cem"].flatten().tolist()
    in_ref = sum(1 for c in cem_codes if c in ref_used) / max(1, len(cem_codes))
    print(f"\nCEM selections landing on a code the training data uses: {in_ref:.1%}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--frame-skip", type=int, default=5)
    p.add_argument("--horizon", type=int, default=2)
    p.add_argument("--num-reference", type=int, default=4096)
    p.add_argument("--num-eval", type=int, default=16)
    add_budget_args(p)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--seed", type=int, default=42)
    return p


if __name__ == "__main__":
    _args = build_parser().parse_args()
    with recorded_run("measure_support", _args, tag=Path(_args.checkpoint).stem):
        _code = run(_args)
    raise SystemExit(_code)
