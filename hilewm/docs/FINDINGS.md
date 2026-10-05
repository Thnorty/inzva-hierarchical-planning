# Findings — Hi-LeWM subgoal diagnosis

The evidence log. Moved verbatim from `CLAUDE.md` on 2026-09-21, when that file
had grown to 717 lines of which 390 were results. Nothing below was rewritten
in the move; corrections are marked in place where they were made, and
summarised in the changelog.

Every number here should trace to a file under `results/` — see
`results/README.md`. Numbers from before 2026-09-21 that ran in the foreground
left no log; `results/backfill/2026-09-19_session/MANIFEST.md` lists them and
the command that regenerates each. **Regenerate before quoting.**

> **Reconstruction, 2026-10-05.** The working tree behind this file was deleted;
> what survived was merged into the inzva `stable-worldmodel` repository as
> `hilewm/`. Most records this file cites have been regenerated there, by the same
> scripts on the same data, and most reproduce to the digit. Where a cited record
> was replaced, a bracketed note beside its path names the new one. The
> backfill `MANIFEST.md` mentioned above is lost; every number it covered was
> later superseded by a recorded measurement. **`docs/RECONSTRUCTION.md` is the
> full account**, including the five comparisons whose numbers moved and the
> few numbers that now rest on this text alone.

> **Update 2026-09-21, later:** the headline ratios — support, exploitation, and
> CEM win rate, for all four variants — have been **re-measured at the paper
> budget**; see *Headline ratios at the paper budget* below, which supersedes
> every earlier value of those three quantities. The caveat that follows still
> applies to the rest: the single-draw per-variant tables (subgoal quality,
> realism, reachability), the VQ cost-tie counts, and the decoded panels.
>
> **⚠️ Budget caveat, 2026-09-21 — applies to every CEM-derived number below
> unless marked as paper-budget.**
> All measurements that run the high-level CEM used **20 iterations**. The
> paper's d=50 budget (Table 5), and the authors' own d=50 diagnostics, use
> **40**. The scripts took 1500 samples from Table 5's d=50 row and 20
> iterations from the shipped `hi_pusht.yaml`, whose high-level settings match
> d=25. The reachability test likewise used a low-level budget of 300/20/30
> against the paper's 900/30/150. With half the iterations CEM optimises less,
> so the support-distance and exploitation figures are **probably
> underestimates** — but that is a guess until re-measured. Budgets now come from
> `analysis/hilewm_local/budgets.py`, keyed on the goal offset, and every record
> in `results/` says which budget it used.
>
> **Unaffected**, because no CEM is involved: the eigenvalue spectra and
> dimensionality estimates, codebook geometry, every expert-row baseline, and the
> two code defects (the `CEMSolver` env count, the unenforced box).

## Changelog of corrections

| date | what changed | why |
| --- | --- | --- |
| 2026-09-19 | **Retracted** "the unconstrained CEM is box-bounded by data quantiles" | `CEMSolver` never reads the box; measured 74% of candidates fall outside it unclipped |
| 2026-09-19 | d_l=8 in-support explanation changed from "unit-scale latents" to "covariance spectrum" | scales measured comparable; the spectrum is what differs |
| 2026-09-19 | VQ support rows re-measured with `cem-q` | first run compared raw continuous output against a quantised reference |
| 2026-09-21 | support ratio x1019 -> **x759** (x517-x1081 over 10 draws); reference-free **x611** | x1019 was a single draw near the top of the range |
| 2026-09-21 | "~5 dimensions" -> **5-7, depending on estimator** | "5" was the participation ratio, the lowest of several estimators, quoted without naming it |
| 2026-09-21 | "27 / 3 empty directions" -> **25 / 1** | the old counts subtracted a soft estimate from the ambient dimension |
| 2026-09-21 | exploitation (d32) x15.9 / 94% -> **median x5.4 (x0.7-x10.6) / 78% (62-88%)** | single draw with an unusually high expert cost (34.4; the 10 audit draws ranged 9.9-27.5) |
| 2026-09-21 | exploitation (d8) x5.9 / 81% -> **median x4.3 (x1.8-x8.8) / 75% (62-81%)** | single draw |
| 2026-09-21 | d_l=8 support x1.3 -> **median x1.6 (x1.1-x2.1)** | single draw at the low end; still essentially in-support |
| 2026-09-21 | **Withdrawn:** "restricting the search reduces exploitation monotonically (15.9 -> 5.9 -> 5.7 -> 1.8)" | the d32 and d8 intervals overlap almost entirely, and the VQ values are still single draws. Not established |
| 2026-09-21 | **All CEM-derived numbers flagged**: measured at 20 high-level iterations, not d=50's 40 | budget assembled from two sources that disagree; see the banner above. Re-running at the paper budget |
| 2026-09-21 | Headline ratios re-measured at the paper budget, all four variants, 10 paired draws: d32 exploitation **x9.5**, support **x794**; d8 x3.9 / x1.5; VQ-128 x3.6; VQ-16 x2.2 | the 20-iteration values under-stated d32 badly: doubling the iterations raised its exploitation in 9 of 10 paired draws (p=0.02) |
| 2026-09-21 | **Retracted:** "exploitation is largely decoupled from support; d32 and d8 exploit by indistinguishable amounts" | an artefact of the half budget. At 40 iterations d32 exploits more than d8 on the **same segments in 10 of 10 draws** (p=0.002, median x2.45) |
| 2026-09-22 | Geometry table: d32 "8 dims above 0.4, **25** below" -> **7 before the largest spectral gap, 25 after** (or 8 / 24 by the 0.4 threshold) | the old row mixed two definitions and summed to 33 for a 32-d latent. The "25 near-empty" figure holds under the gap definition, which is now named |
| 2026-09-22 | **fixed_stride_dim32 measured**: "d8" is fixed_stride_dim8, so d32 vs d8 had changed d_l *and* waypoint strategy. fs32 separates them: **support distance is a d_l effect** (fs32 vs d8 10/10, p=0.002; d32 vs fs32 no difference), while the **exploitation gap cannot be attributed to either** (8/10, p=0.11 both ways) | see *fixed_stride_dim32* below |
| 2026-09-22 | **Qualified:** "leaving the support amplifies exploitation". The across-model evidence (d32 vs d8, 10/10) is confounded and fs32 does not isolate support as the cause; the within-model manipulations — lambda_res, CEM budget — remain the evidence | fs32 is as far out of support as d32 yet exploits no more than d8 detectably |
| 2026-09-22 | lambda_res sweep (0.05-1.0, 6 paired draws): "Hi-LeWM-C does not exploit" **holds only for lambda_res <= 0.1**; exploitation crosses x1 between 0.1 and 0.3. It stays far below plain CEM at every value, and its subgoals beat plain CEM's at every value | the lambda_res caveat, now measured; see *lambda_res sweep* below |
| 2026-09-22 | **Hi-LeWM-C measured** (first time), paired with plain CEM on the same checkpoint and segments: exploitation **x0.83** vs x9.51, subgoal error 22.1 vs 76.4, 10 of 10 draws on every metric | the project's central comparison; see *Hi-LeWM-C vs plain CEM* below |
| 2026-09-24 | **Axis 2 re-measured at the paper budget**, five variants (Hi-LeWM-C added) x 6 paired draws, with reachability at 900/30/150 instead of 300/20/30. Superseded the single-draw axis-2 tables. Headline: achieved/achievable subgoal error is **x0.94 / x1.02 for VQ-128 / VQ-16 but x18.64 for d32** — the VQ planners are at their representation's ceiling, the continuous ones are not | the project's central question ("do the two fixes work by the same mechanism?") answered: **no** — both cut exploitation, only Hi-LeWM-C keeps the accuracy ceiling. See *Axis 2 at the paper budget* |
| 2026-09-24 | **Retracted:** reachability at 20 iterations put d32 at relative 0.093 and d8 at 0.088. At the paper budget d32 is 0.08 and d8 is 0.08 — they tie (3 of 6, p=1.0) — while Hi-LeWM-C and both VQ variants sit at 0.02-0.03. The split is constrained-vs-unconstrained search, **not** in-support-vs-out-of-support | d8 is in support and still produces hard-to-reach subgoals |
| 2026-09-24 | "Quantisation buys robustness by destroying accuracy" (single draw, ~4x) **confirmed and strengthened** at 6 draws: VQ's accuracy floor is ~8x the continuous variants' (118.90 / 130.24 vs 15.16 / 16.27) and its achievable subgoal ~9-12x (47.14 / 60.25 vs 5.20 / 5.73) | STATUS's "do not present the exploitation-vs-accuracy trade-off as established" can be lifted |
| 2026-09-24 | **Resolved:** the horizon-2 cost/subgoal mismatch is not real. At n=64 over 4 draws the correlation is **Spearman +0.595 (+0.566 to +0.652), significant in 4 of 4** — the objective is consistently aligned, so this candidate explanation is closed | it stood open at corr=+0.425, n=16, underpowered. See *The horizon-2 cost/subgoal mismatch is not real* |
| 2026-09-24 | `measure_subgoal` now reports **Spearman** alongside Pearson, with an n-dependent significance threshold | both quantities are heavy-tailed; draw 1 above gives Spearman +0.652 against Pearson +0.457 |
| 2026-09-21 | **Partly restored, qualified:** restricting the search reduces exploitation | not a smooth ladder: d32 > {d8, VQ-128} > VQ-16 is significant at each end (p<=0.02), but d8 and VQ-128 tie (5 of 10, p=1.0) |
| 2026-10-01 | **Qualified:** "oracle beats the deployed planner by +34.0 / +36.0 points". The oracle comes from the acting diagnostics, which execute **staged**, while the planner rows replan online every 5 steps, so those rows vary subgoal source *and* execution mode. The matched subgoal effect is **+16.0, p = 0.152** | see *Qualified: the +34 mixes the subgoals with the execution mode* |
| 2026-10-01 | **Resolved:** the +34 decomposes into **+22.0 subgoals (p = 0.035)** and **+12.0 execution mode (p = 0.21)**, which sum to it exactly. The subgoal term is now attributed *and* significant at one seed, against +16.0 / p = 0.152 for its 50-step version | `generated_subgoal_acting --max-steps 100` reached 48.0 %, matching the oracle on execution, horizons, budget and episodes. See *Resolved: the +34 is +22 subgoals and +12 execution mode* |
| 2026-10-01 | **Diagnosis step 4 answered in the environment:** the model's subgoals are *wrong*, not merely hard. Failed episodes reach progress **0.76** under the expert's subgoals and **0.12** under the model's; a high-level failure ends 0.811 from the expert's path, a low-level one 0.138 | see *Diagnosis step 4, answered in the environment* |
| 2026-10-01 | **Qualified before publishing:** the off-path / stopped-short / reached-the-end split is threshold-dependent. Generated and oracle failures are indistinguishable at a 0.10 cut and separate at 0.25 and 0.50; the low-horizon contrast survives all three. The reading now rests on the threshold-free `progress` and nearest-state distance | a sensitivity sweep caught it before it reached a slide; the script reports the split at three thresholds by default |
| 2026-10-01 | **Withdrawn within the session:** a first version of the row above blamed a low-level horizon mismatch (eval config 5, diagnostics 2) and put 34 points on it. Wrong — `colab_hi.ipynb` cell 26 passes the authors' `D50` matrix row, which sets `planning.low.plan_config.horizon=2`, on every eval command, so all four runs were matched at 2 | the config file was read in place of the recorded command; FINDINGS' own provenance paragraph for the 36.0 % run already said "low horizon 2" |
| 2026-10-05 | **Records regenerated after the working tree was lost.** Every comparison whose manifests survived reproduces to the digit. Five used the first 50-step oracle run (30/50), whose manifest is lost; regenerated from its 29/50 rerun they move by one discordant pair each (e.g. low horizon 5 -> 2: +34.0 / p = 0.0005 becomes **+32.0 / p = 0.0015**), and none loses significance | see `docs/RECONSTRUCTION.md`, *The first oracle run*. Quote the regenerated values, which a reader can check |
| 2026-10-05 | **Staged Hi-LeWM-C written up: 46.0 %, against the paper's 64.0.** The run finished on 2026-10-01 and was logged, but never entered here | see *Staged Hi-LeWM-C: 46.0 %, not 64.0* |

## Contents

1. Verified by reading the code
2. Findings that change the diagnosis plan
3. Measured results — support distance, the d_l=32/d_l=8 mechanism, VQ, axis 2,
   the four-variant comparison, decoded subgoals, synthesis
4. Things not yet verified

## Verified by reading the code (2026-09-19, no runs yet)

- **Both checkpoint formats bundle the frozen low-level weights.** `model.encoder.*`,
  `model.action_encoder.*`, `model.low_predictor.*` are present alongside
  `high_predictor` and `latent_action_encoder`. `*_weights.ckpt` is a plain state
  dict; `*_object.ckpt` is a **pickled model object** referencing the old module
  name `hi_jepa`. Plain `torch.load` on an object checkpoint fails with
  `ModuleNotFoundError: No module named 'hi_jepa'` — import
  `h_le_wm.train.hierarchical` first, which registers the aliases
  (`h_le_wm/train/hierarchical.py:44-53`).
- **VQ checkpoints load; there is no separate discrete planner.**
  `rollout_high` quantizes inside the rollout (`h_le_wm/models/jepa.py:342`), so
  high-level CEM still searches a continuous space and each candidate is snapped
  to the nearest code. Verified 2026-09-19 by `torch.load` on the `*_weights.ckpt`
  files (a plain Lightning state dict — no `stable_worldmodel` needed): all three
  PushT checkpoints load, module groups as expected (encoder 198, high_predictor
  81, latent_action_encoder 30 continuous / 35 VQ tensors).
- **The VQ variants use d_l = 16, not 32 — a second confound.**
  `latent_action_encoder.quantizer.codebook.weight` is (16, 16) for VQ-16 and
  (128, 16) for VQ-128; `latent_action_encoder.output_proj.weight` is (16, 192)
  for both, vs (32, 192) for the main continuous checkpoint. (fixed_stride_dim32
  is 32, fixed_stride_dim8 is 8, as their names say.) So VQ-vs-continuous in
  Table 2 changes **two** things, not one: 50 vs 15 epochs *and* half the
  macro-action latent dim. **VQ-16 vs VQ-128 is the clean comparison** — same
  d_l, same epochs, only the code count differs.
- **Tie hypothesis, now quantitative.** The eval config uses `horizon: 2`,
  `action_block: 1`, so one candidate is 2 macro tokens and its cost depends only
  on the quantized pair. VQ-16 can produce at most 16^2 = 256 distinct sequences
  against 900-1500 CEM samples (3.5-5.9 samples per distinct sequence), so elites
  are largely picked among ties; VQ-128 reaches 128^2 = 16384, far above the
  sample count, and ties essentially vanish. A mechanical explanation for
  VQ-128 > VQ-16 that needs neither confound. Cheap to measure: count unique
  costs per CEM step.
- **Tie hypothesis, measured 2026-09-19** (local CPU via `analysis/hilewm_local`,
  no environment, seed 0, 1500 candidates, horizon 2). Candidates were drawn from
  N(0, I), **not** from the planner's calibrated prior, so read the ordering
  rather than the absolute counts; redo this against the real prior once the
  dataset is staged.

  | checkpoint | distinct costs / 1500 | candidates per cost |
  | --- | --- | --- |
  | continuous d_l=32 | 1500 | 1.0 |
  | fixed stride d_l=8 | 1500 | 1.0 |
  | VQ-128 | 590 | 2.5 |
  | VQ-16 | 63 | 23.8 |

  Both VQ numbers sit far below their combinatorial ceilings (256 and 16384)
  because codebook usage is concentrated. Under 200k random queries VQ-16 has
  perplexity 5.2 (~5 effective codes out of 16) and VQ-128 has 24.9 (~25 out of
  128, with 17 codes never nearest, one code of norm 0.047, and a nearest-neighbour
  distance of 0.048 between two codes). So **VQ-128 is itself partially
  collapsed** — it is 5x richer than VQ-16 in practice, not 8x as the code counts
  suggest. The codebook geometry is distribution-independent and therefore solid;
  the perplexities are not.
- **Tie hypothesis under the real CEM, measured 2026-09-19.** Static draws
  understate it badly. Running the artifact's own
  `stable_worldmodel.solver.cem.CEMSolver` over `get_cost_high` locally
  (`analysis/measure_high_cem.py`, 1500 samples, 20 steps, horizon 2, topk 10,
  seed 42, ~10 s per run on CPU):

  | checkpoint | distinct costs at step 1 | mean candidates per distinct cost |
  | --- | --- | --- |
  | continuous d_l=32 | 1500 / 1500 | 1.0 |
  | fixed stride d_l=8 | 1500 / 1500 | 1.2 |
  | VQ-128 | 572 / 1500 | 17.5 |
  | VQ-16 | 69 / 1500 | 101.7 |

  It compounds as CEM converges: VQ-16 goes 69 -> 52 -> 36 distinct costs over
  the first three steps and reaches **5 distinct costs among 1500 candidates** by
  step 20, so the top-10 elites are drawn from ties almost entirely at random.
  VQ-128 is 6x better but still far from the continuous variants.
  **Rerun 2026-09-19 with the real dataset and the calibrated box: every number
  above is unchanged, to the candidate.** That is not a coincidence — see the
  retraction below, the solver never applies the box, so calibrating it cannot
  move the search. Useful as a control: it confirms the tie effect comes from
  quantisation and not from the prior.
- **Corollary:** for VQ-16 the out-of-support hypothesis is
  void by construction — every candidate is one of 16 learned codes, hence
  in-support. If VQ-16 is still poor, the failure is representational capacity,
  not out-of-support search. This is a useful lever for separating the two.
- **The empirical-macro bank is rebuilt at eval time, not shipped.**
  `build_empirical_macro_action_bank` (`h_le_wm/planning/policies.py:138-240`)
  encodes 4096 contiguous training action spans; `EmpiricalMacroActionSolver`
  (same file, from line 243) adds the residual. Datasets must be staged first.

### Colab feasibility, and two more artifact defects (2026-09-26, by reading the code)

Checked while planning the first evaluation run; all of it before spending GPU
time. Write-up with the session plan in `docs/COLAB_PLAN.md`.

- **`stable_worldmodel` installs on Colab.** Every package that blocks the Intel
  Mac ships a Linux x86_64 wheel (PyPI, 2026-09-26): `lancedb` 0.39.0 and
  `pylance` 12.0.0 as `cp310-abi3-manylinux_2_28_x86_64`, so any CPython >= 3.10
  works, and `stable-pretraining` is pure Python needing `torch>=2.4`, which
  Colab exceeds. `stable-worldmodel` 0.1.1 declares `requires-python >=3.10`.
  Unverified until a session runs: whether pip leaves Colab's CUDA torch alone,
  and whether `stable_pretraining.data` imports there (it raises on this Mac
  under torchvision 0.17.2).
- **Defect: `environment-gpu.yml` omits the `format` extra, which is mandatory.**
  It installs `stable-worldmodel[train,env]`, but
  `stable_worldmodel/data/formats/hdf5.py:11` imports `hdf5plugin`
  unconditionally, and the PushT `pixels` column really is blosc-compressed —
  HDF5 filter id `32001`, read off our own copy of the dataset. Without
  `hdf5plugin` the dataset cannot be opened at all, so the declared environment
  cannot run the eval it is shipped for. `[env]`, meanwhile, is far more than
  PushT needs: `envs/__init__.py` registers entry points as strings, and
  `envs/pusht/env.py:1-8` imports only `cv2`, `gymnasium`, `pygame`, `pymunk`.
- **Defect: the dataset is written where the reader does not look.** The HF repo
  `quentinll/lewm-pusht` holds `pusht_expert_train.h5.zst` at its root, so
  `scripts/setup_datasets.sh` extracts to `$STABLEWM_HOME/pusht_expert_train.h5`
  — and `h_le_wm/validate.py:15` checks exactly that path, so **preflight
  passes**. But `HDF5Dataset.__init__` resolves
  `get_cache_dir(cache_dir, sub_folder='datasets')`
  (`stable_worldmodel/data/formats/hdf5.py:53`), i.e.
  `$STABLEWM_HOME/datasets/pusht_expert_train.h5`. A green preflight followed by
  `FileNotFoundError`, after a 45-minute download. A hard link fixes it.
- **Defect: the same thing again with the checkpoints**, found in the session.
  `setup_checkpoints.sh` stages to the registry relpath
  `$STABLEWM_HOME/runs/pusht_hierarchical_default/..._epoch_15_object.ckpt`, while
  `swm.policy.AutoCostModel` resolves a policy name under
  `get_cache_dir(sub_folder='checkpoints')` and appends `_object.ckpt`
  (`stable_worldmodel/policy.py:455-475`), i.e.
  `$STABLEWM_HOME/checkpoints/runs/.../..._epoch_15_object.ckpt`. The eval stops
  with `AssertionError: Checkpoint path does not exist: ... Launch pretraining
  first.` One symlink, `$STABLEWM_HOME/checkpoints/runs -> $STABLEWM_HOME/runs`,
  covers every staged run including the probes. That function's first branch takes
  `run_name` as a path when it exists, so an absolute `policy=` would also work —
  but then the command stops matching the authors' own matrix command, which is
  what keeps our number comparable.
- **`run_pusht_smoke.sh` does not evaluate the released checkpoint.** Spec
  `smoke/pusht` is a workflow of `pusht_train.yaml` + `pusht_eval.yaml`
  (`h_le_wm/experiments/specs/smoke/pusht.yaml`): it trains a one-epoch
  `pusht_smoke` model and evaluates *that*. It tests wiring, nothing else — which
  is why `docs/STATUS.md` could record a "smoke test" as the next step without it
  ever producing a comparable number.
- **Preflight cannot be narrowed to PushT, and neither can the checkpoint
  check.** `validate preflight` always calls `check_baseline()` (needs
  `code/third_party/lewm`) and checks tier `required-now`, which is
  `baseline/pusht/lewm` **and** `baseline/cube/lewm`
  (`checkpoint_registry.yaml`). No skip flag exists. `validate datasets
  --datasets pusht` does work. But `validate checkpoints --checkpoint <name>` is
  **not** targeted, as we assumed on 2026-09-26 and found out in the session:
  `--tier` defaults to `required-now` and cannot be emptied (argparse `choices`),
  and `iter_registry_entries` returns the **union** of the tier's entries and the
  named ones (`h_le_wm/checkpoints.py:114-127`), so naming the Hi-LeWM checkpoint
  still demands both flat baselines. With the baseline conversion broken (below),
  no invocation of the shipped validator can pass on a PushT-only setup. Check the
  staged file directly instead — it is the one file the eval loads.
- **The 46 GB dataset is 46 GB of pixels, and the eval needs few of them.**
  Measured on our copy: `pixels` is 351.7 GB raw (46.3 GB on disk under blosc)
  while `action`, `proprio`, `state`, `episode_idx`, `step_idx`, `ep_len` and
  `ep_offset` total **0.16 GB**. Pixels cannot be dropped outright — the goal
  observation is the dataset's own frame, `_extract_init_goal` takes the last
  frame of `load_chunk(ep, start, start+goal_offset+1)`
  (`stable_worldmodel/world/world.py:566-592`) — but a 50-episode run touches
  only ~2.5 MB of compressed pixels per episode. So ~400 whole episodes is about
  1 GB: a Drive-resident stand-in that removes the download from every later
  session. Two caveats keep it out of the first, paper-comparable run:
  normalization statistics are computed from whatever file is loaded
  (`build_process_map`, `h_le_wm/eval/hierarchical.py:319`) and the episode pool
  shrinks to the subset. And `write_episode_subset`
  (`analysis/hilewm_local/data.py:151`) needs two changes first: it writes
  uncompressed (pixels would balloon to ~7.5 GB) and it copies `episode_idx`
  verbatim, while the eval indexes episodes by that column's *value*
  (`h_le_wm/eval/hierarchical.py:556`), so a subset must renumber it to `0..K-1`.

### A finished run is only comparable if its episode manifest survives (2026-09-26)

`results/runs.csv` keeps the rate; the **per-episode outcomes** live only in
`<output>/None/*_episodes.tsv` under `$STABLEWM_HOME`, which is Colab local disk. A
run whose manifest is lost can still be quoted as a number and can no longer be
**paired** against any other run — and pairing is what makes a ~10-point difference
measurable at n=50 (see `analysis/compare_eval_runs.py`). The rate alone cannot be
paired, because pairing needs to know *which* episodes each planner won.

So the manifest copy is not housekeeping, it is part of producing the measurement:
run the copy step after every eval, not once at the end of a session. The notebook's
appendix now reports how many manifests reached Drive and how many are still only on
local disk.

### The eval prints every episode outcome twice (2026-09-26)

Small, but it corrupts any automated reading of a run.
`h_le_wm/eval/hierarchical.py:589-598` prints the per-episode lines three times
over: once under `==== EPISODE OUTCOMES ====` for all episodes, then again under
`==== FAILED EPISODES ====` and `==== PASSED EPISODES ====` for the two subsets. So
each `PASS`/`FAIL` line appears exactly twice, and counting raw lines doubles the
episode count — our first parser reported 8 failures in a 4-episode probe. The
notebook deduplicates by `eval_index` before cross-checking the count against
`eval.num_eval` and the rate against the metrics dict.

### `World.evaluate_from_dataset` does not exist in the released library (2026-09-26, hit in the first Colab session)

After the checkpoint loads, the model is built, the latent bounds are calibrated
(`[hi_eval] calibrated high-level latent bounds (chunks=2048, chunk_len=5)`) and
1,402,587 valid starting points are found — and then
`h_le_wm/eval/hierarchical.py:562` calls

```python
world.evaluate_from_dataset(dataset, start_steps=..., goal_offset_steps=...,
                            eval_budget=..., episodes_idx=..., callables=...,
                            video_path=...)
```

`AttributeError: 'World' object has no attribute 'evaluate_from_dataset'`.
`stable_worldmodel` 0.1.1 exposes that behaviour through
`World.evaluate(dataset=..., episodes_idx=..., start_steps=..., goal_offset=...,
eval_budget=..., callables=..., video=...)`, which dispatches to the private
`_evaluate_from_dataset` (`world/world.py:188-255`, `:492`). Two keywords were
renamed as well: `goal_offset_steps` -> `goal_offset`, `video_path` -> `video`.

`hilewm_local.patches.apply_world_evaluate_alias` installs the missing method as a
forwarder, so the artifact's call site runs unmodified and the evaluation itself is
the library's own code. `analysis/run_eval.py` applies it and prints whether it was
needed. The same alias covers `h_le_wm/train/hierarchical.py:576` and
`h_le_wm/eval/baseline_manifest.py:233`, which call the same missing method.

Ninth mismatch, and the deepest in the pipeline so far: everything before it now
works, including the model, the CEM calibration and the dataset sampling.

### The shipped eval cannot load the shipped checkpoints: missing pickle aliases (2026-09-26, hit in the first Colab session)

`swm.policy.AutoCostModel` -> `torch.load` raises `ModuleNotFoundError: No module
named 'hi_jepa'`. The released `*_object.ckpt` files are pickled model objects
naming the old top-level modules of the `hi_train` codebase — `hi_jepa`,
`hi_module`, `hi_vq`, `hi_waypoint_sampling`, `module` — and the artifact knows it:
`h_le_wm/train/hierarchical.py:41-54` maps all five onto `h_le_wm.models.*` with
`sys.modules.setdefault`, under the comment "Register aliases so torch.load can
unpickle them".

`h_le_wm/eval/hierarchical.py:34-39` carries the first half of that block — the
`_baseline_adapter.ARPredictor` touch that registers the dynamic
`_baseline_lewm_module` — and **not the alias registration**. So the eval path as
shipped cannot load the checkpoints as shipped. Nothing in the artifact's own eval
entry point works around it.

Fixed in our wrapper, not in their code: `analysis/run_eval.py` calls
`hilewm_local.patches.register_object_ckpt_aliases()`, which imports
`h_le_wm.train.hierarchical` so the artifact's own registration runs, and falls
back to registering the five aliases directly if that import fails. It prints which
route it took.

**This is the strongest evidence yet on the open question of how the paper's
numbers were produced.** Eight independent mismatches now sit between the released
artifact and the released `stable_worldmodel` 0.1.1, and this one is internal to
the artifact: the eval module is missing a block that its sibling train module
has. A single working run of `h_le_wm.eval.hierarchical` against
`pusht_hi_lewm_epoch15_object.ckpt` was not possible with what was published.

### The shipped eval config passes env kwargs the released library does not accept (2026-09-26, hit in the first Colab session)
### `world.history_size` must be present for the artifact and absent for the library (2026-09-26)
### The acting diagnostics cannot run against the released library either (2026-09-27)

The `oracle_subgoal_acting` experiment — the paper's own upper-bound test, part of its
`paper/reproduction` workflow — drives the environment itself instead of going through
`World.evaluate`, and every assumption it makes about that environment is a gymnasium
vector-env assumption:

| line in `scripts/diagnostics/hi_acting_diagnostics.py` | what it needs | what 0.1.1 has |
| --- | --- | --- |
| `:440` `for i, env in enumerate(ctx.world.envs.unwrapped.envs)` | `envs.unwrapped` | `World.envs` is a custom `EnvPool` with no `unwrapped` |
| `:1089` `world.step()` | a public single-step | only the private `_run` / `_run_iter` generator |
| `:1091` `world.envs.unwrapped._autoreset_envs = 0` | gymnasium's autoreset flag | `EnvPool.step` never auto-resets, so there is nothing to disable |

So the entire acting-diagnostics surface is unrunnable as published, on top of the ten
mismatches already recorded. `hilewm_local.patches.apply_world_step_shim` supplies the
two missing pieces: `EnvPool.unwrapped` returns the pool itself (what gymnasium's
`unwrapped` means for a non-wrapper), and `World.step` performs exactly the two
statements `_run_iter` executes per iteration (`world/world.py:398-404`) **without the
reset** — which is precisely what that `_autoreset_envs = 0` line was trying to
arrange. Verified against stand-in classes: the shim installs both, is idempotent,
steps with `mask=None`, and leaves `infos` for the caller's goal injection.

One consequence to read carefully: terminated envs keep being stepped. The diagnostic
ORs `terminateds` across steps, so `success_rate` is unaffected, but the final latent of
an env that already succeeded keeps drifting, which inflates
`final_terminal_latent_error_mean`.

**Running total: eleven mismatches between the released artifact and the released
`stable_worldmodel` 0.1.1**, five of them requiring runtime patches in
`analysis/hilewm_local/patches.py`. Every headline surface of the paper we have tried —
the hierarchical eval, the empirical-macro path, the flat baseline conversion, the
acting diagnostics — needed work before it would run, and one of them (the flat
baseline) still does not.

A sharper form of the previous finding, hit while running the authors' own acting
diagnostics. The two requirements cannot both be met by any config:

- `swm.World` forwards unknown kwargs to `gym.make`, and 0.1.1's `PushT` accepts
  neither `history_size` nor `frame_skip`, so the eval config's `world` block raises
  `TypeError` — **the keys must be absent**;
- `scripts/diagnostics/hi_acting_diagnostics.py:393` computes
  `shape_prefix = (int(world.num_envs), int(eval_cfg.world.history_size))` — **the key
  must be present**.

Deleting them, which is what the eval path does with Hydra's `~key`, makes the
diagnostic die with `omegaconf.errors.ConfigAttributeError: Missing key history_size`.
Keeping them makes the environment refuse to build. So the config is unsatisfiable and
the fix has to be at runtime: `hilewm_local.patches.apply_world_env_kwargs_filter`
wraps `World.__init__`, drops those keys on the way to `gym.make`, and leaves the
config intact for whoever reads it. Both are no-ops in 0.1.1 at their configured value
of 1 — that version has no frame stacking and no frame skipping — and the filter
prints what it dropped. Verified against a stand-in `World`: exactly those two keys are
removed and `render_mode` survives.

`world.history_size` has exactly one reader in the entire artifact, so this is a
two-line incompatibility rather than a deep one — but it is the tenth, and the first
where the artifact contradicts *itself* through the library rather than merely
disagreeing with it.

`swm.World(**cfg.world, ...)` (`h_le_wm/eval/hierarchical.py:498`) raises

```
TypeError: PushT.__init__() got an unexpected keyword argument 'history_size'
  ... raised from the environment creator for swm/PushT-v1
      with kwargs ({'history_size': 1, 'frame_skip': 1, 'render_mode': 'rgb_array'})
```

`config/eval/hi_pusht.yaml:10-11` sets `world.history_size: 1` and
`world.frame_skip: 1`. In `stable-worldmodel` 0.1.1, `World.__init__` names none
of them and forwards `**kwargs` to `gym.make` (`world/world.py:115-152`, `:58`),
and `PushT.__init__` takes `block_cog, damping, render_action, resolution,
with_target, render_mode, relative, init_value` — neither key exists
(`envs/pusht/env.py:29-39`). All four `hi_*.yaml` eval configs carry the same two
lines, so this is not PushT-specific.

Dropping them is exactly equivalent at these values: 0.1.1's `MegaWrapper` has no
frame stacking and no frame skipping, so there is nothing for `history_size: 1` /
`frame_skip: 1` to configure, and no artifact code reads either key — they appear
only in the eval configs. Our commands therefore delete both with Hydra's `~key`
syntax rather than translating them.

Taken together with the two findings above, the pattern is clear: **the artifact
was developed against a `stable_worldmodel` that is not the one on PyPI.** The
`CEMSolver` env-count bug, the `transformers` pickle classes, and now the env
kwargs are three independent symptoms of the same gap, which also bears on the open
question of how the paper's unconstrained Hi-LeWM numbers were produced.

### The eval cannot start: the config directories are not importable packages (2026-09-26, hit in the first Colab session)

`python analysis/run_eval.py --config-name=hi_pusht ...` fails immediately with

```
Primary config module 'h_le_wm.config.eval' not found.
Check that it's correct and contains an __init__.py file
```

`h_le_wm/eval/hierarchical.py:467` declares
`@hydra.main(version_base=None, config_path="../config/eval")`. On a packaged
module Hydra resolves that relative path to the **module** `h_le_wm.config.eval`,
which must be importable. The artifact ships `h_le_wm/config/`,
`config/eval/`, `config/train/` and `config/train/data/` **without
`__init__.py`**, while every other subpackage under `h_le_wm/` has one
(`__init__.py` exists in `probe`, `experiments`, `planning`, `baseline`, `models`,
`train`, `eval`). Recent hydra-core refuses; presumably the version the authors
used fell back to a file path.

**This is the one change we have made inside `code/`**: four empty `__init__.py`
files, added rather than edited, so `git diff ff6eb38 -- code/` shows exactly four
new empty files and nothing else. The notebook also creates them if they are
missing, so a fresh Drive copy heals itself.

Two smaller observations from the same run, neither a problem:

- `run_eval.py` prints `CEM env-count fix: needed=False applied=False` because
  `sitecustomize` had already applied it (`HILEWM_PATCH_CEM=1` is set for
  subprocesses). The first line of the log, `[hilewm_local] CEM env-count fix
  applied via sitecustomize`, is the one that matters.
- The probe's "peak GPU memory: 0 MiB" and its extrapolated runtime are
  meaningless when the run exits in seconds; they only carry information once the
  command actually plans.

### The object checkpoints cannot be unpickled under transformers >= 5.9 (2026-09-26, hit in the first Colab session)

`torch.load` on `pusht_hi_lewm_epoch15_object.ckpt` raises
`AttributeError: Can't get attribute 'ViTEncoder' on transformers.models.vit.modeling_vit`.
The `*_object.ckpt` files are pickled model objects, so every class they name must
exist in the installed library. Read out of our own copy with `pickletools`
(`zipfile` -> `data.pkl` -> `genops`, counting `STACK_GLOBAL` operands), the
pickle names ten of them:

```
transformers.models.vit.modeling_vit: ViTModel ViTEncoder ViTLayer ViTAttention
  ViTSelfAttention ViTSelfOutput ViTIntermediate ViTOutput ViTEmbeddings
  ViTPatchEmbeddings
transformers.models.vit.configuration_vit.ViTConfig
transformers.activations.GELUActivation
```

Checked against the upstream tags: all ten are present in 4.57.x and up to
**5.8.0**, and gone in **5.9.0**, where `modeling_vit.py` keeps only
`ViTEmbeddings`, `ViTPatchEmbeddings`, `ViTAttention`, `ViTMLP`, `ViTLayer`,
`ViTPooler` and the model classes. Latest at the time of writing is 5.17.0, which
is what a current Colab installs, since `stable-worldmodel` asks only for
`transformers>=4.50.0`.

This blocks the whole evaluation, not just a sanity check: the artifact's eval
loads the same object checkpoint (`h_le_wm/eval/hierarchical.py:527`). The fix is
a pin — `transformers>=4.50,<5.9` (5.8.1 at present), with `4.57.6` as the
era-matched fallback — plus a `hasattr` check on those ten class names right after
the install, which costs nothing and fails in the second cell instead of at load
time. Our own `hilewm_local` loader is unaffected: it rebuilds the model from the
`*_weights.ckpt` state dicts and constructs the ViT itself, which is why no local
measurement ever hit this.

### The flat baseline conversion is broken by upstream drift (2026-09-26, hit in the first Colab session)

`scripts/setup_baseline_checkpoints.sh fetch-baselines` downloads
`quentinll/lewm-pusht` and dies in
`scripts/tools/convert_hf_weights_to_object_ckpt.py:281` with `RuntimeError:
Failed to load weights into model`, on all three of its key-stripping strategies.
The two sides disagree about the pixel encoder:

| side | keys |
| --- | --- |
| the model Hydra built | `encoder.layers.N.attention.{q,k,v,o}_proj.*`, `encoder.layers.N.mlp.fc{1,2}.*` (12 layers) |
| the weights on the Hub | `encoder.encoder.layer.N.attention.attention.{query,key,value}.*`, `...intermediate.dense.*` (12 layers) |

The second set is HuggingFace `ViTModel` naming; the first is a hand-written ViT,
and the run log says `Created ViT-tiny from scratch with config {hidden_size:
192, num_hidden_layers: 12, num_attention_heads: 3, intermediate_size: 768,
image_size: 224, patch_size: 14}`. That builder is not in `stable-worldmodel`
0.1.1 — the string and the `q_proj` naming appear nowhere in the wheel — so the
model came from the upstream `le-wm` checkout, which we cloned at `main` because
`THIRD_PARTY_LEWM.md` ships the literal placeholder `<PINNED_COMMIT>`. Upstream
has since replaced the HF encoder; the released weights predate that.

`stable_worldmodel`'s own `LeWM` takes an injected encoder and calls it as
`self.encoder(pixels, interpolate_pos_encoding=True)`
(`wm/lewm/lewm.py:19,34`) — the HuggingFace API the weights were saved against.
So there are two ways back: an older upstream commit, or building the baseline
against a stock HF ViT in `analysis/` (which is what `hilewm_local` already does
for the Hi-LeWM encoder). Neither has been tried.

**Do not take the error message's advice.** It suggests `--allow-non-strict`;
every encoder key is missing, so that would leave the entire 12-layer pixel
encoder randomly initialised and save the result as a baseline checkpoint.

Consequences, all bounded: the flat-vs-hierarchical comparison is deferred, full
`validate preflight` cannot pass (both baselines are tier `required-now`), and
**the Hi-LeWM evaluation is unaffected** — only `h_le_wm/baseline/*` and
`h_le_wm/eval/baseline_manifest.py` import the upstream checkout. Treat the
paper's implied flat numbers (~52.7 at d=50, ~18.0 at d=75) as the reference
until we measure our own.

## Findings that change the diagnosis plan

- **RETRACTED 2026-09-19: the quantile box is computed but never enforced, so
  the "unconstrained" CEM really is unconstrained.** An earlier entry here
  claimed the search was box-bounded by data quantiles and that the claim to
  test was therefore about box *shape* rather than "it searches anywhere". That
  was wrong. The box is real — `calibrate_latent_prior`
  (`h_le_wm/planning/policies.py:443-644`) takes the 5th-95th percentile of 2048
  encoded training chunks, adds a 5% margin and clamps to ±3 — and
  `_build_high_action_space` does hand it to the solver. But
  `stable_worldmodel.solver.cem.CEMSolver` uses `action_space` for exactly one
  thing: `self._action_dim = int(np.prod(action_space.shape[1:]))`
  (`solver/cem.py:61-64`). It never reads `.low`/`.high`, never clips, and
  samples `randn * var + mean` starting from mean 0, var 1. Verified by grep
  across the package: `cem.py`, `mppi.py`, `gd.py` and
  `predictive_sampling.py` enforce nothing, while `icem.py`, `pgd.py` and
  `categorical_cem.py` do — so this is solver-specific, and the shipped config
  picks one of the solvers that does not. `EmpiricalMacroActionSolver` also
  ignores the bounds; what constrains it is the bank, not a box.
  **Measured, so the size of the retraction is clear** (main checkpoint, real
  dataset, seed 42): the calibrated box has mean width 5.43 and **31 of 32
  dimensions sit on the ±3 clamp**; 3.8% of per-dimension draws and **74.3% of
  candidates** fall outside it. If it were enforced it would bite hard. It is
  not. **So the paper's framing stands and our refinement did not** — the
  hypothesis to test is the original one, that the search leaves the support of
  training macro-actions. The kNN / Mahalanobis measurement in diagnosis step 2
  is still the right instrument, and is now the *main* one rather than a test of
  box shape.
- **Cost/subgoal mismatch — a second candidate explanation.** With `horizon: 2`,
  `get_cost_high` scores the **last** predicted waypoint
  (`h_le_wm/models/jepa.py:469-471`) but the subgoal handed to the low level is
  the **first** (`h_le_wm/planning/policies.py:822`). Nothing forces the first
  waypoint to be a good control target. This is independent of out-of-support
  search and should be separated from it in the diagnosis.
- **The published `stable_worldmodel` CEM solver cannot run the artifact's
  hierarchical planner at all.** `CEMSolver.solve` takes the environment count
  from the *first* value of the info dict:
  `total_envs = len(next(iter(info_dict.values())))`
  (`stable_worldmodel/solver/cem.py:131`). Both `_plan_high` and `_plan_low` put
  the string `planner_level` first (`h_le_wm/planning/policies.py:793`, `:840`,
  and `:954` for the staged policy), so the high level always plans for
  `len("high") == 4` envs and the low level for `len("low") == 3`, whatever
  `eval.num_eval` says. **Verified 2026-09-19** by driving the real
  `HierarchicalWorldModelPolicy` with the real solver and a stub env:

  | n_envs | `_plan_high` | `_plan_low` |
  | --- | --- | --- |
  | 1 | RuntimeError | — |
  | 4 | ok (coincidence) | RuntimeError (`[4, 5, -1]` from size 30) |
  | 8 | RuntimeError (`[8, 1, 32]` from size 128) | — |
  | 50 | RuntimeError (`[50, 1, 32]` from size 128) | — |

  No env count satisfies both levels, so this is not a matter of picking
  `num_eval` carefully. The line is byte-identical in stable-worldmodel 0.1.0 and
  0.1.1 — the only published versions whose dates fit this artifact.
  Two details suggest the authors met the symptom without finding the cause:
  `HiJEPA.get_cost` carries an explicit fallback for when "solver paths may drop
  non-tensor metadata keys" (`h_le_wm/models/jepa.py:543-551`), which is exactly
  what the slicing does to `planner_level`; and their own
  `EmpiricalMacroActionSolver` gets it right, using `self.n_envs` and slicing
  only tensors (`h_le_wm/planning/policies.py:365-380`). **So the
  empirical-macro path (Hi-LeWM-C) is unaffected and only plain CEM is broken.**
  Open question worth raising: how were the unconstrained Hi-LeWM numbers
  produced, if not with a published `stable_worldmodel`?
  **Our fix:** `analysis/hilewm_local/patches.py` reorders the info dict so a
  tensor comes first, leaving the solver's arithmetic untouched and preserving
  its documented "subset of envs" intent. It is a monkeypatch, not an edit to
  `code/`, and it no-ops if an upstream release fixes the solver. Apply it via
  `analysis/run_eval.py` (direct runs) or `HILEWM_PATCH_CEM=1` plus `analysis/`
  on `PYTHONPATH` (the artifact's shell scripts). After patching, 1/4/8/50 envs
  all plan correctly through both levels.
- **Hi-LeWM-C searches "random real anchor + a learned offset", and its one
  pure-bank candidate per iteration never matters.** Measured 2026-09-22 with
  `analysis/inspect_empirical_residual.py` (d32, d=50, 1500 x 40, lambda_res 0.1,
  bank 4096, sequence sampling, 4 environments; record
  `results/inspect_empirical_residual/20260922-002009_d50_sequence.json`), which
  observes the solver instance from outside without touching the artifact.
  Line 412 of `h_le_wm/planning/policies.py`, `residual[:, 0] = 0.0`, zeroes
  sample index 0 only, so each iteration has **exactly 1 pure-bank candidate per
  environment and 1499 bank+noise** — constant over all 40 iterations, 0.067% of
  the 240,000 candidates scored. The pure-bank candidate **never entered the
  top-10 elites at any iteration (0 of 40 each time)** and was **never the
  returned action (0 of 4)**. What does change across iterations is the noise:
  its standard deviation contracts from 0.100 to 0.0044 (x23) while the absolute
  mean residual grows from 0.002 to 0.070. The search therefore converges not to
  real bank sequences but to *randomly re-drawn bank anchors plus one learned,
  anchor-agnostic offset*; no noised candidate ever came within 1e-2 of its
  anchor. Two consequences. First, our CLAUDE.md summary of the paper says "one
  zero-residual candidate per sampled anchor"; the code has one per iteration,
  and with 1500 anchors per iteration those are very different constraints —
  either the summary or the paper's description does not match the
  implementation, and we have not checked the paper text directly. Second, a
  possible origin, **unverified**: `CEMSolver` keeps its current mean alive with
  `candidates[:, 0] = batch_mean`; the analogous line here would be
  `residual[:, 0] = residual_mean`, but it is `0.0`, so after the first iteration
  sample 0 is an unperturbed anchor rather than the current mean, which would
  explain why it never wins.
- **Bank anchors are re-drawn every CEM step.** Only the residual mean/std are
  refit from elites (`h_le_wm/planning/policies.py:697-703`), so the empirical
  search never concentrates on good anchors.
- **Shipped eval config does NOT match paper Table 5.**
  `config/eval/hi_pusht.yaml` ships high CEM 900 samples / 20 steps / topk **30**
  and low 600 / 30 / topk **60**; Table 5 above says topk 10 / 150 and low 300
  samples. Reconcile before comparing against the reference numbers.
  `device: "cuda"` is hardcoded in the solver configs.

## Measured results with the environment (Colab)

### Our first success rate: Hi-LeWM online, plain CEM, d=50 — 36.0 % (2026-09-26)

**36.0 %, 18 of 50 episodes.** PushT, Hi-LeWM with unconstrained high-level CEM,
goal offset d = 50, the paper's Table 5 budget (high 1500 samples / 40 iterations /
top-10, low 900 / 30 / 150, `eval_budget` 100), the canonical `D50` row of the
authors' own sweep (high horizon 2, low horizon 2, receding 1/1, replan interval 5,
action blocks 1/5), seed 42, one seed.

| quantity | value |
| --- | --- |
| success rate | **36.0 %** (18/50) |
| standard error | 6.8 points |
| Wilson 95 % | 24.1 - 49.9 % |
| Clopper-Pearson 95 % | 22.9 - 50.8 % |
| paper, same cell | 38.7 % |
| difference | **-2.7 points** |

From `analysis/summarize_eval_runs.py` over `results/runs.csv`; the record is
`results/summarize_eval_runs/20260926-213028.json` [regenerated 2026-10-05: `20261005-103325.json`, identical]. Run on Colab (A100, 40960 MiB)
in ~37 minutes; environment and provenance below.

**What this establishes.** The paper's central claim about this configuration
reproduces: unconstrained hierarchical planning at d=50 lands near 38.7 %, well
below the flat baseline the paper implies (~52.7). Our -2.7 points is inside the
noise — the standard error alone is 6.8 points, and the paper's value is the best
of a sweep over the rows of `hierarchical_matrix.csv` while ours is the canonical
row, which biases their number upward relative to ours. **At n=50, nothing smaller
than roughly 15 points is resolvable**, so this run cannot distinguish 38.7 from
30 or from 45; what it does do is rule out a gross failure of our setup, which
after nine mismatches was a live possibility.

**What it does not establish.** One seed, one configuration, one goal offset. The
diagnosis of *why* the subgoals are poor (everything in the sections below) is
still tied to this number only by the fact that both use the same checkpoint at the
same budget.

**Provenance.** `analysis/run_eval.py` with the three runtime fixes (`CEM env-count
fix: needed=False applied=False` because `sitecustomize` had already applied it;
`object-checkpoint module aliases: train-module`; `World.evaluate_from_dataset alias
installed: True`), content fingerprint `sha:bb14f7e89a2b`, which
`analysis/resolve_run_provenance.py` resolves to commit `56c397f`. Colab: Python
3.13, `torch` 2.11.0+cu128, `stable-worldmodel` 0.1.1, `stable-pretraining` 0.1.8,
`transformers` pinned `<5.9`, `numpy` 2.1.3. Two gates passed inside the notebook:
the library's metrics dict agreed with the artifact's per-episode lines, and the
number of those lines matched `eval.num_eval`.

**Timings**, for planning the rest: at 50 environments on the A100 a high-level CEM
solve took 47.3 s and a low-level solve 31.7 s, one of each per 5 environment steps,
so 100 steps is ~37 minutes. At 4 environments the same solves took 3.9 s and 2.5 s
— about linear in the environment count. Peak GPU memory never exceeded 1 GB of 40,
so the environment count, not memory, is the knob.

### Hi-LeWM-C does not beat plain CEM in control at d=50 — 34.0 % vs 36.0 % (2026-09-26)

**The paper's +10 points for empirical-macro CEM does not reproduce at this
configuration.** Same checkpoint, same budget, same 50 episodes, same seed, the only
change being `planning.high.empirical_macro.enabled=true` with the config's own
defaults (4096 sequences, `chunk_len` 5, `residual_scale` 0.1, sequence-level bank
sampling).

| | plain CEM | Hi-LeWM-C |
| --- | --- | --- |
| success rate | 36.0 % (18/50) | **34.0 % (17/50)** |
| Wilson 95 % | 24.1 - 49.9 | 22.4 - 47.8 |
| paper (best of sweep) | 38.7 % | 48.7 % |
| difference vs paper | -2.7 | **-14.7** |

Paired, on the identical episodes (`analysis/compare_eval_runs.py`, record
`results/compare_eval_runs/20260926-230003_d50_seed42.json` [regenerated 2026-10-05: `20261005-103115_d50_seed42.json`, identical]):

|  | Hi-LeWM-C pass | Hi-LeWM-C fail |
| --- | --- | --- |
| **plain CEM pass** | 8 | 10 |
| **plain CEM fail** | 9 | 23 |

Paired difference **-2.0 points** (95 % Wald -19.1 to +15.1), 19 discordant pairs
split 9 / 10, **McNemar exact p = 1.00**. So: no evidence of any advantage, and the
interval is wide enough that a +10 effect is not excluded either. What *is* excluded
is the effect being obvious.

**The discordance is the interesting number.** Both planners succeed on about a
third of the episodes, but only **8 of 50 on the same ones**, with 19 episodes won
by exactly one of them. If Hi-LeWM-C were simply a better planner the success sets
would nest; instead they overlap barely more than two independent coin flips at this
rate would (0.36 x 0.34 x 50 = 6.1 expected against 8 observed). That is what "the
terminal cost of the learned model is a poor control objective" looks like from the
outside: which episodes a planner wins is close to arbitrary.

**This is the first place where our local diagnosis and control come apart.**
Hi-LeWM-C's subgoals measure 3.5x better than plain CEM's and it does not exploit
the model (x0.83 against x9.5, 10 of 10 draws) — and none of that shows up in
success rate. Either the advantage is real but smaller than 50 episodes can see, or
better subgoals do not help because the low-level planner is not the binding
constraint. The reachability numbers lean the second way: Hi-LeWM-C's subgoals are
*easier* to reach (relative error 0.02-0.03 against 0.08), so the agent is getting
closer to better waypoints and still not finishing the task.

**Caveats, in order of how much they could matter.**

1. **One seed.** 19 discordant pairs at a 9/10 split is exactly the null. With the
   4:1 split a +10 effect implies, one seed gives p = 0.11 — so this run could not
   have established +10 even if it were there. Seeds 43 and 44 are the fix.
2. **The paper's 48.7 is best-of-sweep, ours is one row.** The sweep varies horizon,
   replan interval and receding horizon, and the paper's strongest empirical-macro
   result is the **staged** variant (64.0 at d=50), not the online one. We ran the
   canonical online row.
3. **`residual_scale` sits exactly at the boundary we measured locally.** Our
   lambda_res sweep found no exploitation only up to 0.1, with exploitation
   returning from 0.3. The config default is 0.1 — the most favourable value, which
   makes the null result harder to attribute to a badly chosen residual.
4. Bank size (4096 sequences) and `stage_sampling=sequence` are the defaults, and
   `CLAUDE.md` records sequence-level sampling as the paper's strongest setting.

**What to run next, reordered by statistical power rather than by narrative.** The
paper's largest claimed effects are staged Hi-LeWM-C at d=50 (**64.0 vs 38.7, +25**)
and online Hi-LeWM-C at d=75 (**32.7 vs 15.3, +17**). A +25 effect is visible at 50
paired episodes; a +10 is not. So test the big claims before spending seeds on the
small one.

#### Audit of that run (2026-09-26, from the executed notebook)

The result was distrusted on sight, so the session's own notebook was audited
against the alternative that we mis-ran it. **We did not**, as far as the run
itself goes:

- The empirical solver really was active. The log carries
  `[hi_eval] enabled empirical macro-action high solver (sequences=4096,
  chunk_len=5, raw_macro_len=25, encode_batch_size=4096, residual_scale=0.1,
  return_top_candidates=8, stage_sampling=sequence)` and then 20
  **`Empirical macro solve time`** lines (45.4 s each) beside 20 low-level
  `CEM solve time` lines (31.4 s) — exactly the 20 high and 20 low solves that
  `replan_interval=5` over 100 steps implies. Had the flag silently not taken, the
  log would say `CEM solve time` 40 times and the two runs would differ only by
  RNG, which is what a -2.0 with p = 1.00 looks like. It does not.
- The bank is horizon-aware and coherent with d=50.
  `total_macro_tokens = high_horizon * high_action_block = 2`, and
  `raw_macro_len = 25`, so each macro token covers 25 primitive steps and a bank
  sequence spans **50** — exactly the goal offset
  (`build_empirical_macro_action_bank`, `h_le_wm/planning/policies.py:143-245`).
- No fallback, clamp or "not enough valid spans" line anywhere in the run.
- **Our CEM patch cannot have harmed the empirical path asymmetrically.** It patches
  `CEMSolver.solve` only, and `EmpiricalMacroActionSolver` is a different class.
  Both paths still reach `get_cost_high`: with `planner_level` intact it routes
  directly, and where `CEMSolver` slices that string to a fragment,
  `HiJEPA.get_cost` falls back to routing on the `z_init`/`z_goal` tensors
  (`h_le_wm/models/jepa.py:536-551`).
- **The dataset cannot explain the difference.** Both runs read the same file, and
  the plain-CEM run reproduced the paper's own number for its cell (36.0 against
  38.7). A broken dataset would not spare one planner.
- The two runs evaluated the identical 50 episodes from the identical start steps —
  verified from the manifests, which `analysis/compare_eval_runs.py` refuses to pair
  otherwise.

**What the audit did find is worse than a mis-run, and it is not ours.** The
artifact ships **no reproduction path for Hi-LeWM-C at all.** `paper/reproduction`
runs `matrix/pusht/baseline`, `matrix/pusht/hierarchical`, the Cube pair, the
diagnostics and the figures — and **nothing sets
`planning.high.empirical_macro.enabled=true`**. Across every spec and script in
`code/`, the only occurrences of `empirical_macro` are the four eval configs, all
with `enabled: false`, and the plumbing in
`h_le_wm/experiments/run.py:359-362` that a spec *could* use and none does. The
authors' own tests exercise the bank with toy values (`num_sequences` 4, 5, 16,
`chunk_len` 2).

So the configuration behind the paper's 48.7 is **not recorded in the artifact**,
and our 34.0 is Hi-LeWM-C *at the artifact's defaults on the canonical online row* —
a defensible guess at the paper's setting, not a reproduction of it. That is the
honest status of the number, and it is a finding about the artifact as much as about
the method: of the paper's four headline PushT cells, exactly one (plain CEM) can be
reproduced from what was published.

#### The bank is genuinely the expert's contiguous actions (2026-09-26, `analysis/audit_macro_bank.py`)

The audit above dismissed the dataset as an explanation because both runs read the
same file. **That reasoning was wrong**, and the objection that corrected it is
worth recording: the two arms use the dataset *differently*. Hi-LeWM-C builds its
search space from the dataset's `action` column, while plain CEM's only contact with
those actions is `calibrate_latent_prior`, whose box `CEMSolver` never applies. A
fault in the action column, its normalisation or its grouping would therefore
depress exactly one arm and spare the other — an asymmetric failure, not a shared
one.

So it was measured instead of argued (`results/audit_macro_bank/20260926-232444_distrust_check.json` [regenerated 2026-10-05 by the rebuilt script: `20261005-103331_distrust_check.json`, identical],
256 sampled sequences, main checkpoint, CPU):

| check | result |
| --- | --- |
| bank latents vs our own independent encoding of the same spans | **max abs difference 2.9e-6** (mean latent magnitude 2.0, i.e. float32 noise) |
| spans inside a single episode | **256 / 256** |
| spans strictly contiguous (`step_idx` increments by 1) | **256 / 256** |
| span length vs goal offset | **50 primitive steps vs d = 50** |
| action column | (2336736, 2), **0 NaN rows**, range [-1.495, 2.043] |
| grouping | 5 primitive actions per model action (10 / 2), 25 primitive steps per macro token |

The first row is the strong one: `h_le_wm.planning.policies.build_empirical_macro_action_bank`
and `analysis/measure_support.encode_spans` are separate implementations of the same
grouping, ordering and normalisation, written months apart, and they agree to float
precision. Training and eval also fit the *same* `sklearn` `StandardScaler` on the
same column (`train/hierarchical.py:338`, `eval/hierarchical.py:319-332`), so the
bank is normalised as the encoder was trained.

The temporal check matters for a specific reason. Had the spans straddled episode
boundaries, the bank would hold latents that look statistically ordinary — the
encoder maps plausible inputs into a plausible region — while encoding action
sequences no agent could execute. That is exactly the shape of failure that would
produce better-looking subgoals and no control gain, which is what we observed. It
is ruled out.

**What this leaves open.** The bank is sampled **state-independently**: 4096 expert
action spans drawn uniformly from the whole training set, with no conditioning on the
current observation. Whether that covers the useful directions from a given state is a
question of bank size and of how far the residual may move an anchor — `num_sequences`
and `residual_scale`, the two knobs we left at the artifact's defaults, and the two
the paper does not record. That, not the dataset, is where the remaining doubt about
the 34.0 % belongs.

### The high level is the binding constraint: oracle subgoals reach 60.0 % (2026-09-27)

**Feed the low-level planner the expert's own future waypoint latents and the same
frozen controller succeeds on 30 of 50 episodes — in half the step budget.** This is
the artifact's own `oracle_subgoal_acting` experiment, run through
`analysis/run_diagnostics.py` (seed 42, d=50, high horizon 2, low horizon 2, low
receding horizon 1, low CEM 900/20/150, **`max_steps = 50`**, A100, 3.9 min).

| | success | budget |
| --- | --- | --- |
| **oracle subgoals** (expert waypoints) | **60.0 %** (30/50) | 50 steps |
| plain CEM | 36.0 % (18/50) | 100 steps |
| Hi-LeWM-C | 34.0 % (17/50) | 100 steps |

The comparison is **paired**: the diagnostic's episode sampling is line-for-line the
eval's (`hi_acting_diagnostics.py:330-335` against `eval/hierarchical.py:541-556`, both
`default_rng(seed).choice` over the same validity mask), and this was verified against
the dataset rather than assumed — the first nine row indices the diagnostic sampled
resolve to exactly the `(episode_id, start_step)` pairs of our eval manifests.

| vs oracle | discordant | paired difference | McNemar exact p |
| --- | --- | --- | --- |
| plain CEM | 18 for oracle, 6 for plain | **+24.0** (95 % Wald +6.0 to +42.0) | **0.023** |
| Hi-LeWM-C | 19 for oracle, 6 for Hi-LeWM-C | **+26.0** (+7.8 to +44.2) | **0.015** |

Significant at a single seed, and **conservative**: the oracle ran with half the
environment steps.

**This settles how to read the Hi-LeWM-C null, and it overturns my own reading of it.**
After that null I wrote that the reachability numbers leaned towards the low level not
being the binding constraint — i.e. that no high-level improvement could pay. That is
now refuted: there are **24 points of headroom at d=50 that better subgoals do
capture**, and Hi-LeWM-C captures none of them. So the dissociation is not "the high
level does not matter". It is:

> Hi-LeWM-C's subgoals are better by every latent-space measure we have — 3.5x closer
> to the expert's waypoint, in support, not exploiting the model, easier for the low
> level to reach — and none of that is the kind of better that control needs.

**Three secondary readings, all from the same run.**

1. **The low-level world model is accurate.** `reality_gap_mean` = 0.054, against block
   errors of 0.14-0.91: the model predicts its own block outcomes well. The low level's
   failures are not model error.
2. **Error accumulates across stages even with perfect targets.** Terminal latent error
   at the first oracle waypoint is 0.175 and at the second 0.414 — it more than doubles
   over the second 25 steps.
3. **Out-of-support search is not only a high-level phenomenon.** Even with oracle
   subgoals, the primitive actions the low-level CEM selects sit far outside the data:
   11-36 % outside the training actions' q05-q99 band per block, Mahalanobis median 22
   to 191, max |z| up to 13.7, and up to 4.2 % outside the environment's own action
   bounds. The paper's diagnosis of the high level applies to its low level too.

**And a caveat that matters for the paper's premise.** 60 % is not 100 %: even perfect
subgoals fail two episodes in five. The paper's implied flat LeWM at d=50 is ~52.7 %
(never quoted, inferred from its deltas, and at a budget we cannot check). If both
numbers are near their face value, then the entire upside of this hierarchy at d=50 —
given *oracle* subgoals — is a few points over not having a hierarchy at all, while its
own planner lands 17 points below flat. Worth stating carefully, since the budgets
differ, but it is the shape of the thing.

Records: `results/compare_eval_runs/20260927-001416_oracle_vs_plain.json` [lost with the first oracle run's manifest; regenerated 2026-10-05 from its rerun as `*_rerun_manifest`: +22.0, 18:7, p = 0.043, Fisher p = 0.045] (unpaired,
Fisher exact p = 0.027), the two paired records tagged `oracle_vs_plain_paired` and
`oracle_vs_hi_c_paired` [regenerated 2026-10-05 from the rerun manifest: +22.0 /
p = 0.043 and +24.0 / p = 0.029], and the manifest
`results/colab/manifests/oracle_subgoal_acting_d50_seed42_episodes.tsv` [lost; the surviving 50-step manifest is the 29/50 rerun, `oracle_subgoal_acting_d50_hh2_lh2_budget50_seed42_episodes.tsv`].

### The acting suite decomposes the gap — and the low-level horizon dominates it (2026-09-27)

Four more runs of the authors' own acting diagnostics, same 50 episodes, same seed,
`max_steps = 50` throughout. Everything below is paired on those episodes.

| configuration | subgoals | execution | low horizon | success | budget |
| --- | --- | --- | --- | --- | --- |
| oracle, low horizon 2 | expert waypoints | staged | 2 | **60.0 %** | 50 steps |
| generated staged, high horizon 2, low horizon 2 | the model's own | staged | 2 | **44.0 %** | 50 steps |
| online plain CEM | the model's own, replanned every 5 | **online** | 2 | 36.0 % | 100 steps |
| online Hi-LeWM-C | bank-constrained | **online** | 2 | 34.0 % | 100 steps |
| **oracle, low horizon 5** | expert waypoints | staged | **5** | **26.0 %** | 50 steps |

**The execution and horizon columns were added on 2026-10-01.** The horizon is matched at
2 everywhere except the last row, which is the deliberate probe; the eval commands get it
from the authors' `D50` matrix row, not from the config file. **Execution is what differs
between the staged diagnostics and the online evals**, so only comparisons within one
execution mode are attributable to the subgoals.

| paired comparison | difference | discordant | McNemar p |
| --- | --- | --- | --- |
| oracle lh2 vs **oracle lh5** | **+34.0** (+17.7 to +50.3) | 20 to 3 | **0.0005** |
| oracle vs generated staged | +16.0 (-2.7 to +34.7) | 16 to 8 | 0.15 |
| generated staged (50 steps) vs online plain (100 steps) | +8.0 (-7.5 to +23.5) | 10 to 6 | 0.45 |

**The largest effect anywhere in this project is the low-level planning horizon, not
the subgoals.** With the expert's own waypoints — the best subgoals that exist —
raising the low-level horizon from 2 to 5 costs **34 points**, wiping out more than the
entire 24-point gap between the oracle and the deployed planner. It is the only
comparison here that is significant at one seed, and it is significant at p = 0.0005.
The authors' sweep contains those rows, so this is visible from their own grid; it is
not visible in the paper's tables.

So the earlier headline needs qualifying. The high level does matter — the predicted
waypoint costs 16 points against the true one — but **the low level's configuration
dominates it**, and "improve the subgoals" is not the biggest lever available at d=50.

**Two mechanisms, both measured by the artifact's own instruments.**

1. **The predicted waypoints undershoot.** `generated_subgoal_acting` reports, for each
   stage, which true future state the produced subgoal is nearest to. At high horizon 2
   the first subgoal should sit 5 tokens (25 primitive steps) ahead and lands nearest to
   **4.01** tokens; at high horizon 1 the single subgoal should sit 10 tokens ahead and
   lands nearest to **7.53**. The high-level predictor systematically proposes a state
   ~20-25 % *less far along the trajectory* than the horizon it is asked for. A subgoal
   that is too near is reachable and useless, which is exactly the profile our latent
   measurements kept reporting.
2. **The selected macro-actions are astronomically off-manifold, with ordinary norms.**
   `high_plan_events.macro_summary` gives Mahalanobis **p50 = 496,942** at high horizon 2
   and **911,195** at high horizon 1, while `norm_ratio_vs_dataset` is 0.92 — the
   magnitudes look like the data and the directions do not. This is the paper's
   out-of-support hypothesis, confirmed inside the acting loop rather than in a static
   draw, and it matches the x794 we measured locally.

**Two supporting readings.**

* **The low-level world model is accurate when it is pointed at something reachable.**
  `low_level_reality_gap` over 10, 15 and 25-step blocks: gaps of 0.008, 0.003 and 0.028
  against actual errors of 0.046, 0.054 and 0.142, overall gap **0.013**. But with
  *generated* subgoals the same gap is 0.058-0.198 (mean ~0.13), two to four times the
  oracle's ~0.05. An off-manifold subgoal degrades the low-level model's own block
  predictions too — the error compounds rather than staying in the high level.
* **The second subgoal collapses onto the goal.** In the generated hh2 run, stage 1's
  nearest true-future offset is 49 steps for 44 of 50 episodes, while stage 0's ranges
  from 1 to 49. The high level is effectively producing "something erratic, then the
  goal", which is not a decomposition.

**~~Still missing~~ Filled 2026-10-01:** the `generated_subgoal_acting` run at high
horizon 1 completed (`exit 0`) but its printed summary was truncated before
`success_rate`. Recovered from the JSON on Drive
(`results/colab/acting/generated_subgoal_acting_d50_hh1_lh2_seed42.json`): **34.0 %**,
against 44.0 % at high horizon 2. Logged in `results/runs.csv` as
`generated_subgoal_acting_hh1`.

Records: `results/compare_eval_runs/` tags `generated_vs_oracle`, `online_vs_staged`,
`lh5_vs_lh2`; manifests under `results/colab/manifests/`. [2026-10-05: the two that
used the first oracle run are regenerated from its rerun under `*_rerun_manifest`
tags -- lh5 vs lh2 becomes +32.0, 20:4, p = 0.0015 -- and `online_vs_staged` is
identical. `docs/RECONSTRUCTION.md`.]

#### Why the oracle is only 60 %, and what my claim about it was worth (2026-10-01)

Raised against the reading above, and correctly: **there is no direct measurement here
that the low-level planner struggles to reach its targets**, and two things point away
from it. The paper reports **73.3 %** for oracle subgoals at d=50 and calls those
subgoals mostly reachable, and our own `low_level_reality_gap` says the low-level model
is accurate on reachable targets (gap 0.013 over 10-25 step blocks).

Three candidate explanations for 60 % against 73.3 %, in the order they are worth
testing:

1. **The budget.** Our oracle ran at **`max_steps = 50`** for a goal 50 steps away — no
   slack whatsoever — because `run_oracle_subgoal_acting` hardcodes
   `max_steps = int(cfg.goal_offset_steps)` (`hi_acting_diagnostics.py:1166`) and
   `--eval-budget` does not reach it (only `online_hierarchical_logging` reads that,
   `:1480`). The paper's goal budget at d=50 is **100**, twice the distance. The expert
   covers that path in exactly 50 steps, so the oracle run demanded expert-rate progress
   with zero margin.
2. **Fixed stage duration.** Staged execution switches target at step 25 whether or not
   the first waypoint was reached, so a slow first stage cannot be recovered.
3. **The low level's own ceiling.** Flat LeWM at d=50 is ~52.7 % (implied), so a
   controller-side limit of this order would be unsurprising.

**What this costs the earlier entry.** The comparison that supports "the high level
matters" is oracle 60.0 % against generated 44.0 % — both at `max_steps = 50`, both
staged, same episodes — and that stands. What does **not** stand is the inference I drew
from 60 % as an absolute: I wrote that even perfect subgoals fail two episodes in five
and compared that against the flat baseline's ~52.7 % to bound the hierarchy's total
upside. Those two numbers are at different budgets, 50 against 100, so the comparison was
invalid and is **withdrawn**. The 60 % is a lower bound on what oracle subgoals achieve,
not a ceiling.

**Two tests, both cheap.** `analysis/run_diagnostics.py --max-steps 100` overrides the
hardcoded loop budget (a deliberate deviation, which the run prints and the record keeps),
so the oracle can be measured at the paper's budget: if it moves toward 73 %, the
explanation is the budget. And `analysis/analyse_acting_npz.py` answers the reachability
question per episode from the saved `.npz` with no rerun at all — where each episode
ended relative to the goal and to the true trajectory, split by success, which separates
"stopped short" from "reached the end of the trajectory and still failed". The oracle
lh2 run was saved without `--save-npz`, so that one needs a 4-minute rerun; the lh5 and
generated runs already have theirs on Drive.

#### Answered: it was the budget. Oracle at the paper's 100 steps reaches 70.0 % (2026-10-01)

| oracle subgoals, d=50, lh2, seed 42 | success |
| --- | --- |
| `max_steps = 50` (the artifact's hardcoded budget) | 58.0 % (29/50), and 60.0 % on the first run |
| **`max_steps = 100` (the paper's goal budget)** | **70.0 %** (35/50) |
| the paper | 73.3 % |

**The paper's oracle number reproduces.** 70.0 against 73.3 is 3.3 points apart with a
standard error of 6.5 at n=50 — the same relationship as our plain-CEM 36.0 against their
38.7. So of the paper's PushT cells we have tried, **two now reproduce** (flat-CEM
hierarchy and the oracle upper bound) and one does not (Hi-LeWM-C).

**The headroom claim gets bigger and cleaner, not smaller.** At the *same* 100-step
budget: oracle **70.0 %** against the deployed planner's **36.0 %** — **+34.0 points**,
Fisher exact p = 0.0012, 3.6 standard errors. The earlier +24 compared a 50-step oracle
against a 100-step planner and understated the gap. The hypothesis that prompted this —
that the oracle's 60 % was budget-starved because the expert covers that path in exactly
50 steps — was right, and worth 12 points.

**The withdrawn comparison can now be made properly.** At a 100-step budget: oracle
70.0 %, flat LeWM ~52.7 % (implied by the paper's deltas, same budget), deployed
hierarchy 36.0 %. Perfect subgoals buy ~17 points **over** no hierarchy; the planner the
paper ships loses ~17 **to** it. Still resting on an implied flat number, which is the
next thing worth measuring ourselves.

**And a reproducibility result nobody asked for.** The `max_steps = 50` configuration was
run twice, same seed, same overrides, `torch.use_deterministic_algorithms(True)` and
`cudnn.deterministic` both on: **30/50 then 29/50**. One episode flips between sessions,
most likely a different GPU or driver changing a reduction order. So **±1 episode, ±2
points, is irreducible run-to-run noise** here, and no paired difference of a couple of
points means anything — including the -2.0 we measured for Hi-LeWM-C, which was already
p = 1.00. Our significant differences are an order of magnitude above it — though of
those, only the **+34 for the low-level horizon** isolates a single variable; see the
qualification below.

**One more number from the same batch:** `generated_subgoal_acting` at high horizon 1
reaches **34.0 %** against 44.0 % at high horizon 2. Two stages beat one by 10 points, and
the single-stage subgoal is also the one that undershoots most (nearest the true future at
7.53 tokens where 10 was asked).

**Paired, on the identical 50 episodes, everything at the paper's 100-step budget:**

| comparison | difference | discordant | McNemar exact p | isolates one variable? |
| --- | --- | --- | --- | --- |
| plain CEM -> oracle | **+34.0** (95 % Wald +15.9 to +52.1) | 22 to 5 | **0.0015** | **no** — subgoals *and* staged-vs-online |
| Hi-LeWM-C -> oracle | **+36.0** (+17.8 to +54.2) | 23 to 5 | **0.0009** | **no** — same two |
| oracle 50 steps -> 100 steps | +10.0 (+1.7 to +18.3) | **5 to 0** | 0.0625 | yes (budget) |

(The last column was added on 2026-10-01.)

The budget row is the most informative of the three despite the largest p, because
**the relationship is exactly nested**: every episode the 50-step oracle solved, the
100-step oracle solved too, and it added five more. Five discordant pairs all pointing the
same way is the smallest p the exact test can return (2 x 0.5^5 = 0.0625), so the limit
here is the number of episodes that changed, not the evidence. A pure budget extension
should be monotone in exactly this way, and it is — which is a much stronger signal than a
p-value from five pairs suggests, and it rules out the alternative that the extra steps let
the agent wander off a target it had already reached.

The two headline rows looked like the cleanest statement this project had. **They are
not — see the section immediately below, which qualifies them.** What they measure is the
difference between two shipped configurations, which differ in the subgoals *and* in
whether execution is staged or online.

#### Qualified: the +34 mixes the subgoals with the execution mode (2026-10-01)

**What is matched across all four runs.** Low horizon 2, high horizon 2, receding 1/1,
action blocks 1/5, replan interval 5, the paper's Table 5 CEM budget, goal offset 50, seed
42, the same 50 episodes. `colab_hi.ipynb` cell 26 passes the authors' `D50` row of
`hierarchical_matrix.csv` explicitly on every eval command, and `run_diagnostics.py` is
called with `--high-horizon 2 --low-horizon 2`. Nothing in the CEM or the horizons
differs.

**What is not matched.**

| rows | subgoals | execution | budget |
| --- | --- | --- | --- |
| oracle 70.0 % | expert waypoints | **staged** — commit to a subgoal sequence, switch at a fixed step | 100 |
| generated 44.0 % | the model's own | **staged** | 50 |
| plain CEM 36.0 %, Hi-LeWM-C 34.0 % | the model's own | **online**, replan every 5 | 100 |

So "+34.0 for oracle over plain CEM" varies **two** things: the subgoal source and the
execution mode. It is a real difference between two shipped configurations and it is
**not** a measurement of what correct subgoals are worth on their own.

**What stands.** The subgoal contrast with everything else held — oracle against the
model's own subgoals, both staged, both hh2/lh2, both at `max_steps = 50`, same 50
episodes — is **+16.0 points** (95 % Wald -2.7 to +34.7), 16 discordant to 8, McNemar exact
**p = 0.152** (`results/compare_eval_runs/20260927-004722_generated_vs_oracle.json`) [regenerated 2026-10-05 against the rerun manifest: +14.0, 16:9, p = 0.230]. The
*The acting suite decomposes the gap* entry already reported this and correctly called it
the comparison that stands; the error was later re-escalating to +34 and reading it as a
subgoal effect. Also clean: **two stages beat one**, 44.0 % against 34.0 %, where only the
high horizon differs.

**The gap between +16 and +34 is unexplained.** The candidate is the execution mode, and
the only measurement touching it — generated staged 44.0 % at 50 steps against online plain
36.0 % at 100 steps, +8.0 at p = 0.45
(`results/compare_eval_runs/20260927-004707_online_vs_staged.json`) [regenerated 2026-10-05: `20261005-103124_online_vs_staged.json`, identical] — is itself confounded
with the budget, so it cannot carry the attribution.

**The decisive run is four minutes.** `generated_subgoal_acting` with `--max-steps 100`,
hh2/lh2, seed 42: it pairs against the 70.0 % oracle with execution mode, horizons, budget
and episodes all held, giving the matched subgoal effect at the budget everything else is
reported at. That is `colab_hi.ipynb` cell 39 with one row added to `SUITE`. The oracle
path skips the high level, which is why these cost 4 minutes against the eval's 37.

**A question for the paper.** If the authors' 73.3 % oracle is staged and their 38.7 %
online, their oracle-vs-hierarchy gap mixes the same two variables. Not checkable from the
artifact; it goes to them alongside the plain-CEM question.

#### Resolved: the +34 is +22 subgoals and +12 execution mode (2026-10-01)

`generated_subgoal_acting` at `--max-steps 100`, hh2/lh2, seed 42, 50 episodes: **48.0 %**
(24/50). That is the model's own subgoals under the oracle's own machinery -- staged
execution, the same horizons, the same budget, the same episodes -- so oracle against it
varies **only the subgoal source**.

| comparison | what varies | difference | discordant | McNemar exact p |
| --- | --- | --- | --- | --- |
| generated staged -> **oracle staged** | **the subgoals, nothing else** | **+22.0** (95 % Wald +4.2 to +39.8) | 17 to 6 | **0.0347** |
| plain online -> generated staged | execution mode | +12.0 (-3.3 to +27.3) | 11 to 5 | 0.21 |
| plain online -> oracle staged | both of the above | +34.0 (+15.9 to +52.1) | 22 to 5 | 0.0015 |

**+22.0 and +12.0 sum to the +34.0 exactly**, and the subgoal term is the larger one and
the only one significant at a single seed. So the project's central claim is now both
attributed and significant, where its 50-step version was +16.0 at p = 0.152: **the model's
subgoals cost 22 episodes in a hundred against the expert's own, with the controller, the
budget and the execution mode all held fixed.**

Two more pairings from the same manifests. **Two stages beat one** by +10.0 (p = 0.27, 9 to
4) -- a comparison that had never had a test. And the +34.0 reproduces to the digit when
computed off the scripted manifest instead of the hand-built one, which is the regression
check on `--write-manifest`.

Records: `results/compare_eval_runs/` tags `subgoal_effect_at_paper_budget`,
`execution_mode_at_paper_budget`, `stages_two_vs_one`,
`oracle_vs_plain_scripted_manifest`.

#### Diagnosis step 4, answered in the environment: the subgoals are wrong, not unreachable (2026-10-01)

`analysis/analyse_acting_npz.py` over all six acting runs' saved `.npz`, per episode, no
GPU. The plan's question was whether a poor subgoal is a **bad** control target or merely a
**hard** one. Medians over the failed episodes of each run, none of which needs a
threshold:

| run | success | failures: progress | MSE to goal | MSE to nearest expert state |
| --- | --- | --- | --- | --- |
| generated, hh1, 50 steps | 34.0 % | 0.22 | 1.599 | 0.848 |
| generated, hh2, 50 steps | 44.0 % | 0.17 | 1.473 | 0.785 |
| **generated, hh2, 100 steps** | 48.0 % | **0.12** | 1.604 | **0.811** |
| oracle, 50 steps | 58.0 % | 0.72 | 0.538 | 0.368 |
| **oracle, 100 steps** | 70.0 % | **0.76** | 0.450 | **0.398** |
| **oracle, low horizon 5** | 26.0 % | 0.67 | 0.572 | **0.138** |

`progress` is `1 - MSE(final, goal) / MSE(start, goal)`: 1 means arrived, 0 means never
moved. Successes sit at 0.92-0.94 in every run.

**The answer is "wrong", and the margin is large.** A failed episode under the expert's
subgoals has still covered **three quarters** of the latent distance to the goal (0.76);
under the model's own it has covered **one eighth** (0.12) -- six times less, on the same
50 episodes, at the same budget, with the same frozen controller. Oracle failures are near
misses. The model's are not failures of tracking at all: the agent never went anywhere
useful.

**And the two levels fail in different directions, which is the cleaner result.** Compare
the bottom three rows, where the only difference is which level was broken:

* break the **high** level (the model's own subgoals): progress collapses to 0.12 and the
  final state sits **0.811** from the nearest point on the expert's whole trajectory;
* break the **low** level (horizon 5 with expert subgoals): progress stays at 0.67 and the
  final state sits **0.138** from the expert's path -- the smallest of all six runs.

So a high-level failure steers the agent **off the expert's path**, and a low-level failure
leaves it **on the path but short**. Both quantities separate the two modes, and neither
needs a cut-off.

**The categorical version of this is threshold-dependent, and that is worth stating.** The
script also bins failures into off-path / stopped-short / reached-the-end against a
threshold on the distance to the nearest expert state, as a fraction of the start-to-goal
distance. Across 0.10 / 0.25 / 0.50:

| run | failures | 0.10 | 0.25 | 0.50 |
| --- | --- | --- | --- | --- |
| generated, hh2, 100 steps | 26 | 21 / 2 / 3 | 18 / 3 / 5 | 13 / 8 / 5 |
| oracle, 100 steps | 15 | 12 / 2 / 1 | 6 / 6 / 3 | 3 / 8 / 4 |
| oracle, low horizon 5 | 37 | 16 / 16 / 5 | 9 / 22 / 6 | 3 / 26 / 8 |

Read as fractions of each run's failures, generated and oracle are **indistinguishable at
0.10** (81 % against 80 % off-path) and separate at 0.25 and 0.50 (69/40, 50/20). The cut at
0.25 happens to fall between their median distances, 0.811 and 0.398, which is what makes
a graded difference look categorical. **The low-horizon contrast is the one that survives
every threshold:** 43 / 24 / 8 % off-path against the oracle's 80 / 40 / 20 %, in the
opposite direction at all three.

So: rest the reading on `progress` and the distance to the nearest expert state. The bins
are a convenience, the script reports them as a sweep, and no claim here depends on a
single cut.

Records: `results/analyse_acting_npz/20261001-1310*.json` [regenerated 2026-10-05 as `20261005-1029*` and `-1030*`, every value identical], one per run, each carrying
`progress_median_failure`, `nearest_mse_median_failure` and
`failure_split_by_threshold`.

**One run cannot be analysed this way at all**, and the script now says so and skips it:
`low_level_reality_gap` runs a separate acting loop per offset block and saves
`offset_<k>_episode_successes` with no `final_latent`
(`hi_acting_diagnostics.py:1289`), so it has neither a single final state nor one success
flag per episode.

#### Retracted the same day: this was first blamed on the low-level horizon (2026-10-01)

For the record, because the reasoning is a trap worth naming. The first version of the
section above claimed the two code paths disagreed on the **low-level horizon** — 2 in
`hi_acting_diagnostics.py:64` (written over the config at `:1057`) against 5 in
`config/eval/hi_pusht.yaml:73` — and put the whole +34 on that, since 2 -> 5 costs 34
points with oracle subgoals held fixed.

**It was wrong.** `colab_hi.ipynb` cell 26 builds every eval command from the authors'
`D50` matrix row, which includes `planning.low.plan_config.horizon=2`. All four runs were
at 2. The claim came from reading the config file instead of the recorded command — and
this file's own provenance paragraph for the 36.0 % run said "low horizon 2" in plain
words.

**What survives from it, and is worth keeping:** the shipped eval config really does say
5, the authors' own matrix row and diagnostics really do use 2, and the difference really
is worth 34 points. So **an eval launched without the matrix-row overrides lands silently
on the worse horizon** — a live trap for any future run, just not one that bit these.
Recorded as a gotcha in `CLAUDE.md`.


### Staged Hi-LeWM-C: 46.0 %, not 64.0 (run 2026-10-01, written up 2026-10-05)

**The paper's largest PushT claim does not reproduce at one seed.** Staged
Hi-LeWM-C at d=50 -- the configuration behind its 64.0 against plain CEM's 38.7,
+25 points -- reaches **46.0 % (23/50)**.

| | ours | paper |
| --- | --- | --- |
| staged Hi-LeWM-C | **46.0 %** (Wilson 95 % 33.0 - 59.6) | 64.0 % |
| online plain CEM | 36.0 % | 38.7 % |
| online Hi-LeWM-C | 34.0 % | 48.7 % |

The paper's 64.0 lies above our 95 % interval. Treated as a fixed target, 23/50
against 0.64 gives an exact binomial p = 0.011; that overstates the case, since the
paper's number is a best-of-sweep value with noise of its own. Treated as 32/50,
Fisher's exact test gives p = 0.11. Either way, what we measure is **about +10
over online plain CEM (Fisher p = 0.42, unpaired)**, not +25.

**The configuration is the canonical one, recorded exactly.** From
`code/outputs/2026-10-01/10-58-05/.hydra/overrides.yaml`: `planning.mode=hierarchical_staged`,
`planning.high.empirical_macro.enabled=true` with the config's own bank defaults
(4096 sequences, `chunk_len` 5, `residual_scale` 0.1, sequence sampling), the D50
matrix row (horizons 2/2, receding 1/1, replan 5, blocks 1/5), the Table 5 budget,
goal budget 100, seed 42, 50 episodes. The rate is from `results/colab/runs_rows.csv`,
fingerprint `sha:cda5c4b65f95`.

**What it cannot support, and why.**

1. **It cannot be paired.** Its per-episode manifest was never copied off Colab.
   It ran the same 50 episodes as every other d=50 eval (same seed, same sampler),
   but which of them it won is unknown, so every comparison above is unpaired and
   correspondingly weak. Its 50 episode videos survive
   (`results/colab/hi_c_staged_seed42_d50_seed42_n50/None/`).
2. **Its solver activation was not audited.** For the online Hi-LeWM-C run the
   stdout showed the empirical solver's banner and 20 `Empirical macro solve time`
   lines. This run's stdout was not saved; the override is recorded, the banner is
   not.
3. **One seed, one row of the sweep.** The paper's 64.0 is the best staged
   configuration it found; the artifact records neither which one nor its bank
   settings (see *Audit of that run* above).

**How it fits the rest.** Staged execution is worth about the same to Hi-LeWM-C
(+12 over its online 34.0) as to plain CEM (+12, *Resolved: the +34 is +22
subgoals and +12 execution mode*), and staged Hi-LeWM-C lands next to the model's
own subgoals under staged execution in the acting diagnostics (48.0 %, a different
code path, so not comparable to the digit). The reading is consistent with
everything above: the empirical bank does not buy control in either execution
mode, and the subgoal gap to the expert's waypoints stays.

## Measured results (PushT, local CPU, no environment)

Run with `analysis/measure_support.py` and `analysis/measure_high_cem.py`, which
drive the artifact's own `calibrate_latent_prior`, `encode_macro_actions` and
`stable_worldmodel.solver.cem.CEMSolver`. No rollouts, so no success rates —
these measure what the planner *searches over*, not how well it controls.

### Headline ratios at the paper budget (authoritative)

**Supersedes every earlier value of support ratio, exploitation ratio and CEM win
rate in this file.** `audit_dimensionality.py --checks draws` at d=50 with the
paper's Table 5 budget (1500 samples x 40 steps, topk 10), 10 draws x 16
segments, for all four variants; paired analysis by `analysis/compare_draws.py`.
Sources: `results/audit_dimensionality/20260921-175756_draws_vq16_vq128_d50.json`,
`results/audit_dimensionality/20260921-194945_draws_d32_d8_d50.json`,
`results/compare_draws/`. Both runs at commit `8e23bd2`, clean tree.

| variant | exploitation (expert cost / CEM cost) | support (CEM / expert Mahalanobis²) | CEM beats expert |
| --- | --- | --- | --- |
| continuous d_l=32 | **x9.5** (x2.6 - x24.7) | **x794** (x576 - x1034) | 81% (69-88%) |
| fixed stride d_l=8 | x3.9 (x1.6 - x10.7) | x1.5 (x1.3 - x2.1) | 75% (62-81%) |
| VQ-128 | x3.6 (x2.5 - x8.0) | x0.9 (x0.7 - x1.1) | 94% (88-100%) |
| VQ-16 | x2.2 (x1.1 - x4.3) | x0.9 (x0.7 - x1.4) | 88% (69-94%) |

Median and range over the 10 draws. Support for VQ is measured on the quantised
selection (`cem-q`), so ~x1 is expected by construction.

**The draws are paired.** Segment sampling is seeded `2000 + k` and depends on
nothing else, so draw *k* uses the same 16 segments in every variant and at every
budget. That makes a paired sign test the right tool, and it is much sharper than
comparing overlapping ranges:

| A vs B, same segments | draws where A exploits more | p (exact two-sided sign test) | median A/B |
| --- | --- | --- | --- |
| d32 vs d8 | **10 / 10** | **0.002** | x2.45 |
| d32 vs VQ-128 | 9 / 10 | 0.02 | x2.56 |
| d32 vs VQ-16 | 9 / 10 | 0.02 | x4.24 |
| d8 vs VQ-128 | 5 / 10 | 1.0 | x0.94 |
| d8 vs VQ-16 | 8 / 10 | 0.11 | x1.57 |
| VQ-128 vs VQ-16 | **10 / 10** | **0.002** | x1.77 |

**Budget effect**, same segments, 20 -> 40 high-level iterations (the 20-iteration
values survive only as 1-decimal text, so both sides are compared at 1 decimal
and exact ties dropped):

| variant | at 20 iterations | at 40 iterations | 40 > 20 | p |
| --- | --- | --- | --- | --- |
| d32 | x5.3 | **x9.5** | 9 of 10 | **0.02** |
| d8 | x4.2 | x3.9 | 6 of 8 (2 ties) | 0.29 |

What this establishes:

1. **Every variant exploits the model.** All four medians are above x1 and CEM
   beats the expert's own actions on 75-94% of segments, including VQ-16.
2. **Leaving the support amplifies exploitation — and the amplification grows
   with the optimisation budget.** d32 exploits most (above every other variant
   here, p <= 0.02), and it is the only one whose exploitation rises when CEM
   gets more iterations (x5.3 -> x9.5, p=0.02) — in step with its support ratio
   rising (x694 -> x794). d8 is stuck in-support and does not respond to budget
   (p=0.29). The mechanism fits the spectrum finding: d32 has 25 near-empty
   directions (after its largest spectral gap) to keep walking into, d8 has one.
   **Qualified 2026-09-22:** "d8" is fixed_stride_dim8, so the d32-vs-d8
   comparison changes d_l and waypoint strategy together, and an earlier version
   of this reading said d32 was "the only variant far outside the data" — false,
   fixed_stride_dim32 is just as far out (x829). fs32 shows the *support* gap is
   a d_l effect but does not isolate support as the cause of the *exploitation*
   gap (see *fixed_stride_dim32* below). The within-model evidence — the budget
   effect here, and the lambda_res sweep — is what supports the amplifier
   reading.
3. **But in-support search still exploits.** d8 (x3.9), VQ-128 (x3.6) and VQ-16
   (x2.2) are all in-support and all exploit. Leaving the support is the
   amplifier, not the cause.
4. **Restriction reduces exploitation at the ends, not smoothly.** d32 exploits
   most and VQ-16 least, each significant, but d8 and VQ-128 are
   indistinguishable (5 of 10). Continuous-but-low-dimensional and
   quantised-with-128-codes restrict the search about equally.
5. **Only quantisation to very few codes gets it low.** VQ-16 < VQ-128 in 10 of
   10 draws — the one comparison that changes nothing but the code count. So
   the tie-collapse measured for VQ-16 comes with lower exploitation.

Caveats: one seed family (draws 2000-2009), 16 segments per draw, d=50 only, one
replan step, no environment. The sign tests are exact but n=10.

### Hi-LeWM-C vs plain CEM — the controlled comparison (authoritative)

**The cleanest comparison in the project: the same d32 checkpoint, the same 16
segments per draw, the same paper budget (d=50, 1500 x 40, topk 10) — only the
high-level search differs.** Hi-LeWM-C is the artifact's own
`EmpiricalMacroActionSolver` over a bank from its own
`build_empirical_macro_action_bank`, built as `eval/hierarchical.py::build_policy`
does, with the shipped defaults: **lambda_res = 0.1, bank = 4096 sequences,
sequence sampling**. Record:
`results/audit_dimensionality/20260922-001913_draws_hilewm_c_d32_d50.json`
(commit `8499b1e`, clean tree); paired analysis `analysis/compare_draws.py`.

That run re-ran d32 too, and it **reproduced the earlier paper-budget d32 record
exactly on all 10 draws** (support, exploitation, win rate), and the expert's
first-waypoint error is identical under both solvers — so the pairing is sound
and the extended script changed nothing it should not have.

| metric (median over 10 draws) | Hi-LeWM-C | plain CEM | plain CEM higher on | p |
| --- | --- | --- | --- | --- |
| support, Mahalanobis² vs expert | **x3.6** | x793 | 10 / 10 | 0.002 |
| support, 1-NN distance vs expert | **x0.95** | x5.3 | 10 / 10 | 0.002 |
| exploitation (expert cost / solver cost) | **x0.83** | x9.5 | 10 / 10 | 0.002 |
| segments where the solver beats the expert | **50%** | 81% | 10 / 10 | 0.002 |
| first-waypoint error ‖ẑ_1 − z_true‖² | **22.1** | 76.4 | 10 / 10 | 0.002 |
| first-waypoint error, expert (reference) | 4.54 | 4.54 | identical | — |

Solve time is the same (293 s vs 295 s per draw).

What this establishes:

1. **Hi-LeWM-C stays in support.** Its selections sit at the expert's own
   nearest-neighbour distance (x0.95). Mahalanobis² is modestly above the expert
   (x3.6), which fits `inspect_empirical_residual.py`: the solver converges to
   bank anchors plus a learned offset, and that offset leaks into the
   near-empty directions a whitened distance is sensitive to.
2. **Hi-LeWM-C does not exploit the model.** Its predicted cost is *worse* than
   the expert's in 7 of 10 draws (median x0.83), and it beats the expert on half
   the segments — a coin flip. It is the only planner we have measured that does
   not mine prediction error. Against plain CEM on the same model, every metric
   separates in 10 of 10 draws.
3. **So yes, keeping the search in support removes exploitation — for this
   model, at lambda_res <= 0.1** (see the sweep below: it returns, mildly, from
   0.3 upward, and stays far below plain CEM throughout). This is the paper's hypothesis tested with the confounds removed,
   and it holds. Together with the budget effect above (plain CEM's
   exploitation grows with iterations, in step with how far it leaves the data),
   it is the strongest evidence we have for the paper's account.
4. **Removing exploitation does not recover expert-quality subgoals.** The
   subgoal is 3.5x better than plain CEM's, but still x5.7 the expert's error
   (plain CEM: x18.4). Hi-LeWM-C looks *search-limited* rather than exploitative:
   its plans score worse than the expert's own actions, consistent with anchors
   re-drawn every iteration that the search can never concentrate on.
5. **"In support" is not by itself enough — the bank is doing something VQ is
   not.** VQ-16 and VQ-128 are also in support, yet exploit x2.2 and x3.6 and
   beat the expert on 88-94% of segments. Hi-LeWM-C, anchored to whole real
   sequences with a small residual, does not. Read this cautiously: the VQ
   numbers come from different predictors, so this is not a controlled
   comparison the way Hi-LeWM-C vs plain CEM is.

**Caveats.** lambda_res = 0.1 is the shipped default; the paper's Hi-LeWM-C
numbers come from a sweep whose settings the artifact does not record, and a
larger residual lets candidates move further from the bank, which would likely
bring exploitation back. The result is therefore conditional on lambda_res until
a sweep is run. Also one seed family (draws 2000-2009), 16 segments per draw,
d=50 only, one replan step, no environment — so nothing here is a success rate,
though the direction agrees with the paper's d=50 online numbers (Hi-LeWM-C 48.7
vs plain Hi-LeWM 38.7).

### The horizon-2 cost/subgoal mismatch is not real — resolved

One of the two candidate explanations listed under *Findings that change the
diagnosis plan* was that the objective is misaligned: with `horizon: 2`,
`get_cost_high` scores the **last** predicted waypoint while the subgoal handed
to the low level is the **first**, so nothing forces a low-cost plan to have a
good first waypoint. It stood open because `corr = +0.425` at n=16 is not
significant.

Measured at n=64, four draws, paper budget, d32
(`analysis/measure_subgoal.py --num-eval 64 --skip-reachability`, seeds
2000-2003; records in `results/measure_subgoal/`, commit `6f93f3c`) [records lost and, by decision, not regenerated on 2026-10-05: this table is text only; see `docs/RECONSTRUCTION.md`]:

| draw | Spearman | Pearson | CEM ẑ_1 error | expert ẑ_1 error |
| --- | --- | --- | --- | --- |
| 0 | +0.623 | +0.620 | 90.89 | 5.31 |
| 1 | +0.652 | +0.457 | 94.23 | 3.64 |
| 2 | +0.567 | +0.574 | 103.40 | 5.45 |
| 3 | +0.566 | +0.562 | 128.79 | 5.62 |

**Median Spearman +0.595, range +0.566 to +0.652, significant in 4 of 4 draws**
(|r| > 0.25 at p=0.05, n=64). Spearman is the estimator to read: both quantities
are heavy-tailed, and draw 1 shows the gap it guards against (+0.652 vs Pearson
+0.457).

**So the objective is not misaligned — it is solidly and consistently aligned.**
A lower terminal cost really does go with a better first waypoint. This candidate
explanation is closed, and the diagnosis narrows to the other one: the terminal
cost itself is being driven below the model's accuracy floor, so an objective
that selects well is being pointed at a number that no longer means anything.

Note the correlation says nothing about subgoal *quality*, which is still bad on
these same draws: the CEM subgoal sits 17-23x the expert's error. Alignment and
accuracy are separate questions and only the first is settled here.

**Caveat:** these are 64-segment draws, so the segments are *not* the 16-segment
draws used everywhere else in this file — `valid_starts` draws a different set
for a different count from the same seed. Do not pair these rows with the
six-draw tables above.

### Axis 2 at the paper budget — five variants, six paired draws (authoritative)

**Supersedes the single-draw tables in *Axis 2 — is the subgoal a usable control
target?* and *Axis 2 across all four variants* below**, which ran at 20
high-level iterations with a low-level budget of 300/20/30. This runs at the
paper's d=50 budget throughout (high 1500 x 40 topk 10, low 900 x 30 topk 150),
adds Hi-LeWM-C as a fifth variant, and reports six paired draws instead of one.
`analysis/run_subgoal_sweep.py` (30 cells, 11 h 20 min, 0 failures) then
`analysis/compare_subgoal_sweep.py`; records in `results/measure_subgoal/` and
`results/subgoal_sweep/20260923-194639_index.jsonl`, analysis in
`results/compare_subgoal_sweep/`. Commit `bdfeec1`, clean tree.

**Two verification gates passed before any number below was read.** The expert's
first-waypoint error is identical for d32 and Hi-LeWM-C on all six draws, so the
two solvers really did see the same segments. And **all 30 cells reproduce the
audit records' exploitation for the same draw, to the audit's one decimal** —
the only independent check available for d8, VQ-128 and VQ-16, whose audit
records predate first-waypoint recording. Exploitation therefore reproduces per
draw, and **the 10-draw audit medians remain the better estimate of it**; what is
new here is axis 2 for all five variants.

Medians over the six draws, range in brackets:

| variant | exploitation | wins | ẑ_1 error | realism MD² | realism NN | reach, relative |
| --- | --- | --- | --- | --- | --- | --- |
| continuous d_l=32 | x10.21 | 78% | 75.10 | 139.01 | 8.19 | 0.08 |
| **Hi-LeWM-C** | **x0.81** | 50% | **30.43** | **178.23** | 8.15 | **0.02** |
| fixed stride d_l=8 | x6.01 | 75% | 61.36 | 112.59 | 8.07 | 0.08 |
| VQ-128 | x3.55 | 94% | 41.92 | 152.37 | **7.09** | 0.03 |
| VQ-16 | x2.37 | 88% | 61.19 | 161.90 | 7.25 | 0.03 |
| *true waypoint (reference)* | | | | *209.74* | *7.40* | *0.01* |

The true-waypoint reference is **identical to two decimals in all five runs**,
which incidentally confirms the frozen pixel encoder is the same in every
checkpoint.

Per-variant references, not comparable across checkpoints:

| variant | model accuracy floor (expert cost) | best achievable subgoal (expert ẑ_1) |
| --- | --- | --- |
| d32 and Hi-LeWM-C | 15.16 | 5.20 |
| fixed stride d_l=8 | 16.27 | 5.73 |
| VQ-128 | 118.90 | 47.14 |
| VQ-16 | 130.24 | 60.25 |

What this establishes:

1. **The two fixes do not work by the same mechanism.** This is the project's
   central question and the answer is now measured. Both reduce exploitation, but
   Hi-LeWM-C does it *without paying in representation accuracy* — it keeps the
   continuous checkpoint's accuracy floor (15.16) and its achievable subgoal
   (5.20), while VQ's are ~8x and ~9-12x worse. VQ buys robustness by throwing
   away the representation; the empirical bank does not.

2. **Achieved / achievable subgoal error, computed per draw then taken as a
   median, separates the two families completely:**

   | variant | achieved / achievable |
   | --- | --- |
   | continuous d_l=32 | **x18.64** (x5.17-x36.05) |
   | fixed stride d_l=8 | x8.37 (x2.35-x15.12) |
   | Hi-LeWM-C | x5.51 (x3.82-x9.54) |
   | VQ-128 | **x0.94** (x0.61-x1.61) |
   | VQ-16 | **x1.02** (x0.57-x1.47) |

   **The VQ planners sit at their representation's ceiling; the continuous ones
   are 5.5 to 18.6 times away from theirs.** That is the axis-1/axis-2 split as a
   single number, and it says exactly what the decoded panels show by eye: for VQ
   the planner is fine and the representation is the limit, for the continuous
   checkpoints the representation is fine and the planner is the limit.
   Hi-LeWM-C closes about two thirds of plain CEM's gap to its own ceiling
   (x18.64 -> x5.51) while keeping the high ceiling. VQ's ratios sitting slightly
   *below* 1 is not a planner beating the expert: the expert reference is itself
   quantised, so it is degraded by the same representation.

3. **Reachability splits into two groups, and the split is not about support.**
   Plain continuous search — d32 *and* d8 — produces subgoals at relative reach
   error 0.08; every constrained search — Hi-LeWM-C, VQ-128, VQ-16 — produces
   0.02-0.03, against 0.01 for a true waypoint. Each cross-group pair separates
   6 of 6 (p=0.031: d32 vs Hi-LeWM-C x4.64, d32 vs VQ-128 x3.46, d8 vs VQ-128
   x3.75) while **d32 vs d8 ties exactly (3 of 6, p=1.0)** — although d8 is
   in-support and d32 is x800 outside it. So what makes a subgoal hard to reach
   is not whether the *macro-action* was in support, but whether the search was
   constrained to real sequences or a codebook.

4. **Every variant's subgoal is over-smoothed, and Hi-LeWM-C is the least so.**
   All five Mahalanobis² medians sit below the true waypoint's 209.74, i.e. all
   are closer to the centre of the frame distribution than a real frame is.
   Hi-LeWM-C is highest at 178.23 and beats every other variant 6 of 6
   (p=0.031); fixed stride d_l=8 is the most over-smoothed at 112.59. Regression
   to the mean is therefore a property of the *search* as much as the predictor:
   the same predictor, searched differently, gives 139.01 under plain CEM and
   178.23 under the bank.

5. **VQ subgoals are the closest to an individual real frame** (nearest-frame
   7.09 and 7.25, against 8.07-8.19 for the rest; VQ-128 beats d32 6 of 6). Put
   with reading 2, that is "sharp but wrong", which is exactly how the decoded
   VQ-16 panel reads.

6. **At d=50, d_l=8's in-support search buys nothing on axis 2.** d32 vs d8
   separates on exploitation (6 of 6, x1.68) and on nothing else: subgoal error
   (4 of 6, p=0.69), nearest-frame distance (3 of 6, p=1.0) and reachability
   (3 of 6, p=1.0) all tie. This is consistent with the paper scoring them
   46 / 42 at d=50, within its own noise.

**Caveats.** Six draws, one seed family (2000-2005), 16 segments per draw, d=50
only, one replan step, no environment — so none of this is a success rate. The
d32 reachability range (0.05-0.60) is driven by one bad draw. The
achieved/achievable ratio divides two quantities measured on the same segments,
which makes it comparable across checkpoints, but it says nothing about whether
a low ceiling and a high one are worth the same in the environment.

### fixed_stride_dim32 — separating d_l from the waypoint strategy

What we have been calling "d8" is `fixed_stride_dim8`. Against the main d32
checkpoint it changes two things at once:

| checkpoint | d_l | waypoint strategy |
| --- | --- | --- |
| main ("d32") | 32 | random_sorted, 5 waypoints |
| fixed_stride_dim32 ("fs32") | 32 | fixed stride 5, 4 waypoints |
| fixed_stride_dim8 ("d8") | 8 | fixed stride 5, 4 waypoints |

(From each run's shipped `config.yaml`; all 15 epochs. Both fixed-stride models
were trained with stride 5 tokens — exactly the 5-token macro-action span used
throughout, so the d8 measurements were never off-distribution.)

So fs32 vs d32 isolates the strategy and fs32 vs d8 isolates d_l. 10 paired draws
at the paper budget (`results/audit_dimensionality/20260922-114851_draws_fs32_d50.json`,
commit `a128dcb`, clean tree):

| metric (median) | d32 | fs32 | d8 |
| --- | --- | --- | --- |
| support, Mahalanobis² | x793 | **x829** | x1.5 |
| support, 1-NN | x5.3 | x4.3 | — |
| exploitation | x9.5 | **x6.4** | x3.9 |
| solver beats expert | 81% | 88% | 75% |
| first-waypoint error, solver | 76.4 | 82.4 | — |
| first-waypoint error, expert | 4.5 | 5.7 | — |

("—": d8's audit record predates 1-NN and first-waypoint recording.)

| paired sign test (draws where the first is higher) | support | exploitation | wins | first-waypoint error |
| --- | --- | --- | --- | --- |
| strategy — d32 vs fs32 | 3/10, p=0.34 | 8/10, p=0.11 | 3/10, p=0.73 | 4/10, p=0.75 |
| d_l — fs32 vs d8 | **10/10, p=0.002** | 8/10, p=0.11 | **8/10, p=0.039** | — |

What this establishes:

1. **Leaving the support is a d_l effect.** At d_l = 32 the search goes ~x800 out
   whichever waypoint strategy trained the model; at d_l = 8 it stays in. This
   matches the spectra: fs32, like d32, pads a handful of used dimensions with
   20-odd near-empty ones.
2. **The waypoint strategy changes nothing measurable** — support, win rate and
   subgoal error all tie between d32 and fs32.
3. **The exploitation gap between d32 and d8 is not cleanly attributable.** fs32
   sits in between (x6.4 vs x9.5 and x3.9) and neither step is significant on 10
   draws. In particular fs32 is as far out of support as d32 yet does not
   exploit detectably more than the in-support d8. So across models, support
   distance alone does not predict exploitation; the controlled evidence for
   "support amplifies exploitation" is the within-model manipulations.
4. It squares with the paper: fixed stride at d_l 32 and at d_l 8 score the same
   (42 / 20) despite a ~500-fold difference in support distance here — one more
   sign that support distance does not map straight onto success.

### lambda_res sweep — how far the Hi-LeWM-C result depends on the residual scale

The caveat on the section above, measured. lambda_res 0.05, 0.3 and 1.0 at 6
draws each; lambda_res 0.1 and plain CEM taken from the 10-draw run and **cut to
the same 6 draws** (seeds 2000-2005), so every row describes the same segments.
Paired analysis `analysis/compare_draws.py`; records
`results/audit_dimensionality/*_draws_hilewm_c_lam{0.05,0.3,1}_d50.json`.
Pairing check passed: the expert's first-waypoint error is identical in every
condition. Six draws because a paired sign test on five cannot get below p=0.0625;
with six the floor is p=0.031, which every "6 of 6" below reaches.

| condition (d32 checkpoint) | support, Mahalanobis² | support, 1-NN | exploitation | draws with exploitation > 1 | solver beats expert | first-waypoint error |
| --- | --- | --- | --- | --- | --- | --- |
| Hi-LeWM-C, lambda_res 0.05 | x1.6 | x0.97 | **x0.73** | 1 / 6 | 47% | 30.9 |
| Hi-LeWM-C, lambda_res 0.1 | x3.7 | x1.00 | **x0.81** | 1 / 6 | 50% | 30.4 |
| Hi-LeWM-C, lambda_res 0.3 | x22.5 | x1.31 | x1.16 | 5 / 6 | 62% | 26.8 |
| Hi-LeWM-C, lambda_res 1.0 | x242 | x2.65 | x1.85 | 6 / 6 | 72% | 33.3 |
| plain CEM | x851 | x5.77 | **x10.2** | 6 / 6 | 78% | 75.1 |
| expert (reference) | | | | | | 5.2 |

Paired sign tests, 6 draws:

| comparison | support | exploitation | first-waypoint error |
| --- | --- | --- | --- |
| 0.1 vs 0.05 | 6/6, p=0.031 | 5/6, p=0.22 | 2/6, p=0.69 |
| 0.3 vs 0.1 | 6/6, p=0.031 | **6/6, p=0.031** | 2/6, p=0.69 |
| 1.0 vs 0.3 | 6/6, p=0.031 | 5/6, p=0.22 | 4/6, p=0.69 |
| plain CEM vs each lambda_res | 6/6, p=0.031 (all four) | 6/6, p=0.031 (all four) | 6/6, p=0.031 (all four) |

What this establishes:

1. **"Hi-LeWM-C does not exploit the model" is true only for lambda_res <= 0.1.**
   Exploitation crosses x1 between 0.1 and 0.3 — the one step where it rises in
   6 of 6 draws — and at 0.3 and 1.0 the solver beats the expert's predicted
   cost in most draws. The earlier caveat was right to worry.
2. **But Hi-LeWM-C exploits far less than plain CEM at every value tested.** Even
   at lambda_res 1.0, where its selections sit x242 outside the data, it exploits
   x1.85 against plain CEM's x10.2, and plain CEM exceeds it in 6 of 6 draws.
   This part does not depend on lambda_res.
3. **Exploitation follows support distance under a controlled manipulation.**
   Only lambda_res changes, on the same model and segments, and support rises
   monotonically (every step 6/6) while exploitation rises with it
   (x0.73 -> x0.81 -> x1.16 -> x1.85 -> x10.2 for plain CEM). Together with the
   budget effect above, this is dose-response evidence for the paper's
   hypothesis. The relation is strongly non-linear: support grows ~500-fold
   across the range while exploitation grows ~14-fold.
4. **Subgoal quality does not track exploitation once exploitation is small.**
   First-waypoint error is flat across lambda_res (26.8-33.3, no adjacent
   difference significant) while exploitation more than doubles. It beats plain
   CEM at every value (6 of 6) and stays ~5-6x the expert's throughout. So the
   remaining gap to the expert is not exploitation; bringing exploitation from
   x1.85 down to x0.73 buys no better subgoal. The likelier culprits are the
   search itself (anchors re-drawn every iteration) and the predictor's own
   error, which this measurement cannot separate.
5. **Correction to our own reading.** An eyeball comparison suggested lambda_res
   0.1 was optimal for subgoal quality (22.1 vs 26.8-33.3). That compared a
   10-draw median against 6-draw medians; on the same six draws 0.1 gives 30.4
   and nothing separates. There is no optimum in this data.

Caveats: 6 draws per value, one seed family, d=50, one replan step, no
environment. Which lambda_res the paper's Hi-LeWM-C numbers used is still
unknown, so we cannot say which regime their 48.7% reflects.

### Support distance — the main test of the paper's hypothesis

Main checkpoint, d=50, horizon 2, 1500 samples x 20 CEM steps, 16 segments
(32 macro-actions per population), 4096 reference macro-actions, seed 42.
Reference and expert spans follow the artifact's recipe exactly: eval-time
`StandardScaler`, episode-boundary-safe contiguous spans, 5 primitive actions
grouped per token, 5 tokens (25 primitive steps) per macro-action.

| population | Mahalanobis² median | p90 | nearest-neighbour median | p90 |
| --- | --- | --- | --- | --- |
| expert (in-support, and the right answer) | 22.9 | 36.5 | 2.23 | 3.04 |
| CEM-selected | 23355 | 41949 | 12.08 | 16.70 |
| CEM prior, N(0, I) | 6403 | 11028 | 12.05 | 13.32 |

Reading it:

1. **The hypothesis holds, and not narrowly.** Selected macro-actions sit far
   outside the training distribution. **Corrected 2026-09-21** by
   `analysis/audit_dimensionality.py`: the x1019 first written here was a single
   segment draw and sat near the top of the range. Over 10 independent draws the
   ratio is **median x759, range x517-x1081**, with expert MD² 21.5-32.5 and CEM
   MD² 13550-24160. **Quote the reference-free figure instead — CEM MD² is x611
   the chi²(32) median** — because it does not depend on how tight the expert
   sample happens to be on a given draw. Nearest-neighbour distance is 5.4x the
   expert's on the original draw. The ridge on the covariance was also checked
   and is not manufacturing this: at ridge 0 the ratio is x1064 against x1019 at
   the 1e-4 we use, so the regularisation slightly *shrinks* it.
2. **Optimisation makes it worse, not better.** CEM ends 3.6x further out than
   its own starting prior (23355 vs 6403). The search does not merely begin
   off-manifold, it walks further off as it minimises predicted terminal cost —
   which is what exploiting an unconstrained learned model looks like.
3. **It moves along directions the data barely varies in.** Nearest-neighbour
   distance is essentially identical for CEM and prior (12.08 vs 12.05) while
   Mahalanobis² differs 3.6x, so the extra distance is in low-variance
   directions of the macro-action distribution — invisible to a Euclidean
   measure, heavily penalised by a whitened one. Report both.
4. **The starting distribution is already far outside the data.** N(0, I) gives
   Mahalanobis² 6403 against the encoded macro-action cloud. Calibrating the
   prior is exactly what `calibrate_latent_prior` computes — and exactly what
   `CEMSolver` throws away (see the retraction above). That connects the two
   findings: the fix the artifact already contains is never applied.

Sanity check on the reference: expert Mahalanobis² median is 22.9 against a
chi²(32) median of 31.3, so the reference statistics are well behaved and the
expert population is, if anything, slightly tighter than the reference sample.

**Audited 2026-09-21** — see `analysis/audit_dimensionality.py`, which exists
because the numbers behind the dimensionality claim originally came from an
inline snippet that was never saved and therefore could not be re-checked. Every
reported number now has a runnable source. The audit changed three figures
(x1019 -> x759, "~5 dimensions" -> 5-7, "27 empty directions" -> 25) and left
the conclusions intact. It also confirmed two things that could have gone the
other way: the covariance ridge is not manufacturing the result (ridge 0 gives a
*larger* ratio), and drawing the reference and expert rows from disjoint
episodes does not shrink it (expert MD² 26.1 disjoint vs 28.7 overlapping).
What it cannot rule out is the macro-action encoder having memorised these
spans — the dataset is its training set and no held-out split is available.

**Caveat: one seed, 16 segments, 32 macro-actions per population.** Enough to
establish the effect — the gap is three orders of magnitude, not a few percent —
but the presentation numbers need more segments and >=3 seeds, and d=25/75
alongside d=50.

### Why d_l=32 leaves the support and d_l=8 does not

Same measurement across variants, each read against its own expert row
(Mahalanobis² is whitened per checkpoint, so only the ratios compare):

| variant | ambient d_l | CEM vs expert, Mahalanobis² | note |
| --- | --- | --- | --- |
| continuous | 32 | **x759** (range x517-x1081 over 10 draws) | far outside |
| fixed stride | 8 | **x1.6** (x1.1-x2.1 over 10 draws) | essentially inside |
| VQ-128 | 16, quantised | x0.9 | inside by construction |
| VQ-16 | 16, quantised | x1.0 | inside by construction |

My first explanation — that the d_l=8 encoder happens to output unit-scale
latents so the N(0, I) prior lands well — was **wrong**. Measured scales are
comparable, and d_l=8 actually has the *larger* per-dimension spread:

| variant | mean ‖z‖ | mean per-dim std | Mahalanobis² of N(0, I) | chi²(d) median |
| --- | --- | --- | --- | --- |
| continuous d32 | 13.73 | 2.09 | 7675 | 31.3 |
| fixed stride d32 | 14.96 | 2.31 | 8389 | 31.3 |
| fixed stride d8 | 10.23 | 3.30 | 6.0 | 7.3 |

The real mechanism is the covariance spectrum. **Both encoders use about the
same number of dimensions; what differs is how many near-empty ones surround
them.**

**Corrected 2026-09-21.** An earlier version of this entry said "a roughly
5-dimensional manifold" with "27 empty directions" at d_l=32 and "3" at d_l=8.
Both numbers were wrong. "5" was the participation ratio, the lowest of several
defensible estimators, quoted without saying which; and the empty-direction
counts came from subtracting that soft estimate from the ambient dimension,
which conflates an effective dimension with a hard count. Re-derived with
`analysis/audit_dimensionality.py`:

| estimator | continuous d32 | fixed stride d8 |
| --- | --- | --- |
| participation ratio | 4.95 (95% CI [4.88, 5.00]) | 4.67 ([4.60, 4.73]) |
| spectral entropy | 5.81 ([5.77, 5.86]) | 5.57 ([5.52, 5.62]) |
| 95% of variance | 6 ([6, 6]) | 6 |
| 99% of variance | 7 | 7 |
| largest spectral gap after | 7 (x8.3 drop) | 7 (x7.8 drop) |

So **say 5-7 and name the estimator**; the sampling error is negligible
(identical to two decimals from n=256 to n=16384), and all the spread is in the
choice of estimator.

The counts of near-empty directions, read off the spectra rather than inferred.
**Corrected 2026-09-22:** this table first listed d32 as "8 dims above 0.4, 25
below", which sums to 33 for a 32-d latent — it mixed two definitions. Both are
now given explicitly (`analysis/compare_draws.py`, from the spectrum record
`results/audit_dimensionality/20260922-114829_spectrum_estimators_d32_d8_fs32_d50.json`);
**"25 near-empty" means the dimensions after the largest spectral gap.**

| variant | largest gap after dim | used / near-empty (by gap) | tail variance | used / near-empty (by eigenvalue 0.4) | tail variance | condition number |
| --- | --- | --- | --- | --- | --- | --- |
| continuous d32 | 7 (x8.3 drop) | 7 / **25** | 0.65% | 8 / 24 | 0.34% | 7.0e4 |
| fixed stride d8 | 7 (x7.8 drop) | 7 / **1** | 0.37% | 7 / 1 | 0.37% | 8.8e1 |
| fixed stride d32 | 9 (x21.6 drop) | 9 / **23** | 0.14% | 9 / 23 | 0.14% | 1.1e5 |

fixed_stride_dim32 looks like d32, not like d8: a handful of used dimensions
(participation ratio 4.85, CI [4.78, 4.91]; spectral entropy 6.01) and 23
near-empty ones. So the padding is a property of d_l = 32, whatever the
waypoint strategy.

The two spectra are near-identical in shape over their leading dimensions —
d32 runs 43.1, 37.5, 21.0, 18.8, 14.6, 6.55, 3.86 and d8 runs 29.3, 23.1, 11.6,
9.59, 7.84, 5.00, 2.61 — and then d32 falls off a cliff to 0.47 and trails 25
dimensions down to 6.1e-4, while d8 has one dimension left at 0.33. **The
difference between the two models is almost entirely the padding.** An N(0, I)
prior puts unit variance into every one of those 25 near-empty directions, which
is where Mahalanobis² in the thousands comes from. At d_l=8 there is only one
such direction and it still has eigenvalue 0.33, so an uncalibrated prior lands
in-support by accident.

Three consequences:

1. **Out-of-support search is about excess ambient dimensions, not scale.**
   A useful macro-action needs 5-7 dimensions; d_l=32 gives it roughly 4-6x more
   room than it uses.
2. **A per-dimension box could not have fixed this even if it were applied.**
   `calibrate_latent_prior` produces an axis-aligned box; a 5-7 dimensional
   structure inside 32-d is not an axis-aligned box. This is the intuition the retracted note
   above had right while getting the mechanism wrong.
3. **It explains why VQ removes the problem completely.** A codebook is a
   discrete approximation of that manifold, so a quantised candidate is on it by
   construction.

### VQ: in-support by construction, so the failure must be elsewhere

Measured with `cem-q`, the selected vectors after
`quantize_macro_actions_for_planning` — which is what `rollout_high` actually
feeds the predictor. Raw selected vectors look far out (VQ-16 x840) but that
number is meaningless: the solver searches continuous R^16 and only the rollout
quantises, so comparing raw output against a quantised reference is apples to
oranges.

| | cem-q vs expert (Mahalanobis²) | nearest neighbour | selections on a code the data uses |
| --- | --- | --- | --- |
| VQ-16 | x1.0 | 0.000 | 100% |
| VQ-128 | x0.9 | 0.000 | 100% |

Code usage over the evaluated segments (d=50):

| | codes used by reference | by expert | by CEM | CEM perplexity |
| --- | --- | --- | --- | --- |
| VQ-16 | 16 / 16 | 13 | **8** | 6.7 (expert 10.6) |
| VQ-128 | 66 / 128 | 22 | 23 | 19.9 (expert 19.9) |

So for both VQ variants the out-of-support hypothesis is **void**: every
selection is a learned code, and every code is one the training data uses. What
separates them is expressiveness and the tie problem — VQ-16's CEM collapses
onto 8 distinct codes and 5 distinct costs, while VQ-128 matches the expert's
code diversity exactly (perplexity 19.9 vs 19.9). Half of VQ-128's codebook is
unused even by the training data (66 of 128), which is the collapse noted above.

### Axis 2 — is the subgoal a usable control target? (single draw, superseded)

`analysis/measure_subgoal.py`, main checkpoint, d=50, horizon 2, 16 segments,
seed 42. High CEM at 1500x20, low CEM at 300x20 over the first stage
(5 tokens = 25 primitive steps).

**Model exploitation is the dominant effect.** The expert's own macro-actions
demonstrably reach `z_goal`, so the cost the model assigns them is its accuracy
floor on real trajectories:

| | predicted terminal cost ‖ẑ_H − z_goal‖², median | p90 |
| --- | --- | --- |
| expert macro-actions | 34.39 | 209.27 |
| CEM-selected | **2.16** | 72.29 |

CEM drives the predicted cost below the model's own error on real data and
"beats" the expert on most segments. Anything under the expert's cost is the
optimiser mining prediction noise, not finding a better plan.

**Corrected 2026-09-21.** The single draw above gave x15.9 and 94%, and both
were written up as headline figures. Over 10 independent draws
(`audit_dimensionality.py --checks draws`, results in
`results/backfill/2026-09-19_session/audit__draw_intervals_exploitation_and_support.txt`):

| | median | range over 10 draws |
| --- | --- | --- |
| exploitation ratio (expert cost / CEM cost) | **x5.4** | x0.7 - x10.6 |
| segments where CEM "beats" the expert | **78%** | 62% - 88% |
| expert cost (the model's accuracy floor) | 14.9 | 9.9 - 27.5 |

The original draw's expert cost of 34.4 sits above every one of the ten, which is
what inflated its ratio. Exploitation is real and typical — nine draws of ten are
above x1 — but it is about x5, not x16, and **one draw in ten shows none at the
median** (x0.7: CEM's predicted cost 16.0 against the expert's 11.7).

**The subgoal that comes out is much worse than the expert's**, though the
objective is not actively misaligned:

| first waypoint vs the true intermediate frame | squared error, median |
| --- | --- |
| expert-rolled ẑ_1 | 6.59 |
| CEM ẑ_1 | **83.67** (12.7x worse) |

`corr(terminal cost, first-waypoint error) = +0.425`. Positive means lower cost
does go with a better subgoal, so the horizon-2 cost/subgoal mismatch is *not*
catastrophic on this evidence. But n=16 makes this underpowered (r=0.425 at
n=16 is not significant), so treat it as unresolved and re-measure with more
segments before claiming either way.

**The subgoal is over-smoothed, not hallucinated.** Against 1024 encoded real
frames in R^192:

| | Mahalanobis² median | nearest real frame, median |
| --- | --- | --- |
| true waypoint | 214.88 | 6.16 |
| expert-rolled ẑ_1 | 190.54 | 6.97 |
| CEM ẑ_1 | **127.88** | **8.91** |

Note the direction: the CEM subgoal is *closer to the centre* of the frame
distribution than a real frame is (chi²(192) median is 191, and 127.88 is well
below it) while being *further from any individual frame*. That is regression to
the mean, which is what an MSE-trained predictor does — the subgoal is a blurry
average of plausible futures rather than a wild hallucination. This is the
prediction to check with the decoder probe, and it is the figure for the interim
slide.

**And it is measurably harder to reach.** Low-level CEM run toward each target,
scored by the model's own `rollout_low`:

| target | residual ‖ẑ_low − target‖², median | relative |
| --- | --- | --- |
| true waypoint | 1.90 | 0.008 |
| CEM subgoal | 14.15 | 0.093 |

So the subgoal is both bad *and* harder to hit — 7.4x the residual, 12x the
relative error. Not unreachable in absolute terms (9% relative), so "bad target"
weighs more than "unreachable target", but both are present.

### Axis 2 across all four variants — the central comparison (single draw, superseded)

Same script, same 16 segments, same seed, d=50. This is the measurement that
answers the project's key question: *do the two fixes work by the same
mechanism?*

| variant | search space | exploitation ratio | CEM "beats" expert | model accuracy floor (expert cost) | best achievable subgoal (expert ẑ_1 error) | actual subgoal error | reach residual (relative) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| continuous d_l=32 | R^32 | **x5.4** (x0.7-x10.6)† | 78% (62-88%)† | 34.4 | 6.6 | 83.7 | 0.093 |
| fixed stride d_l=8 | R^8 | **x4.3** (x1.8-x8.8)† | 75% (62-81%)† | 44.9 | 6.7 | 106.8 | 0.088 |
| VQ-128 | 128 codes | **x5.7** | 100% | 167.0 | 38.8 | 63.9 | 0.038 |
| VQ-16 | 16 codes | **x1.8** | 81% | 165.9 | 45.8 | 70.1 | 0.033 |

† Median and range over 10 independent draws, audited 2026-09-21. The VQ rows
and every other column are still **single draws** and should be treated as
provisional until they get the same treatment.

Five readings, in decreasing order of confidence:

**Readings 1 and 2 are superseded by *Headline ratios at the paper budget*
above.** They were written against 20-iteration numbers and went through two
revisions in one day; kept here, struck through in substance, so the history is
visible:

1. *First* "restricting the search reduces exploitation monotonically,
   15.9 -> 5.9 -> 5.7 -> 1.8" (single draws); *then* withdrawn when 10 draws at
   20 iterations put d32 and d8 at x5.4 and x4.3 with overlapping ranges; *now*
   **partly restored**: at the paper budget the ends are significant
   (d32 > everything, VQ-128 > VQ-16) and the middle ties (d8 = VQ-128).

2. *First* "exploitation is not the same thing as out-of-support search";
   *then* strengthened to "largely decoupled from support — a ~400-fold support
   difference buys no detectable difference in exploitation"; *now*
   **retracted in that strong form**. At the paper budget d32 exploits more than
   d8 on the same segments in 10 of 10 draws. What survives is the weak form:
   in-support search still exploits, so leaving the support is the amplifier,
   not the only route. The 20-iteration budget had simply not let d32 walk far
   enough out for the difference to show.

3. **Quantisation buys robustness by destroying accuracy.** The VQ predictors
   are ~4x worse at predicting the expert's own next waypoint (accuracy floor
   167 and 166, against 34 and 45 for the continuous variants), because a
   quantised macro-action simply carries less information. VQ trades
   exploitability for expressiveness — that is the trade-off to put on a slide.

4. **The VQ planners are near-optimal inside their own representation; the
   continuous ones are far from it.** Ratio of the achieved subgoal error to the
   best achievable with that representation: VQ-128 1.6x, VQ-16 1.5x, versus
   continuous d_l=32 12.7x and fixed stride d_l=8 16.0x. The VQ planners are
   doing nearly as well as their representation permits. It just does not permit
   much.

5. **VQ subgoals are more realistic and easier to reach**, consistent with 3-4:
   nearest real frame 6.8-7.6 versus 8.9-9.1, and relative reach error 0.033-0.038
   versus 0.088-0.093.

**What this does not explain, and should not be stretched to.** Single-step
subgoal quality does not rank-order the paper's d=50 success rates (46 / 42 / 44
/ 38 for the four rows above). It would be overfitting to try: those four
numbers sit inside a ~7-point standard error at 50 episodes, so they are
effectively tied except possibly VQ-16. Our measurement is also one replan step,
while success comes from a full receding-horizon rollout. Treat the mechanism
findings as solid and the mapping to success rates as unestablished.

**Caveats for all of the above:** 16 segments, one seed, d=50 only, one replan
step, no environment. The effects here are large multiples rather than a few
percent, but the presentation needs >=3 seeds, more segments, and d=25/75.

### Decoded subgoals — the blur is in the prediction, not the probe

`analysis/render_subgoals.py`, main checkpoint, d=50, 6 segments, seed 42,
Phase B probe (`pred_exposed`; Phase A is `true_only` and has never seen a
predicted latent, so decoding predictions with it would conflate a bad
prediction with an out-of-distribution probe input — it is rendered too, as a
check, and tells the same story).

The panel has six columns so probe error and prediction error can be separated:
raw `frame t`, `probe(z_t)`, `probe(z_true)`, `probe(expert ẑ_1)`,
`probe(CEM ẑ_1)`, `probe(z_goal)`.

**The control works and it matters.** Column 2 (`probe(z_t)`, an encode-decode
round trip of a real frame) is essentially as sharp as column 1. So the probe is
not the source of blur, and everything soft further right is the *predictor*.

What the panel shows:

- `probe(expert ẑ_1)` is already visibly blurred. Even with the expert's own
  macro-actions, φ does not produce a sharp waypoint.
- `probe(CEM ẑ_1)` is much worse: on several segments the manipulated T-block is
  a diffuse grey cloud rather than a block, and on two of six it is barely
  recognisable as a shape at all.
- **The static green target stays sharp in every column while the manipulated
  grey T smears.** What is uncertain blurs, what is fixed does not. That is
  regression to the mean, visible directly, and it confirms the Mahalanobis
  reading above — closer to the centre of the frame distribution, further from
  any individual frame.

PSNR/SSIM against `probe(z_true)`, with the probe's blur divided out:

| | PSNR | SSIM |
| --- | --- | --- |
| probe(expert ẑ_1) | 30.27 | 0.970 |
| probe(CEM ẑ_1) | 27.10 | 0.951 |
| probe(z_t) — "stay put" control | 23.53 | 0.933 |

The ordering is right — the CEM subgoal beats standing still and loses to the
expert prediction — but **do not lean on these numbers**. PushT frames are
mostly white background, so SSIM sits above 0.93 for everything including a
smeared cloud. The image is the evidence; the metric is a sanity check.

Rendered for all four variants, the same panel makes the trade-off visible:

| variant | probe(expert ẑ_1) PSNR | probe(CEM ẑ_1) PSNR | gap |
| --- | --- | --- | --- |
| continuous d_l=32 | 30.27 | 27.10 | **-3.17** |
| fixed stride d_l=8 | 29.90 | 26.78 | **-3.12** |
| VQ-128 | 27.77 | 27.64 | -0.13 |
| VQ-16 | 26.98 | 27.83 | **+0.85** |

The gap column is the planner's contribution; the expert column is the
representation's ceiling. Continuous variants have the higher ceiling (~30 dB)
and lose ~3 dB to the planner. VQ variants have a lower ceiling (~27 dB) and
lose nothing — VQ-16's CEM subgoal even edges past the expert's, though at 6
segments that is within noise.

The panels show the same thing. For the continuous checkpoint, column 4 (expert)
is passable and column 5 (CEM) is a grey smear — *the planner is the problem*.
For VQ-16, columns 4 and 5 look alike and both are mediocre — *the
representation is the problem*. That is the axis-1/axis-2 split rendered as an
image, and it is the second slide.

This is the interim-presentation figure.

#### All 16 rows (2026-09-22, later) — supersedes the 6-row panels below

The d32 + Hi-LeWM-C and VQ-16 panels were re-rendered with all sixteen segments
of draw 0 (`--rows 16`), fixing the representativeness problem described below:
shown and full-draw medians are now the same thing, and the audit cross-check
held again to the digit (expert 10.02, plain CEM 51.80, Hi-LeWM-C 38.31; VQ-16
73.69 / 76.85). The 16-row files overwrote the 6-row ones of the same name —
`render_subgoals.py` now puts the row count in the file name so that cannot
recur. The d8 and VQ-128 panels are still 6 rows.

By eye, which is not a measurement: in about half of the sixteen rows plain CEM's
subgoal dissolves the grey T into a smear; Hi-LeWM-C keeps a recognisable, blurred
block in most of those; and in one row (12) it is the other way round. Over 16
rows Phase-B PSNR is expert 28.63, Hi-LeWM-C 26.76, plain CEM 26.25 — the right
order now, but still a small spread next to the latent error (38.3 vs 51.8). The
VQ-16 panel keeps its reading: expert and CEM columns alike, crisp but often
closer to the start than to the true waypoint.

#### Re-rendered at the paper budget, with Hi-LeWM-C (2026-09-22) — superseded by the 16-row panels above

`render_subgoals.py --draw 0 --rows 6`, d=50, 1500 x 40. Output
`analysis/figures/subgoals_*_d50_draw0*.png` (gitignored; regenerate with the
records in `results/render_subgoals/`). The d32 panel has seven columns — frame t,
probe(z_t), probe(z_true), probe(expert), probe(plain CEM), **probe(Hi-LeWM-C)**,
probe(z_goal) — so the controlled comparison is one image: same model, same
segments, only the search differs. The 20-iteration panels above are superseded.

**The panel shows the audited subgoals, verified.** `--draw 0` re-solves audit
draw 0 exactly (16 segments, solver seed 2000, batch size 4) and prints the
16-segment first-waypoint error. For d32 it reproduces the audit record to the
digit: expert 10.02, plain CEM 51.80, Hi-LeWM-C 38.31. For d8 and VQ there is no
such check: their audit records predate first-waypoint recording. They run the
same code path, but that is not the same as verified.

**⚠️ The six rows shown are not representative of their draw.** They are the
first six of draw 0's sixteen segments by row index — deterministic, not chosen
— but they happen to be hard for plain CEM:

| first-waypoint error, median | 6 rows shown | all 16 segments of draw 0 |
| --- | --- | --- |
| expert | 6.7 | 10.0 |
| plain CEM | **140.9** | 51.8 |
| Hi-LeWM-C | 40.1 | 38.3 |

So the panel overstates plain CEM's failure for this draw by about 2.7x. Say so on
the slide, or render all sixteen rows.

What the d32 panel shows: in two of the six rows (2 and 6) plain CEM's subgoal
dissolves the grey T into a smear while Hi-LeWM-C keeps a recognisable, blurred
block; in the other four the two look similar. **PSNR does not separate them**
(Phase B: plain CEM 27.20, Hi-LeWM-C 27.05) while the latent first-waypoint error
does (51.8 vs 38.3 over 16 segments; 3.5x over 10 draws). The white background
dominates the pixel metric, as noted above — here it is not merely weak but
uninformative.

The VQ-16 panel keeps its earlier reading — the expert and CEM columns look
alike (16-segment error 73.7 vs 76.9), so the limit is the representation — and
adds one: its predictions are *crisper* than d32's plain-CEM smears, but in
several rows the T sits closer to where it started than to the true waypoint.
Sharp but wrong, rather than blurred, which fits VQ's roughly 4x worse accuracy
floor. VQ-128 is similar (66.4 vs 62.1). Fixed-stride d8: expert 26.0, CEM 61.0.

### Synthesis so far

The paper's hypothesis is right for the checkpoint it was framed around, and the
mechanism is sharper than "searches anywhere": at d_l=32 the search has 27
unused ambient dimensions to wander into, and CEM walks *further* out as it
optimises. But **being in-support does not by itself buy performance** — fixed
stride d_l=8 is in-support and scores 42/20 against continuous d_l=32's 46/20,
and both VQ variants are perfectly in-support while VQ-16 is the worst of the
four. So the diagnosis needs a second axis, measured above: whether the selected
macro-action *yields a good control target*. It does not. The chain that the
measurements support, end to end:

1. At d_l=32 the macro-action distribution occupies 5-7 effective dimensions of
   32, leaving 25 near-empty ones, and the CEM prior ignores that geometry.
2. CEM walks further out of support as it optimises (x3.6 beyond its own prior).
3. It finds plans the model scores **~x9.5** better than the expert's own
   actions (paper budget, median over 10 draws, x2.6-x24.7) — below the model's
   accuracy floor, so it is mining prediction error. *16x (one draw), then x5.4
   (10 draws at half the budget), now x9.5 at the budget the paper uses.*
4. The first predicted waypoint is then an over-smoothed average, 12.7x further
   from the true intermediate state than the expert's, closer to the centre of
   the frame distribution than any real frame.
5. The low level gets 7.4x further from that target than from a real one.

Axis 1 explains the continuous d_l=32 checkpoint. It does **not** explain
fixed-stride d_l=8 or the VQ variants, which are in-support and still do not
win. Axis 2 carries that part. At the paper budget, every variant exploits the
model; leaving the support **amplifies** it, and is the only thing that makes it
grow with optimisation budget (d32: x5.3 -> x9.5 when iterations double; d8
flat) — shown within models, by the budget effect and the lambda_res sweep; the
across-model contrast with d8 is confounded with waypoint strategy and fs32 does
not settle it. In-support variants exploit at a lower, budget-insensitive level, and only
quantising to 16 codes brings it down further (VQ-16 < VQ-128, 10 of 10).
So the paper's hypothesis is **right as the mechanism that amplifies the
failure**, and wrong only if read as the whole story: the in-support variants
fail too, through a smaller, bounded exploitation plus — for VQ — a loss of
accuracy. The accuracy trade-off rests on single-draw subgoal numbers and still
needs the paper-budget re-run.

### Cost ties under quantisation

See the VQ bullets above. Summary at d=50 budget: continuous and fixed-stride
give 1500 distinct costs out of 1500 candidates; VQ-128 gives 572; VQ-16 gives
69, falling to 5 distinct costs by CEM step 20.

## Things NOT yet verified — check before relying on them

- ~~How much of the +34 oracle gap is the subgoals~~ **Resolved 2026-10-01:** +22
  subgoals, +12 execution mode.
- ~~Whether failed episodes stopped short or missed narrowly~~ **Resolved
  2026-10-01:** they missed; see *Diagnosis step 4, answered in the environment*.
- Whether the VQ checkpoints run end-to-end. The `*_weights.ckpt` files load
  (verified 2026-09-19); the `*_object.ckpt` pickle path and an actual rollout
  still need `stable_worldmodel` installed. **No VQ variant has produced a success
  rate**, so the VQ comparison exists only in latent space.
- Whether **d=75** or **any second seed** behave as the paper says. Both are
  unmeasured. (Staged Hi-LeWM-C was measured on 2026-10-01: 46.0 % against the
  paper's 64.0, one seed, unpaired.)
- Whether the flat LeWM baseline can be restored at all; ~52.7 % is the paper's
  implied number, and one of our claims rests on it.

**Resolved since this list was written.** `stable_worldmodel`, dataset staging and
baseline fetching all work on Colab (2026-09-26). Two of the paper's PushT cells
reproduce within noise — plain CEM 36.0 against 38.7 (2026-09-26) and the oracle 70.0
against 73.3 at the paper's 100-step budget (2026-10-01). Hi-LeWM-C does not.

