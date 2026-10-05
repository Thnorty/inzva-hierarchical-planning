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

## Findings live in docs/FINDINGS.md, not here

The code-reading notes, the findings that changed the plan and the open questions
that used to sit here were moved verbatim to `docs/FINDINGS.md` on 2026-09-21, and
corrected there since. **This file's copy was a stale 2026-09-19 snapshot until
2026-10-05**: it still asserted that the "unconstrained" CEM is box-bounded by data
quantiles, which FINDINGS retracted the same day (the box is computed, but
`CEMSolver` never reads it). Read FINDINGS for any claim about the code or the
results, `STATUS.md` for where things stand, and `docs/RECONSTRUCTION.md` for which
records were regenerated after the old working tree was lost.

## Gotchas

- **Low-level horizon.** The shipped `config/eval/hi_pusht.yaml` says 5; the authors'
  D50 matrix row and the diagnostics use 2; the difference is worth 34 points with
  oracle subgoals. Every eval passes the D50 row explicitly (`colab_setup.ipynb`
  cell 26). Set `planning.low.plan_config.horizon` in anything new.
- **Shipped eval config is not Table 5.** Take budgets from
  `analysis/hilewm_local/budgets.py`, keyed on the goal offset.
- **Copy the episode manifest after every Colab run.** A run without one can be
  quoted, never paired. Two have been lost this way.
- **The acting diagnostics run exactly `goal_offset_steps` steps** unless
  `run_diagnostics.py --max-steps` overrides it, which is half the paper's budget.
  Record any override.
- **The eval prints every episode outcome twice.** Deduplicate by `eval_index`.
- **±1 episode is run-to-run noise** on the GPU even under strict determinism.
- **Windows:** set `PYTHONUTF8=1`; the scripts print characters cp1252 cannot encode.

## Working rules for Claude Code

- **Read the code before changing it.** Start by exploring `code/` and summarizing the planner, bank construction, and VQ paths; do not assume the descriptions above match the implementation exactly.
- Do **not** retrain the high-level model. Do **not** edit the authors' original files in place; put our code in a separate directory (e.g. `analysis/`) and import from the artifact. If a change to their code is unavoidable, keep it minimal and note it.
- Log **every evaluation run** in one results table (`results/runs.csv`): date, git commit, checkpoint, planner variant, d, seed, n_episodes, success rate, config path. The table is regenerated from the Colab records by `analysis/rebuild_runs_csv.py`: add a new run's record under `results/colab/` and its entry to that script, never a hand-typed row.
- Fix and record random seeds. Report mean ± std over ≥3 seeds where budget allows; remember the noise level at 50 episodes.
- **Compute.** Since 2026-10-05 this project lives in `hilewm/` of the inzva
  `stable-worldmodel` repository, on a Windows machine. Every `analysis/` script runs
  locally on CPU in `hilewm/.venv` (setup in `README.md`), and reproduces the
  original Intel Mac numbers exactly. Anything that rolls out episodes needs the
  environment and a GPU, and goes to Colab (`docs/COLAB_PLAN.md`).
- Individual eval runs take ~5–58 min. **Ask before launching long or multi-seed GPU sweeps**; prefer a small smoke test first.
- Keep large files (checkpoints, datasets, decoded frames) out of git.
- Priorities if time is short: (1) diagnosis of unconstrained Hi-LeWM, (2) empirical-macro CEM comparison, (3) VQ comparison (can shrink to VQ-128 at d=75).
- When reporting a finding, say what was measured, how many episodes/seeds, and how it compares with the paper's number.

## Timeline

As planned on 2026-09-19. Where the work actually stands is `STATUS.md`.

- **Now → next week:** environment running, checkpoints staged, one baseline eval, an interim presentation (paper story + our research questions + plan; ideally one decoded-subgoal slide).
- **Weeks 1–2 after:** reproduction at d=50/75, build the diagnostics, oracle experiment.
- **Week 3:** empirical-macro and VQ comparisons under the same diagnostics.
- **Week 4:** extra seeds, figures, slides; keep as buffer.
