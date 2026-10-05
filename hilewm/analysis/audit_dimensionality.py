"""Audit the dimensionality and support-distance claims.

Written after a review found that the numbers behind "the macro-actions live on
a ~5-dimensional manifold" came from an inline snippet that was never saved, so
the claim could not be re-checked. Everything that feeds a reported number now
lives here.

Four checks:

1. **Spectrum.** Full eigenvalue spectrum of the centered macro-action covariance
   (i.e. PCA), printed in full rather than summarised, so the reader can see
   where the cliff is instead of trusting one scalar.

2. **Estimator sensitivity.** "Effective dimension" is not one number. The
   participation ratio, spectral entropy, and variance thresholds disagree, and
   the disagreement is larger than the sampling error. Reporting one of them
   without saying which is how "~5" got written down when the spectral gap says
   7. Bootstrap confidence intervals are included to show the spread is in the
   estimator choice, not the sample.

3. **Reference overlap.** The expert population and the reference cloud are both
   drawn from `pusht_expert_train.h5`, which is also what the macro-action
   encoder was trained on. This re-runs the comparison with reference and expert
   taken from disjoint episodes. It cannot rule out the encoder having memorised
   the spans — there is no held-out split available — but it does test whether
   the reference statistics are overfit to the expert rows.

4. **Draw intervals.** Confidence ranges for the two headline ratios — support
   (CEM vs expert Mahalanobis²) and exploitation (expert vs CEM predicted
   terminal cost) — over independent segment draws. Both were first reported
   from one draw.

5. **Ridge and draw sensitivity.** The covariance gets a 1e-4 ridge before
   inversion, which is the same order as the smallest eigenvalues (6e-4), so the
   ridge could plausibly be manufacturing the large Mahalanobis values. It is
   not: at ridge 0 the ratio is if anything slightly larger. The draw sensitivity
   matters more — the reported x1019 was one draw, and ten draws put the median
   near x760 with a range of x517-x1081.

Usage:

    export PYTHONPATH="$PWD/code:$PWD/analysis"
    python analysis/audit_dimensionality.py --dataset code/data/stablewm/pusht_expert_train.h5
    python analysis/audit_dimensionality.py --dataset ... --checks spectrum,estimators
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from hilewm_local import HDF5Columns, build_action_scaler, build_model
from hilewm_local.patches import apply_cem_env_count_fix
from hilewm_local.budgets import add_budget_args, apply_budget
from hilewm_local.results import record, recorded_run
from hilewm_local.swm_compat import cem_solver_class

_REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("_measure_support", Path(__file__).with_name("measure_support.py"))
_ms = importlib.util.module_from_spec(_spec)
sys.modules["_measure_support"] = _ms
_spec.loader.exec_module(_ms)

ALL_CHECKPOINTS = {
    "d32": "checkpoints/pusht/main/pusht_hi_lewm_epoch15_weights.ckpt",
    "d8": "checkpoints/pusht/fixed_stride_dim8/pusht_hi_lewm_fixed_stride_dim8_epoch15_weights.ckpt",
    "vq128": "checkpoints/pusht/vq/vq128/pusht_hi_lewm_vq128_epoch50_weights.ckpt",
    "vq16": "checkpoints/pusht/vq/vq16/pusht_hi_lewm_vq16_epoch50_weights.ckpt",
}
# fixed_stride_dim32 differs from d32 only in waypoint strategy (fixed stride 5,
# 4 waypoints vs random_sorted, 5 waypoints) and from "d8" (= fixed_stride_dim8)
# only in d_l. It is the checkpoint that separates the two, which the d32 vs d8
# comparison had confounded.
ALL_CHECKPOINTS["fs32"] = (
    "checkpoints/pusht/fixed_stride_dim32/pusht_hi_lewm_fixed_stride_dim32_epoch15_weights.ckpt"
)
# Hi-LeWM-C: the main checkpoint searched by the empirical-macro solver.
ALL_CHECKPOINTS["hilewm_c"] = ALL_CHECKPOINTS["d32"]
EMPIRICAL_VARIANTS = {"hilewm_c"}
# The dimensionality checks only make sense for continuous latents.
DEFAULT_CHECKPOINTS = {k: ALL_CHECKPOINTS[k] for k in ("d32", "d8")}


def _require_d50(args) -> None:
    """The CEM checks hard-wire d=50's geometry: 10 tokens split evenly as 5 + 5.

    Table 5's other rows split unevenly with horizon 2 (d=25 -> 2 + 3,
    d=75 -> 7 + 8), and the per-stage reference below assumes equal spans. Refuse
    rather than silently mix geometries — that is the class of mistake this
    module's budget handling exists to prevent.
    """
    if args.goal_offset != 50:
        raise ValueError(f"the CEM checks support only d=50 for now, got d={args.goal_offset}")
SPAN_TOKENS, GROUP = 5, 5          # one macro-action = 5 tokens x 5 primitive actions = 25 steps
RAW_SPAN = SPAN_TOKENS * GROUP


class Corpus:
    """The dataset columns every check needs, loaded once."""

    def __init__(self, path: str | Path) -> None:
        self.data = HDF5Columns(path)
        self.scaler = build_action_scaler(self.data)["action"]
        self.action = np.asarray(self.data.get_col_data("action"))
        self.episode_ids = np.asarray(self.data.get_col_data("episode_idx"))
        self.step_idx = np.asarray(self.data.get_col_data("step_idx"))

    def starts(self, n: int, seed: int, span: int = RAW_SPAN) -> np.ndarray:
        return _ms.valid_starts(self.episode_ids, self.step_idx, span, n, np.random.default_rng(seed))

    def encode(self, model, starts: np.ndarray) -> torch.Tensor:
        return _ms.encode_spans(model, self.action, self.scaler, starts, SPAN_TOKENS, GROUP)

    def close(self) -> None:
        self.data.close()


def spectrum(z: torch.Tensor) -> torch.Tensor:
    """Eigenvalues of the centered covariance, descending. This is PCA."""
    centered = z - z.mean(0)
    cov = (centered.T @ centered) / max(1, z.shape[0] - 1)
    return torch.linalg.eigvalsh(cov).flip(0).clamp_min(0)


def estimators(ev: torch.Tensor) -> dict[str, float]:
    """Every defensible reading of "how many dimensions", side by side."""
    share = ev / ev.sum()
    nonzero = share[share > 0]
    cumulative = torch.cumsum(share, 0)
    return {
        "participation": float(1.0 / (share**2).sum()),
        "spectral_entropy": float(torch.exp(-(nonzero * nonzero.log()).sum())),
        "k_80": int((cumulative < 0.80).sum()) + 1,
        "k_90": int((cumulative < 0.90).sum()) + 1,
        "k_95": int((cumulative < 0.95).sum()) + 1,
        "k_99": int((cumulative < 0.99).sum()) + 1,
    }


def mahalanobis(points: torch.Tensor, mean: torch.Tensor, inv_cov: torch.Tensor) -> torch.Tensor:
    centered = points - mean
    return torch.einsum("bi,ij,bj->b", centered, inv_cov, centered)


def whitener(cloud: torch.Tensor, ridge: float) -> tuple[torch.Tensor, torch.Tensor]:
    mean = cloud.mean(0)
    centered = cloud - mean
    cov = (centered.T @ centered) / max(1, cloud.shape[0] - 1)
    return mean, torch.linalg.pinv(cov + ridge * torch.eye(cloud.shape[1]))


def check_spectrum(corpus: Corpus, checkpoints: dict[str, str], n: int, seed: int) -> None:
    print("=" * 78)
    print("1. FULL EIGENVALUE SPECTRUM (centered covariance = PCA)")
    print("=" * 78)
    for tag, path in checkpoints.items():
        model, spec = build_model(_REPO / path)
        ev = spectrum(corpus.encode(model, corpus.starts(n, seed)))
        share = ev / ev.sum()
        print(f"\n--- {tag}  d_l={spec.latent_action_dim}  n={n} ---")
        print(f"{'i':>3} {'eigenvalue':>12} {'share':>8} {'cumulative':>11}")
        for i, (e, f, c) in enumerate(zip(ev.tolist(), share.tolist(), torch.cumsum(share, 0).tolist()), 1):
            print(f"{i:>3} {e:>12.4e} {f:>7.2%} {c:>10.2%}")
        record(**{f"spectrum_{tag}": ev.tolist()})
        gap = (ev[:-1] / ev[1:]).argmax().item()
        print(f"  largest consecutive drop after dimension {gap + 1} "
              f"({ev[gap]:.3g} -> {ev[gap + 1]:.3g}, x{ev[gap] / ev[gap + 1]:.1f})")


def check_estimators(corpus: Corpus, checkpoints: dict[str, str], seed: int, boot: int) -> None:
    print("\n" + "=" * 78)
    print("2. ESTIMATOR SENSITIVITY — the spread is in the estimator, not the sample")
    print("=" * 78)
    print(f"{'model':>6} {'n':>7} {'particip.':>10} {'spec.ent':>9} {'k80':>5} {'k90':>5} {'k95':>5} {'k99':>5}")
    clouds = {}
    for tag, path in checkpoints.items():
        model, spec = build_model(_REPO / path)
        for n in (256, 1024, 4096, 16384):
            z = corpus.encode(model, corpus.starts(n, seed))
            if n == 4096:
                clouds[tag] = z
            e = estimators(spectrum(z))
            record(**{f"estimators_{tag}_n{n}": e})
            print(f"{tag:>6} {n:>7} {e['participation']:>10.2f} {e['spectral_entropy']:>9.2f} "
                  f"{e['k_80']:>5} {e['k_90']:>5} {e['k_95']:>5} {e['k_99']:>5}   (of {spec.latent_action_dim})")

    print(f"\nbootstrap 95% CI (n=4096, {boot} resamples):")
    for tag, z in clouds.items():
        gen = torch.Generator().manual_seed(7)
        collected: dict[str, list[float]] = {"participation": [], "spectral_entropy": [], "k_95": []}
        for _ in range(boot):
            idx = torch.randint(0, z.shape[0], (z.shape[0],), generator=gen)
            e = estimators(spectrum(z[idx]))
            for key in collected:
                collected[key].append(e[key])
        print(f"  --- {tag} ---")
        for key, values in collected.items():
            a = np.asarray(values, dtype=float)
            record(**{f"bootstrap_{tag}_{key}": [float(np.percentile(a, 2.5)), float(np.median(a)),
                                                  float(np.percentile(a, 97.5))]})
            print(f"    {key:<18} median {np.median(a):6.2f}   95% CI "
                  f"[{np.percentile(a, 2.5):.2f}, {np.percentile(a, 97.5):.2f}]")


def check_overlap(corpus: Corpus, checkpoints: dict[str, str], seed: int) -> None:
    from scipy.stats import chi2

    print("\n" + "=" * 78)
    print("3. REFERENCE OVERLAP — is the expert row in-sample for the reference?")
    print("=" * 78)
    episodes = np.unique(corpus.episode_ids)
    np.random.default_rng(0).shuffle(episodes)
    half = len(episodes) // 2
    mask_a = np.isin(corpus.episode_ids, episodes[:half])
    mask_b = np.isin(corpus.episode_ids, episodes[half:])

    def restricted(mask: np.ndarray, n: int, s: int) -> np.ndarray:
        pool = corpus.starts(n * 6, s)
        ok = np.array([x for x in pool if mask[x] and mask[x + RAW_SPAN - 1]], dtype=np.int64)
        if len(ok) < n:
            raise ValueError("not enough episode-restricted starts; raise the pool")
        return ok[:n]

    for tag, path in checkpoints.items():
        model, spec = build_model(_REPO / path)
        d = spec.latent_action_dim
        for label, ref_mask, exp_mask in (("overlapping (as measured)", None, None),
                                          ("disjoint episodes", mask_a, mask_b)):
            ref = corpus.starts(4096, seed) if ref_mask is None else restricted(ref_mask, 4096, seed)
            exp = corpus.starts(32, seed + 57) if exp_mask is None else restricted(exp_mask, 32, seed + 57)
            cloud = corpus.encode(model, ref)
            mean, inv_cov = whitener(cloud, 1e-4)
            e_med = float(mahalanobis(corpus.encode(model, exp), mean, inv_cov).median())
            prior = torch.randn(32, d, generator=torch.Generator().manual_seed(seed))
            p_med = float(mahalanobis(prior, mean, inv_cov).median())
            ref_chi2 = chi2.ppf(0.5, d)
            print(f"  {tag:>4} / {label:<26} expert MD² {e_med:7.2f}  "
                  f"(chi²({d}) median {ref_chi2:5.1f}, ratio {e_med / ref_chi2:4.2f})   "
                  f"prior/expert x{p_med / e_med:7.1f}")


def check_ridge_and_draws(corpus: Corpus, checkpoint: str, draws: int, seed: int, args) -> None:
    from scipy.stats import chi2

    print("\n" + "=" * 78)
    print("4. RIDGE AND DRAW SENSITIVITY OF THE HEADLINE RATIO")
    print("=" * 78)
    apply_cem_env_count_fix()
    model, spec = build_model(_REPO / checkpoint, with_encoder=True)
    d = spec.latent_action_dim
    CEMSolver = cem_solver_class()
    from gymnasium.spaces import Box

    def cem_selection(segments: np.ndarray, solver_seed: int) -> tuple[torch.Tensor, torch.Tensor]:
        z_init = _ms.encode_frames(model, corpus.data.get_row_data(segments, ["pixels"])["pixels"])
        z_goal = _ms.encode_frames(model, corpus.data.get_row_data(segments + 50, ["pixels"])["pixels"])
        expert = torch.cat([corpus.encode(model, segments + off * GROUP) for off in (0, SPAN_TOKENS)], 0)
        solver = CEMSolver(model=model, batch_size=4, num_samples=args.num_samples, var_scale=1.0,
                           n_steps=args.n_steps, topk=args.topk, device="cpu", seed=solver_seed)
        solver.configure(action_space=Box(-1.0, 1.0, (len(segments), d), np.float32), n_envs=len(segments),
                         config=SimpleNamespace(horizon=2, receding_horizon=1, action_block=1))
        out = solver.solve({"z_init": z_init, "z_goal": z_goal, "planner_level": "high"})
        return expert, torch.as_tensor(out["actions"]).reshape(-1, d)

    rng = np.random.default_rng(seed)
    cloud = corpus.encode(model, _ms.valid_starts(corpus.episode_ids, corpus.step_idx, RAW_SPAN, 4096, rng))
    segments = np.sort(_ms.valid_starts(corpus.episode_ids, corpus.step_idx, 51, 16, rng))
    expert, selected = cem_selection(segments, seed)
    prior = torch.randn(32, d, generator=torch.Generator().manual_seed(seed))

    print(f"\nridge sweep (smallest raw eigenvalue {spectrum(cloud)[-1]:.2e}):")
    print(f"{'ridge':>10} {'expert':>10} {'CEM':>12} {'prior':>12} {'CEM/expert':>12} {'CEM/prior':>11}")
    for ridge in (0.0, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1):
        mean, inv_cov = whitener(cloud, ridge)
        e, c, p = (float(mahalanobis(x, mean, inv_cov).median()) for x in (expert, selected, prior))
        print(f"{ridge:>10.0e} {e:>10.2f} {c:>12.1f} {p:>12.1f} {c / e:>12.1f} {c / p:>11.2f}")

    print(f"\n{draws} independent segment draws at ridge 1e-4:")
    mean, inv_cov = whitener(cloud, 1e-4)
    ratios, cem_values, expert_values = [], [], []
    for k in range(draws):
        seg = np.sort(_ms.valid_starts(corpus.episode_ids, corpus.step_idx, 51, 16,
                                       np.random.default_rng(1000 + k)))
        exp_k, sel_k = cem_selection(seg, 1000 + k)
        e = float(mahalanobis(exp_k, mean, inv_cov).median())
        c = float(mahalanobis(sel_k, mean, inv_cov).median())
        ratios.append(c / e); cem_values.append(c); expert_values.append(e)
        print(f"  draw {k}: expert {e:7.2f}  CEM {c:9.1f}  ratio x{c / e:7.1f}")

    r = np.asarray(ratios)
    print(f"\n  CEM/expert ratio: median x{np.median(r):.0f}, range x{r.min():.0f}-x{r.max():.0f}")
    print(f"  expert MD²      : median {np.median(expert_values):.2f}, "
          f"range {min(expert_values):.2f}-{max(expert_values):.2f}")
    print(f"  CEM MD²         : median {np.median(cem_values):.0f}, "
          f"range {min(cem_values):.0f}-{max(cem_values):.0f}")
    print(f"  reference-free  : CEM MD² / chi²({d}) median = x{np.median(cem_values) / chi2.ppf(0.5, d):.0f}")
    record(headline=f"support ratio median x{np.median(r):.0f} (x{r.min():.0f}-x{r.max():.0f}, {draws} draws)",
           support_ratio_draws=ratios, reference_free_ratio=float(np.median(cem_values) / chi2.ppf(0.5, d)))
    print("\n  The reference-free figure is the one to quote: it does not depend on how")
    print("  tight the expert sample happens to be on a given draw.")



def check_draw_intervals(corpus: Corpus, checkpoints: dict[str, str], draws: int, seed: int, args) -> None:
    """Confidence intervals for the headline ratios, over independent paired draws.

    Per draw, from one CEM solve on 16 segments:

    * support — CEM vs expert, both as squared Mahalanobis distance and as
      distance to the nearest training macro-action (1-NN);
    * exploitation — expert vs CEM predicted terminal cost, plus the share of
      segments where CEM "beats" the expert;
    * first-waypoint error ‖ẑ_1 − z_true‖² for the expert's macro-actions and for
      CEM's, against the real intermediate frame.

    Segments are seeded ``2000 + k`` and depend on nothing else, so draw *k* uses
    the same segments in every variant and every run — the runs are paired.

    The ``hilewm_c`` variant is Hi-LeWM-C: the main d_l=32 checkpoint searched by
    the artifact's own `EmpiricalMacroActionSolver` over a bank built by its own
    `build_empirical_macro_action_bank`, constructed exactly as
    `h_le_wm/eval/hierarchical.py::build_policy` does. The bank settings are the
    shipped `config/eval/hi_pusht.yaml` defaults unless overridden; the paper's
    Hi-LeWM-C numbers come from a sweep whose settings the artifact does not
    record, so ours may differ from theirs.
    """
    apply_cem_env_count_fix()
    from gymnasium.spaces import Box
    from h_le_wm.planning.policies import EmpiricalMacroActionSolver, build_empirical_macro_action_bank

    CEMSolver = cem_solver_class()
    print("\n" + "=" * 78)
    print(f"5. DRAW INTERVALS FOR THE HEADLINE RATIOS ({draws} draws x 16 segments)")
    print("=" * 78)
    first_raw = SPAN_TOKENS * GROUP          # the first subgoal sits 25 primitive steps in
    goal_raw = 2 * first_raw                 # d=50

    for tag, path in checkpoints.items():
        empirical = tag in EMPIRICAL_VARIANTS
        model, spec = build_model(_REPO / path, with_encoder=True)
        d = spec.latent_action_dim
        cloud = corpus.encode(model, corpus.starts(4096, seed))
        mean, inv_cov = whitener(cloud, 1e-4)

        bank = None
        if empirical:
            bank_cfg = {
                "enabled": True,
                "num_sequences": args.bank_size,
                "chunk_len": SPAN_TOKENS,
                "residual_scale": args.residual_scale,
                "min_residual_std": 1.0e-3,
                "return_top_candidates": 8,
                "encode_batch_size": 4096,
                "stage_sampling": args.stage_sampling,
                "seed": seed,
            }
            t0 = time.time()
            bank = build_empirical_macro_action_bank(
                model=model, dataset=corpus.data, cfg=bank_cfg, high_horizon=2, high_action_block=1,
                process={"action": corpus.scaler}, seed=seed,
            )
            record(**{f"empirical_config_{tag}": {
                **bank_cfg,
                "lambda_res": args.residual_scale,
                "bank_shape": list(bank["actions"].shape),
                "raw_macro_len": int(bank["raw_macro_len"]),
                "bank_build_seconds": round(time.time() - t0, 1),
                "source": "shipped config/eval/hi_pusht.yaml defaults unless overridden",
            }})
            print(f"\n  Hi-LeWM-C bank: {bank['actions'].shape[0]} sequences x 2 stages x {d} "
                  f"(raw_macro_len {int(bank['raw_macro_len'])}), lambda_res={args.residual_scale}, "
                  f"stage_sampling={args.stage_sampling}")

        solver_name = "EmpiricalMacroActionSolver" if empirical else "CEMSolver"
        print(f"\n--- {tag}  d_l={d}  ({solver_name}) ---")
        print(f"{'draw':>4} {'exp MD²':>8} {'CEM MD²':>9} {'supp x':>7} {'NN x':>6}  "
              f"{'exp cost':>9} {'CEM cost':>9} {'expl x':>7} {'beats':>6}  "
              f"{'ẑ1 exp':>7} {'ẑ1 CEM':>7}  {'solve s':>7}")
        cols = {k: [] for k in ("support", "support_nn", "exploitation", "cem_wins",
                                "z1_error_expert", "z1_error_cem", "solve_seconds")}
        for k in range(draws):
            seg = np.sort(_ms.valid_starts(corpus.episode_ids, corpus.step_idx, goal_raw + 1, 16,
                                           np.random.default_rng(2000 + k)))
            z_init = _ms.encode_frames(model, corpus.data.get_row_data(seg, ["pixels"])["pixels"])
            z_goal = _ms.encode_frames(model, corpus.data.get_row_data(seg + goal_raw, ["pixels"])["pixels"])
            z_true1 = _ms.encode_frames(model, corpus.data.get_row_data(seg + first_raw, ["pixels"])["pixels"])
            expert = torch.stack([corpus.encode(model, seg + off * GROUP) for off in (0, SPAN_TOKENS)], dim=1)

            if empirical:
                solver = EmpiricalMacroActionSolver(
                    model=model, macro_bank=bank["actions"], batch_size=4, num_samples=args.num_samples,
                    var_scale=1.0, n_steps=args.n_steps, topk=args.topk, device="cpu", seed=2000 + k,
                    residual_scale=args.residual_scale, min_residual_std=1.0e-3,
                    return_top_candidates=8, stage_sampling=args.stage_sampling,
                )
            else:
                solver = CEMSolver(model=model, batch_size=4, num_samples=args.num_samples, var_scale=1.0,
                                   n_steps=args.n_steps, topk=args.topk, device="cpu", seed=2000 + k)
            solver.configure(action_space=Box(-1.0, 1.0, (16, d), np.float32), n_envs=16,
                             config=SimpleNamespace(horizon=2, receding_horizon=1, action_block=1))
            t0 = time.time()
            out = solver.solve({"z_init": z_init, "z_goal": z_goal, "planner_level": "high"})
            solve_s = time.time() - t0
            selected = torch.as_tensor(out["actions"]).reshape(16, 2, d)

            # Support: quantise first where the rollout would, so VQ stays comparable.
            def flat(x):
                y = model.quantize_macro_actions_for_planning(x.reshape(1, -1, d)).squeeze(0) if spec.is_vq \
                    else x.reshape(-1, d)
                return y.reshape(-1, d)

            e_md = float(mahalanobis(flat(expert), mean, inv_cov).median())
            c_md = float(mahalanobis(flat(selected), mean, inv_cov).median())
            e_nn = float(torch.cdist(flat(expert), cloud).min(dim=1).values.median())
            c_nn = float(torch.cdist(flat(selected), cloud).min(dim=1).values.median())

            # Exploitation: the expert's own actions reach z_goal, so their cost is the floor.
            e_roll = model.rollout_high(z_init, expert)[:, 0]
            c_roll = model.rollout_high(z_init, selected)[:, 0]
            e_cost = (e_roll[:, -1] - z_goal).pow(2).sum(-1)
            c_cost = (c_roll[:, -1] - z_goal).pow(2).sum(-1)
            e_med, c_med = float(e_cost.median()), float(c_cost.median())
            won = float((c_cost < e_cost).float().mean())

            # First waypoint — the subgoal actually handed to the low level.
            z1_e = float((e_roll[:, 0] - z_true1).pow(2).sum(-1).median())
            z1_c = float((c_roll[:, 0] - z_true1).pow(2).sum(-1).median())

            nn_ratio = c_nn / e_nn if e_nn > 0 else float("inf")
            for key, value in (("support", c_md / e_md), ("support_nn", nn_ratio),
                               ("exploitation", e_med / c_med), ("cem_wins", won),
                               ("z1_error_expert", z1_e), ("z1_error_cem", z1_c),
                               ("solve_seconds", solve_s)):
                cols[key].append(value)
            record(**{f"draws_{tag}": dict(cols)})
            print(f"{k:>4} {e_md:>8.2f} {c_md:>9.1f} {c_md / e_md:>6.1f}x {nn_ratio:>5.1f}x  "
                  f"{e_med:>9.2f} {c_med:>9.2f} {e_med / c_med:>6.1f}x {won:>6.0%}  "
                  f"{z1_e:>7.2f} {z1_c:>7.2f}  {solve_s:>7.1f}")

        for name, key, pct in (("support ratio (MD²)", "support", False),
                               ("support ratio (1-NN)", "support_nn", False),
                               ("exploitation ratio", "exploitation", False),
                               ("segments CEM wins", "cem_wins", True),
                               ("ẑ1 error, expert", "z1_error_expert", None),
                               ("ẑ1 error, CEM", "z1_error_cem", None)):
            a = np.asarray(cols[key], dtype=float)
            fmt = (lambda v: f"{v:.0%}") if pct else (lambda v: f"{v:.2f}") if pct is None else (lambda v: f"x{v:.1f}")
            print(f"  {name:<22} median {fmt(np.median(a)):>8}   range {fmt(a.min())}-{fmt(a.max())}")
        print(f"  solve time per draw    median {np.median(cols['solve_seconds']):.0f}s")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", required=True)
    p.add_argument("--checks", default="spectrum,estimators,overlap,ridge",
                   help="comma-separated subset of spectrum,estimators,overlap,ridge,draws")
    p.add_argument("--n-reference", type=int, default=4096)
    p.add_argument("--draws", type=int, default=10, help="segment draws for the ridge check")
    p.add_argument("--bootstrap", type=int, default=300)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--variants", default="d32,d8",
                   help=f"checkpoints for the draws check, comma-separated from {sorted(ALL_CHECKPOINTS)}")
    add_budget_args(p)
    p.add_argument("--residual-scale", type=float, default=0.1,
                   help="Hi-LeWM-C lambda_res (shipped default 0.1)")
    p.add_argument("--bank-size", type=int, default=4096,
                   help="Hi-LeWM-C empirical bank size (shipped default 4096)")
    p.add_argument("--stage-sampling", default="sequence", choices=["sequence", "independent"],
                   help="Hi-LeWM-C bank sampling (shipped default sequence)")
    return p


def main(args) -> int:
    torch.set_grad_enabled(False)
    wanted = {c.strip() for c in args.checks.split(",") if c.strip()}
    variants = {k.strip(): ALL_CHECKPOINTS[k.strip()] for k in args.variants.split(",") if k.strip()}
    # The geometry checks need continuous latents and a checkpoint of their own.
    geometric = {k: v for k, v in variants.items() if k not in EMPIRICAL_VARIANTS and not k.startswith("vq")}
    corpus = Corpus(args.dataset)
    try:
        if "spectrum" in wanted:
            check_spectrum(corpus, geometric, args.n_reference, args.seed)
        if "estimators" in wanted:
            check_estimators(corpus, geometric, args.seed, args.bootstrap)
        if "overlap" in wanted:
            check_overlap(corpus, geometric, args.seed)
        if "ridge" in wanted:
            _require_d50(args)
            record(budget=apply_budget(args))
            check_ridge_and_draws(corpus, ALL_CHECKPOINTS["d32"], args.draws, args.seed, args)
        if "draws" in wanted:
            _require_d50(args)
            record(budget=apply_budget(args))
            check_draw_intervals(corpus, variants, args.draws, args.seed, args)
    finally:
        corpus.close()
    return 0


if __name__ == "__main__":
    _args = build_parser().parse_args()
    _tag = _args.checks.replace(",", "+") + "_" + _args.variants.replace(",", "+")
    if "hilewm_c" in _args.variants:
        _tag += f"_lam{_args.residual_scale:g}"   # keep a lambda_res sweep's records apart
    with recorded_run("audit_dimensionality", _args, tag=f"{_tag}_d{_args.goal_offset}"):
        _code = main(_args)
    raise SystemExit(_code)
