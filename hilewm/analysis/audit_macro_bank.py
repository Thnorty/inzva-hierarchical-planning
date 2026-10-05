"""Is the Hi-LeWM-C bank really the expert's own contiguous actions?

**Rebuilt 2026-10-05.** The original script and its record
(``results/audit_macro_bank/20260926-232444_distrust_check.json``) were lost with
the rest of the teammate's working tree. This reimplements the checks
docs/FINDINGS.md lists for it (*The bank is genuinely the expert's contiguous
actions*) and produces a new record; it is not a recovered copy.

Why it exists: Hi-LeWM-C builds its search space from the dataset's ``action``
column, while plain CEM only touches those actions through a prior box the
solver never applies. A fault in that column, its normalisation or its
grouping would depress Hi-LeWM-C alone. So the bank the artifact builds is
compared against an independent encoding of the same spans:

1. bank latents from ``h_le_wm.planning.policies.build_empirical_macro_action_bank``
   against ``measure_support.encode_spans`` on the same rows -- two separate
   implementations of grouping, ordering and normalisation;
2. every span inside one episode;
3. every span strictly contiguous (``step_idx`` increments by one);
4. span length against the goal offset;
5. the action column: shape, NaN rows, range;
6. the grouping: primitive actions per model action, primitive steps per token.

Both use the eval's ``StandardScaler`` (``hilewm_local.build_action_scaler``)
and the shipped bank settings (``chunk_len`` 5, high horizon 2, action block 1).
Runs on CPU in about a minute.

Usage:
    export PYTHONPATH="$PWD/code:$PWD/analysis"
    python analysis/audit_macro_bank.py --dataset code/data/stablewm/pusht_expert_train.h5
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch

from hilewm_local import HDF5Columns, build_action_scaler, build_model
from hilewm_local.results import record, recorded_run
from measure_support import encode_spans

_REPO = Path(__file__).resolve().parent.parent
MAIN = "checkpoints/pusht/main/pusht_hi_lewm_epoch15_weights.ckpt"


def main(args: argparse.Namespace) -> int:
    from h_le_wm.planning.policies import build_empirical_macro_action_bank

    torch.set_grad_enabled(False)
    data = HDF5Columns(args.dataset)
    try:
        action = np.asarray(data.get_col_data("action"))
        episode = np.asarray(data.get_col_data("episode_idx"))
        step = np.asarray(data.get_col_data("step_idx"))
        scaler = build_action_scaler(data)["action"]
        model, spec = build_model(_REPO / args.checkpoint)
        print(spec.describe())

        nan_rows = int(np.isnan(action).any(axis=1).sum())
        print(f"\naction column: shape {action.shape}, NaN rows {nan_rows}, "
              f"range [{np.nanmin(action):.3f}, {np.nanmax(action):.3f}]")

        cfg = {"enabled": True, "num_sequences": args.num_sequences, "chunk_len": args.chunk_len,
               "encode_batch_size": 4096}
        bank = build_empirical_macro_action_bank(
            model=model, dataset=data, cfg=cfg, high_horizon=args.high_horizon, high_action_block=1,
            process={"action": scaler}, seed=args.seed)
        latents = bank["actions"]                       # (N, tokens, d_l)
        rows, goal_rows = bank["row_indices"], bank["goal_row_indices"]
        token_raw = int(bank["raw_macro_len"])           # primitive steps per macro token
        group = token_raw // args.chunk_len              # primitive actions per model action
        span = goal_rows - rows + 1
        goal_offset = args.high_horizon * token_raw
        print(f"bank: {latents.shape[0]} sequences x {latents.shape[1]} tokens x {latents.shape[2]} dims")
        print(f"grouping: {group} primitive actions per model action "
              f"({group * action.shape[1]} / {action.shape[1]}), {token_raw} primitive steps per macro token")

        ours = torch.stack([
            encode_spans(model, action, scaler, rows + j * token_raw, args.chunk_len, group)
            for j in range(latents.shape[1])], dim=1).numpy()
        diff = np.abs(ours - latents)
        magnitude = float(np.abs(latents).mean())
        norm = float(np.linalg.norm(latents, axis=-1).mean())

        same_episode = int(sum(episode[r] == episode[g] for r, g in zip(rows, goal_rows)))
        contiguous = int(sum(bool(np.all(np.diff(step[r:g + 1]) == 1)) for r, g in zip(rows, goal_rows)))
        n = len(rows)

        print(f"\n{'check':<46} result")
        print(f"{'bank vs independent encoding, max abs diff':<46} {diff.max():.1e}  "
              f"(mean |latent| {magnitude:.2f}, mean latent norm {norm:.2f})")
        print(f"{'spans inside a single episode':<46} {same_episode} / {n}")
        print(f"{'spans strictly contiguous (step_idx + 1)':<46} {contiguous} / {n}")
        print(f"{'span length vs goal offset':<46} {sorted(set(span.tolist()))} primitive steps "
              f"vs d = {goal_offset}")
        print(f"{'action column':<46} {action.shape}, {nan_rows} NaN rows, "
              f"range [{np.nanmin(action):.3f}, {np.nanmax(action):.3f}]")

        ok = (diff.max() < 1e-4 and same_episode == n and contiguous == n
              and set(span.tolist()) == {goal_offset} and nan_rows == 0)
        print(f"\nverdict: {'the bank is the expert contiguous actions' if ok else 'A CHECK FAILED'}")
        record(headline=f"bank max abs diff {diff.max():.1e}; {same_episode}/{n} in-episode; "
                        f"{contiguous}/{n} contiguous",
               passed=bool(ok), max_abs_diff=float(diff.max()), mean_abs_latent=magnitude,
               mean_latent_norm=norm, spans_in_episode=same_episode, spans_contiguous=contiguous,
               n_sequences=n, span_lengths=sorted(set(span.tolist())), goal_offset=goal_offset,
               action_shape=list(action.shape), action_nan_rows=nan_rows,
               action_range=[float(np.nanmin(action)), float(np.nanmax(action))],
               primitive_per_model_action=group, primitive_per_token=token_raw)
        return 0 if ok else 1
    finally:
        data.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", required=True)
    p.add_argument("--checkpoint", default=MAIN)
    p.add_argument("--num-sequences", type=int, default=256)
    p.add_argument("--chunk-len", type=int, default=5, help="shipped config default")
    p.add_argument("--high-horizon", type=int, default=2, help="the D50 matrix row")
    p.add_argument("--seed", type=int, default=42)
    return p


if __name__ == "__main__":
    _args = build_parser().parse_args()
    with recorded_run("audit_macro_bank", _args, tag="distrust_check"):
        _code = main(_args)
    raise SystemExit(_code)
