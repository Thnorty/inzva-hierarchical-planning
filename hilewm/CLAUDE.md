# CLAUDE.md — Hi-LeWM Subgoal Diagnosis Project

## What we are doing

We are analyzing the paper **"Mind the Gap: Promises and Pitfalls of Hierarchical Planning in LeWorldModel"** (Caselli et al., Univ. of Amsterdam, arXiv 2607.12547). We are **not training high-level models from scratch**: the authors released trained checkpoints, and we use them.

Our project has three parts:

1. **Diagnose** why the unconstrained high-level planner (Hi-LeWM with plain CEM) produces meaningless / poor subgoals.
2. **Compare** it against **empirical-macro CEM** (Hi-LeWM-C, the paper's support-constrained search) and the **VQ macro-action variants** (VQ-16, VQ-128).
3. **Present** the findings (an interim presentation next week, a final showcase ~4 weeks after that).

The paper already offers a hypothesis: unconstrained high-level CEM searches macro-actions **outside the support of training trajectories**, yielding subgoals that look good under the learned model's terminal cost but are poor control targets. Our job is to **test this directly** (measure it), not just restate it. Be ready for the hypothesis to be only partly right.

## Background (from the paper)

**LeWorldModel (LeWM):** JEPA-style latent world model (~18M params, latent dim d_z = 192) that plans with CEM directly over primitive actions toward a goal observation. Flat planner; degrades at long horizons.

**Hi-LeWM:** keeps the pretrained low-level LeWM **frozen** (encoder, low-level predictor p_lo, low-level action encoder) and adds two trainable high-level modules (12.5M trainable params; 30.5M total):

- **Macro-action encoder g:** transformer over a chunk of primitive actions between two waypoints → latent macro-action ℓ ∈ R^32 (d_ℓ = 32). 2 layers, 4 heads, model dim 192, max chunk length 15, [CLS] pooling.
- **High-level predictor φ:** transformer with adaptive layer norm; takes current waypoint latent z_t and macro-action ℓ_t and predicts the next waypoint latent ẑ. Depth 6, 16 heads, head dim 64, FF dim 2048. ℓ is projected from R^32 to R^192 before conditioning.
- **Training:** MSE on next-waypoint latent. Waypoints are sampled `random_sorted`, N = 5, span up to 15 steps. AdamW, lr 5e-5, batch 128, up to 15 epochs (VQ variant: 50 epochs).

**Test-time planning (two levels):**

1. High-level CEM searches macro-action sequences ℓ\_{1:hh}; roll φ forward; pick the sequence whose terminal prediction is closest to the goal latent: argmin ‖ẑ_hh − z_g‖².
2. The **first predicted subgoal** goes to the frozen low-level LeWM CEM planner, which optimizes primitive actions toward it. Only part of the low-level plan executes before replanning (receding-horizon MPC).
3. **Staged execution** (variant): commit to a sequence of subgoals over a longer interval instead of replanning the high level online.

**Empirical-macro CEM (Hi-LeWM-C):** build a bank B of latent macro-action sequences by sampling contiguous action spans from the _training_ action stream, chunking them, and encoding with g. Candidates are ξ = ξ_bank + λ_res·ε (ε ~ N(μ, Σ)); CEM refits **only the residual** distribution from elites; one zero-residual candidate per sampled anchor is included. Sequence-level bank sampling (preserves temporal correlation) gave the strongest staged results; independent per-stage sampling is the alternative.

**VQ macro-action encoder (Appendix B.5.2):** quantizes macro-action latents to a learned codebook (VQ-VAE style). Loss: L_high + λ_rec·L_rec + λ_commit·L_commit + λ_code·L_code, straight-through estimator. The action-chunk decoder is **training-only**. Codebook sizes 16 and 128. The paper notes a "separate discrete planning interface".

**CEM budgets (paper Table 5, high-level / low-level: samples, steps, top-k):**

- d=25: 900/20/10 and 300/30/150 (goal budget 50)
- d=50: 1500/40/10 and 900/30/150 (goal budget 100)
- d=75: 1200/60/10 and 1200/30/150 (goal budget 150)

## Reference numbers from the paper (PushT success %, goal offset d)

Treat as targets for sanity-checking our reproduction, not ground truth. Most are best-config-from-sweep values; Figure 3 numbers are averaged over 3 seeds; evaluation uses 50 episodes per run. **Flat LeWM values below are implied by the reported deltas, not quoted directly.**

| Method                             | d=50            | d=75            |
| ---------------------------------- | --------------- | --------------- |
| Flat LeWM                          | ~52.7 (implied) | ~18.0 (implied) |
| Hi-LeWM, online, unconstrained CEM | 38.7            | 15.3            |
| Hi-LeWM-C, online, empirical-macro | 48.7            | 32.7            |
| Hi-LeWM-C, staged                  | 64.0            | 22.0            |

Table 2 (representation sweep, best success %): continuous d*ℓ=32: 46 / 20; fixed stride d*ℓ=32: 42 / 20; fixed stride d_ℓ=8: 42 / 20; VQ-16: 38 / 20; VQ-128: 44 / 34 (columns d=50 / d=75). At d=25 flat LeWM is near saturation and hierarchy gives no meaningful advantage. Cube flat baseline: 65.3 / 52.0 / 53.3 at d=25/50/75.

**Caveats to keep in mind:** ~7-point standard error at 50 episodes and ~50% success; VQ was trained 50 vs 15 epochs (confound); the VQ table appears to be a single best configuration, so VQ-128 (34) vs empirical-macro online (32.7) at d=75 is effectively a tie.

## Repository / artifact layout

The authors' Zenodo artifact (doi:10.5281/zenodo.21353240) has:

```
code/          Hi-LeWM source, configs, scripts, tests, environments
checkpoints/   Hi-LeWM checkpoints + decoder probe weights
```

Checkpoints:

```
pusht/main/pusht_hi_lewm_epoch15_object.ckpt
cube/main/cube_hi_lewm_epoch15_object.ckpt
pusht/probes/phase_a/pusht_decoder_probe_phase_a.pt
pusht/probes/phase_b/pusht_decoder_probe_phase_b.pt
pusht/fixed_stride_dim32/   pusht/fixed_stride_dim8/
pusht/vq/vq16/              pusht/vq/vq128/
```

Object checkpoints (`*_object.ckpt`) are what the paper workflows use; training-weight checkpoints are kept where available. Each run dir has a sanitized `config.yaml`.

**Not included** (must be fetched): the flat LeWM baseline checkpoints (`bash scripts/setup_baseline_checkpoints.sh fetch-baselines`), the upstream LeWorldModel source (`git clone https://github.com/lucas-maes/le-wm.git third_party/lewm`, see `code/THIRD_PARTY_LEWM.md`), and datasets (`source scripts/setup_paper_datasets.sh --home "$STABLEWM_HOME"`). Pretrained LeWM checkpoints are also on the Hugging Face Hub (e.g. `quentinll/lewm-pusht`).

## Setup and commands

```bash
cd code
conda env create -f environment-gpu.yml     # use the GPU env for reproduction
conda activate lewm-gpu
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
export STABLEWM_HOME="$PWD/data/stablewm"

bash scripts/setup_checkpoints.sh \
  --checkpoint hierarchical/pusht/default_epoch15="$PWD/../checkpoints/pusht/main/pusht_hi_lewm_epoch15_object.ckpt" \
  --checkpoint hierarchical/cube/default_epoch15="$PWD/../checkpoints/cube/main/cube_hi_lewm_epoch15_object.ckpt" \
  --checkpoint probe/pusht/phase_a="$PWD/../checkpoints/pusht/probes/phase_a/pusht_decoder_probe_phase_a.pt" \
  --checkpoint probe/pusht/phase_b="$PWD/../checkpoints/pusht/probes/phase_b/pusht_decoder_probe_phase_b.pt"

bash scripts/validate_preflight.sh
bash scripts/run_pusht_smoke.sh --dry-run
bash scripts/run_paper_reproduction.sh
```

Outputs go under `$STABLEWM_HOME/repro/`; trained runs under `$STABLEWM_HOME/runs/`. Built on the `stable-worldmodel` library (environments, MPC solvers).

## Diagnosis plan (the core of our contribution)

Run on **PushT** (Cube is less diagnostic: its flat baseline doesn't collapse with horizon) at d ∈ {25, 50, 75}. Define "meaningless subgoal" operationally with these measurements:

1. **Visual check:** decode CEM-selected subgoal latents with the Phase A/B decoder probes; show next to encoded ground-truth expert waypoints.
2. **Support distance:** distance from each selected macro-action ℓ to its nearest neighbors among encoded training macro-actions (kNN / Mahalanobis); same for the predicted subgoal latent vs. real data latents.
3. **Model exploitation:** compare predicted terminal cost ‖ẑ_hh − z_g‖² with the _true_ progress toward the goal. Does predicted cost keep improving while real progress does not?
4. **Bad vs. unreachable subgoal:** after the low-level planner runs toward the subgoal, how close does the agent actually get (latent distance)?
5. **Oracle control:** feed true expert waypoint latents as subgoals (upper bound); add noise to measure low-level sensitivity.

Then evaluate **Hi-LeWM (plain CEM)**, **Hi-LeWM-C (empirical-macro)**, **VQ-128**, **VQ-16** with the _same metrics_, not only success rate. Key question: do the two fixes work by the same mechanism (keeping selected macro-actions in-support)?

## Verified by reading the code (2026-09-19, no runs yet)

- **Both checkpoint formats bundle the frozen low-level weights.** `model.encoder.*`,
  `model.action_encoder.*`, `model.low_predictor.*` are present alongside
  `high_predictor` and `latent_action_encoder`. `*_weights.ckpt` is a plain state
  dict; `*_object.ckpt` is a **pickled model object** referencing the old module
  name `hi_jepa`. Plain `torch.load` on an object checkpoint fails with
  `ModuleNotFoundError: No module named 'hi_jepa'` — import
  `h_le_wm.train.hierarchical` first, which registers the aliases
  (`h_le_wm/train/hierarchical.py:44-53`).
- **VQ checkpoints are evaluable; there is no separate discrete planner.**
  `rollout_high` quantizes inside the rollout (`h_le_wm/models/jepa.py:342`), so
  high-level CEM still searches continuous R^32 and each candidate is snapped to
  the nearest code. **Hypothesis to test:** with 16 codes many candidates collapse
  to the same code and therefore the *same* cost, so CEM elites are picked among
  ties. That is a mechanical explanation for VQ-128 > VQ-16 which does not involve
  the 50-vs-15 epoch confound. Cheap to measure: count unique costs per CEM step.
- **The empirical-macro bank is rebuilt at eval time, not shipped.**
  `build_empirical_macro_action_bank` (`h_le_wm/planning/policies.py:138-240`)
  encodes 4096 contiguous training action spans; `EmpiricalMacroActionSolver`
  (same file, from line 243) adds the residual. Datasets must be staged first.

## Findings that change the diagnosis plan

- **The "unconstrained" CEM is box-bounded by data quantiles.**
  `calibrate_latent_prior` (`h_le_wm/planning/policies.py:437-644`) sets the
  per-dimension search box to the 5th-95th percentile of 2048 encoded training
  chunks, +5% margin, clamped to ±3. So the claim to test is **not** "it searches
  anywhere" but "a per-dimension box does not capture the *shape* of the real
  macro-action distribution" (a 32-d box is mostly empty corners). The
  kNN / Mahalanobis measurement in diagnosis step 2 targets exactly this.
- **Cost/subgoal mismatch — a second candidate explanation.** With `horizon: 2`,
  `get_cost_high` scores the **last** predicted waypoint
  (`h_le_wm/models/jepa.py:469-471`) but the subgoal handed to the low level is
  the **first** (`h_le_wm/planning/policies.py:822`). Nothing forces the first
  waypoint to be a good control target. This is independent of out-of-support
  search and should be separated from it in the diagnosis.
- **Bank anchors are re-drawn every CEM step.** Only the residual mean/std are
  refit from elites (`h_le_wm/planning/policies.py:697-703`), so the empirical
  search never concentrates on good anchors.
- **Shipped eval config does NOT match paper Table 5.**
  `config/eval/hi_pusht.yaml` ships high CEM 900 samples / 20 steps / topk **30**
  and low 600 / 30 / topk **60**; Table 5 above says topk 10 / 150 and low 300
  samples. Reconcile before comparing against the reference numbers.
  `device: "cuda"` is hardcoded in the solver configs.

## Things NOT yet verified — check before relying on them

- Whether our reproduced numbers match the table above (within noise). Needs GPU.
- Whether VQ checkpoints load and run end-to-end — the code path exists but has
  not been executed.
- Whether `stable_worldmodel`, dataset staging, and baseline fetching work on
  Colab.

## Working rules for Claude Code

- **Read the code before changing it.** Start by exploring `code/` and summarizing the planner, bank construction, and VQ paths; do not assume the descriptions above match the implementation exactly.
- Do **not** retrain the high-level model. Do **not** edit the authors' original files in place; put our code in a separate directory (e.g. `analysis/`) and import from the artifact. If a change to their code is unavoidable, keep it minimal and note it.
- Log **every evaluation run** in one results table (`results/runs.csv`): date, git commit, checkpoint, planner variant, d, seed, n_episodes, success rate, config path.
- Fix and record random seeds. Report mean ± std over ≥3 seeds where budget allows; remember the noise level at 50 episodes.
- **Compute: Google Colab.** The local machine is an Intel Mac with no CUDA
  (`torch.cuda.is_available()` is False), so no real evaluation runs here. Code
  reading, checkpoint inspection, and analysis code are local; anything that
  plans or rolls out goes to Colab.
- Individual eval runs take ~5–58 min. **Ask before launching long or multi-seed GPU sweeps**; prefer a small smoke test first.
- Keep large files (checkpoints, datasets, decoded frames) out of git.
- Priorities if time is short: (1) diagnosis of unconstrained Hi-LeWM, (2) empirical-macro CEM comparison, (3) VQ comparison (can shrink to VQ-128 at d=75).
- When reporting a finding, say what was measured, how many episodes/seeds, and how it compares with the paper's number.

## Timeline

- **Now → next week:** environment running, checkpoints staged, one baseline eval, an interim presentation (paper story + our research questions + plan; ideally one decoded-subgoal slide).
- **Weeks 1–2 after:** reproduction at d=50/75, build the diagnostics, oracle experiment.
- **Week 3:** empirical-macro and VQ comparisons under the same diagnostics.
- **Week 4:** extra seeds, figures, slides; keep as buffer.
