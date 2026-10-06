# Project status

**Last updated:** 2026-10-05 · **Read this first every session, update it last.**

> **2026-10-05: the working tree behind this project was deleted, and what survived
> now lives in `hilewm/` of the inzva `stable-worldmodel` repository.** The records
> this file cites have been regenerated there by the project's own scripts, and they
> reproduce to the digit except where `docs/RECONSTRUCTION.md` says otherwise. Two
> things changed as a result: the five comparisons that used the lost first oracle
> run now quote its rerun (one episode apart), and a finished run that was never
> written up -- **staged Hi-LeWM-C, 46.0 %** -- is now in the table below.

## Where we are

**We have success rates of our own, and they say the high level costs something — but
less than the number this file carried until 2026-10-01.** Everything below is PushT,
d=50, seed 42, 50 episodes, the paper's Table 5 CEM budget, and a 100-step goal budget
unless noted. Every pair is on the *same* 50 episodes, so differences are paired
(`analysis/compare_eval_runs.py`) -- except staged Hi-LeWM-C, whose per-episode
manifest was never copied off Colab.

| configuration | ours | paper | reproduces? | execution |
| --- | --- | --- | --- | --- |
| Hi-LeWM online, plain CEM | **36.0 %** | 38.7 % | yes | online, replan every 5 |
| Hi-LeWM-C online, empirical macro | **34.0 %** | 48.7 % | **no** | online, replan every 5 |
| oracle subgoals (expert waypoints) | **70.0 %** | 73.3 % | yes | **staged** |
| Hi-LeWM-C staged, empirical macro | **46.0 %** | 64.0 % | **no** -- 64.0 is above our 95 % interval (33.0-59.6) | **staged**; unpaired |
| flat LeWM | not measured | ~52.7 % (implied) | — | — |

Every row above is at low horizon 2, high horizon 2, the paper's Table 5 CEM budget:
`colab_hi.ipynb` cell 26 passes the authors' `D50` matrix row explicitly on every eval
command, and the diagnostics default to the same. The CEM budgets and horizons are matched
across all five runs. (`colab_hi.ipynb` is lost; its cell 26 survives as cell 26 of
`analysis/colab_setup.ipynb`, and every eval's overrides are in `code/outputs/`.)

**The paper's biggest claim does not reproduce either.** Staged Hi-LeWM-C, its 64.0
against plain CEM's 38.7, reaches 46.0 % here: about +10 over our online plain CEM
(Fisher p = 0.42, unpaired), not +25. It cannot be paired, and its solver banner was not
saved, so it is weaker evidence than the online pair -- but it is the canonical row with
the config's own bank, recorded exactly (FINDINGS *Staged Hi-LeWM-C: 46.0 %, not 64.0*).

**The oracle row executes staged** — commit to a subgoal sequence, switch at a fixed step
— while the two planner rows replan online every 5 steps. So the +34.0 between them was
never a pure subgoal effect. Adding the missing cell settled it: the model's own subgoals
under the oracle's own machinery reach **48.0 %**, and the gap decomposes exactly.

| comparison | what varies | difference | discordant | McNemar p |
| --- | --- | --- | --- | --- |
| generated staged -> **oracle staged** | **the subgoals, nothing else** | **+22.0** | 17 : 6 | **0.035** |
| plain online -> generated staged | execution mode | +12.0 | 11 : 5 | 0.21 |
| plain online -> oracle staged | both | +34.0 | 22 : 5 | 0.0015 |

**+22 and +12 sum to +34.** The subgoal term is the larger one and the only one
significant at a single seed, so this project's central claim is now attributed as well as
measured: **the model's subgoals cost 22 episodes in a hundred against the expert's own**,
with controller, budget, horizons and execution mode all held fixed. Its 50-step version
was +16.0 at p = 0.152.

The other paired result is clean: Hi-LeWM-C over plain CEM is **-2.0**, p = 1.00 — both
online, both at the same budget and horizons, so like for like. **The paper's +10 does not
appear**, although by every latent measure we have its subgoals are better: 3.5x closer to
the expert's waypoint, in support, non-exploiting, easier to reach. That remains the result
we did not expect.

**Three things qualify everything here.**

1. **The low-level horizon dominates every high-level effect we can measure.** With oracle
   subgoals held fixed, raising it from 2 to 5 costs **32 points** (58.0 % -> 26.0 % at the
   50-step budget, paired, p = 0.0015; 34 points and p = 0.0005 against the first run,
   whose manifest is lost) — the largest single effect anywhere in this
   project and **the only comparison isolating one variable that is significant at one
   seed**. It is visible from the authors' own sweep rows and absent from the paper's
   tables. All our runs use 2, which is the authors' matrix-row value; the **shipped eval
   config says 5**, so an eval launched without the matrix-row overrides lands silently on
   the worse setting.
2. **±2 points is irreducible noise.** The same configuration run twice under strict
   determinism gave 30/50 then 29/50, so no small difference here means anything.
3. **The artifact cannot reproduce Hi-LeWM-C at all.** No shipped spec enables
   `empirical_macro`, so our 34.0 % is that method at the artifact's defaults — a
   defensible guess at the paper's configuration, not a reproduction of it. Eleven
   mismatches between the released artifact and the released `stable_worldmodel` 0.1.1 are
   recorded in FINDINGS, five of them needing runtime patches.

**The subgoals are wrong, not unreachable — and the two levels fail in opposite
directions.** From the saved `.npz`, per episode: a failed episode has covered **three
quarters** of the latent distance to the goal under the expert's subgoals (progress 0.76)
and **one eighth** under the model's own (0.12). Oracle failures are near misses; the
model's never went anywhere. Break the **high** level and the final state sits **0.811**
from the nearest point on the expert's whole trajectory; break the **low** level (horizon
5) and it sits **0.138** — on the path but short. Neither number needs a threshold. This is
diagnosis step 4, answered in the environment.

**Other mechanisms, measured.** The predicted waypoints **undershoot** their horizon by
20-25 % (the first subgoal, asked for 5 tokens ahead, lands nearest the true future at
4.01), and the selected macro-actions sit at Mahalanobis ~5x10^5 from the training
distribution while their norms look ordinary. **Two stages beat one**, 44.0 % against
34.0 %, +10.0 paired at p = 0.27.

The latent-space diagnosis that preceded all of this still stands and is summarised below;
what changed is that it no longer stands alone.

## Done

| | where the evidence is |
| --- | --- |
| Local toolkit: model rebuilt from `*_weights.ckpt`, runs on CPU without `stable_worldmodel` | `analysis/hilewm_local/`, `analysis/README.md` |
| PushT dataset downloaded and verified (13.1 GB -> 46.3 GB, `zstd -t` OK) | the log is lost; the same file is verified in `../INZVA_README.md` §5.1 (13,136,247,974-byte archive, `zstd -t` -> 46,300,921,856 bytes) and matches it to the byte |
| Found and patched: published `CEMSolver` cannot run the hierarchical planner at any env count | `docs/FINDINGS.md`, `analysis/hilewm_local/patches.py` |
| Found: the quantile search box is computed but never enforced | `docs/FINDINGS.md` (retraction) |
| Found: VQ checkpoints are d_l=16, a second confound beyond the epoch count | `docs/FINDINGS.md` |
| **Diagnosis step 1** — decoded subgoals, 4 variants, with an encode-decode control | `analysis/render_subgoals.py`; PNGs regenerate into `analysis/figures/` |
| **Diagnosis step 2** — support distance, macro-actions and subgoal latents | `analysis/measure_support.py`, `measure_subgoal.py` |
| Mechanism for step 2: both encoders use 5-7 dims; d_l=32 pads with 25 near-empty ones | `analysis/audit_dimensionality.py` |
| **Diagnosis step 3** (static form) — exploitation ratio vs the expert's cost | `analysis/measure_subgoal.py` |
| **Diagnosis step 4** (model-side) — reachability under `rollout_low` | `analysis/measure_subgoal.py` |
| VQ cost ties under the real CEM (VQ-16 collapses to 5 distinct costs of 1500) | `analysis/measure_high_cem.py` |
| Audit of the headline numbers; three corrected | `docs/FINDINGS.md` changelog |
| 10-draw intervals for exploitation and d_l=8 support; x16 -> x5.4, x5.9 -> x4.3, x1.3 -> x1.6; monotonic claim withdrawn | `results/backfill/2026-09-19_session/audit__draw_intervals_exploitation_and_support.txt` |
| CEM budgets tied to Table 5 (`hilewm_local/budgets.py`) after finding every CEM run used half the d=50 iterations | commit `8e23bd2` |
| **Headline ratios at the paper budget**, all four variants, 10 paired draws, with paired sign tests and the 20 -> 40 budget effect | `results/audit_dimensionality/`, `analysis/compare_draws.py`, FINDINGS *Headline ratios at the paper budget* |
| **Hi-LeWM-C vs plain CEM**, same checkpoint and segments, 10 paired draws: stays in support, does not exploit (x0.83, 50% wins), subgoal 3.5x better but x5.7 the expert's; every metric 10 of 10, p=0.002 | FINDINGS *Hi-LeWM-C vs plain CEM*; `results/audit_dimensionality/20260922-001913_draws_hilewm_c_d32_d50.json` |
| Hi-LeWM-C has one pure-bank candidate per iteration, never elite; search converges to anchors + learned offset | `analysis/inspect_empirical_residual.py` |
| lambda_res sweep: no exploitation only at lambda_res <= 0.1; always far below plain CEM; subgoals flat across lambda_res and better than plain CEM throughout | FINDINGS *lambda_res sweep* |
| Decoded panels at the paper budget, d32 with a Hi-LeWM-C column; d32 panel verified against the audit to the digit; 6 shown rows found unrepresentative | FINDINGS *Re-rendered at the paper budget*; `analysis/figures/*_d50_draw0*.png` |
| Provenance fix: records now stamp the commit at run start, and also record the commit at end | `analysis/hilewm_local/results.py` |
| **fixed_stride_dim32**, 10 paired draws + spectrum: support distance is a d_l effect (fs32 vs d8 10/10); waypoint strategy changes nothing measurable; the d32-vs-d8 exploitation gap is not attributable to either (p=0.11 both ways) | FINDINGS *fixed_stride_dim32* |
| Geometry table corrected (d32 "8 / 25" mixed two definitions; now 7 / 25 by spectral gap, 8 / 24 by threshold); spectra for d32, d8, fs32 now have a results record | FINDINGS; `results/audit_dimensionality/20260922-114829_*` |
| 16-row panels for d32 + Hi-LeWM-C and VQ-16; audit cross-check exact again (d8 and VQ-128 at 16 rows too since 2026-10-05) | `analysis/figures/*_d50_draw0*.png`, tracked |
| **Axis 2 at the paper budget**: 5 variants x 6 paired draws, 30 cells, 11h20m, 0 failures; two gates passed (expert reference identical for the paired solvers; all 30 cells reproduce the audit's exploitation to one decimal) | FINDINGS *Axis 2 at the paper budget*; `analysis/run_subgoal_sweep.py`, `analysis/compare_subgoal_sweep.py` |
| Hi-LeWM-C branch in `measure_subgoal` (`--solver empirical`), verified against audit draw 0 on ten numbers | commit `bf8a064` |
| **Horizon-2 mismatch closed**: Spearman +0.595 at n=64, 4 of 4 draws significant — the objective is aligned, so that candidate explanation is out | FINDINGS *The horizon-2 cost/subgoal mismatch is not real* |
| **Colab plan and a rebuilt session notebook**; `stable_worldmodel` confirmed installable on Linux x86_64; five setup traps found by reading the code (the `[format]` extra, the `datasets/` path mismatch, the smoke spec that trains, preflight's Cube requirement, the 0.16 GB non-pixel dataset) | `docs/COLAB_PLAN.md`, `analysis/colab_setup.ipynb`, FINDINGS *Colab feasibility* |
| **Nine artifact/library mismatches fixed** so the eval can run at all — eight against `stable_worldmodel` 0.1.1, one internal (missing pickle aliases); five need runtime patches, one touches `code/` (four empty `__init__.py`) | FINDINGS *Verified by reading the code*; `analysis/run_eval.py`, `analysis/run_diagnostics.py` |
| **First success rates (Colab, 2026-09-26)**: plain CEM **36.0 %** and Hi-LeWM-C **34.0 %** at d=50, seed 42, paper budget, paired on the same 50 episodes | `results/runs.csv`; FINDINGS *Our first success rate*, *Hi-LeWM-C does not beat plain CEM in control* |
| **Acting suite (2026-09-27, 2026-10-01)**: oracle **70.0 %** at the paper's 100-step budget and 58-60 % at the artifact's 50, generated staged **44.0 %** (hh2) and **34.0 %** (hh1), oracle at low horizon 5 **26.0 %**; plus a measured **±2-point** noise floor from a strict-determinism rerun | `results/runs.csv`, `results/colab/manifests/`, `results/compare_eval_runs/`; FINDINGS *The acting suite decomposes the gap*, *it was the budget* |
| **Found: the +34 oracle headline mixes the subgoal source with staged-vs-online execution**; the matched subgoal effect is +16 (p = 0.15). Also found: the shipped eval config's low horizon (5) differs from the authors' matrix row (2), a 34-point trap that our runs escape only because the notebook overrides it | FINDINGS *Qualified: the +34 mixes the subgoals with the execution mode* |
| Git, results recording, this file | commits `ff6eb38` .. (that history is lost; the project as received is commit `7c2be18` of the inzva repo) |
| **Reconstruction (2026-10-05):** merged into the inzva repo; three lost scripts rebuilt and checked against FINDINGS; every Colab-derived record regenerated, exact except the five that used the lost first oracle run; staged Hi-LeWM-C written up | `docs/RECONSTRUCTION.md` |

## In progress

**2026-10-05: regenerating the local CPU records whose files were lost.** Done and
checked: every audit, the lambda_res sweep, the 20-iteration draws, the spectrum, the
residual inspection, all four decoded panels (now 16 rows each) and, on 2026-10-06, the
30-cell axis-2 sweep. All exact except the VQ variants, where tied costs shift a few draws
and move d32 vs VQ-128 to p = 0.11, and two third-digit d8 values in the sweep
(`docs/RECONSTRUCTION.md`). No conclusion changes. The horizon-2 check was skipped by
decision. **Nothing is running.**
Nothing is running on Colab.

The Colab pipeline works end to end and is no longer the bottleneck: six eval and diagnostic runs have finished through it, and
`analysis/colab_setup.ipynb` was rewritten (38 cells, 18 code) so that none of the nine
artifact/library mismatches has to be rediscovered — each is handled in the cell where it
bites, the guards fail before the 45-minute download rather than after it, and a restart
is served by an appendix cell instead of a rerun. Setup is ~10 minutes. Three parts of the
notebook were verified against reality rather than by reading: the probe command it builds
is byte-identical to one that exited 0, `resolve_checkpoints` was run against both a full
tree and a zip-only Drive copy, and the outcome parser was run against real stdout, which
is what caught that the artifact prints every `PASS`/`FAIL` line twice.

**Runtime, for planning.** One high and one low solve per 5 environment steps at the d=50
budget: at 4 envs **A100 3.9 s / 2.5 s** against **L4 15.9 s / 7.4 s**, so the GPU class
moves runtime about 4x. At 50 envs on the A100, 47.3 s / 31.7 s — 12x the time for 12.5x
the batch, so the planner scales about linearly in the environment count. A full 100-step,
50-episode eval is **~37 min**; the acting diagnostics are **~4 min**, because the oracle
path skips the high level entirely, which makes them the cheapest information available.
Peak GPU was 910 MiB of 40960, so memory never binds.

**Colab environment, for provenance:** Python 3.13, `torch` 2.11.0+cu128,
`stable-worldmodel` 0.1.1, `stable-pretraining` 0.1.8, `numpy` 2.1.3, `transformers`
pinned `<5.9`. Full preflight fails as expected on `[baseline-integrity] FAIL: .gitmodules
missing` — the check assumes the upstream LeWM checkout is a git submodule, which a plain
clone is not; the dataset and staged-checkpoint checks both pass.

## Next, in priority order

1. **Done 2026-10-01: the matched subgoal effect is +22.0, p = 0.035.**
   `generated_subgoal_acting --max-steps 100` reached 48.0 %, which decomposed the +34 and
   made the central claim significant at one seed. See *Where we are*.

2. **Done 2026-10-01: `analyse_acting_npz.py` ran on all six `.npz`.** Diagnosis step 4 is
   answered in the environment — the subgoals are wrong, not unreachable — and the script
   gained `--write-manifest`, which also put the acting manifests under a script for the
   first time. All four hand-built manifests verified against it; one differs at exactly
   one episode, which is the documented rerun.

3. **Done 2026-10-01, written up 2026-10-05: staged Hi-LeWM-C at d=50 reaches 46.0 %**
   against the paper's 64.0. If +25 were real it would have shown at one seed; it did not.
   Its manifest was lost, so a rerun with the manifest copied would make it pairable
   against plain CEM -- 37 minutes on an A100.

4. **Online Hi-LeWM-C at d=75** — +17 claimed (32.7 against 15.3), and the horizon where
   our diagnosis says the most.

5. **Restore the flat LeWM baseline.** Either pin an older `le-wm` commit (the one whose
   `LeWM` still used a HuggingFace ViT) or convert the Hub weights against a stock HF ViT
   in `analysis/`. The claim "perfect subgoals buy ~17 points over no hierarchy" rests
   entirely on the paper's **implied** ~52.7 %, and full preflight cannot pass without it.

6. **Seeds 43 and 44** for the d=50 pair, to put an interval on the -2.0 for Hi-LeWM-C.
   Power: with the 4:1 discordant split a +10 effect implies, McNemar gives p = 0.11 at
   one seed, 0.012 at two, 0.0014 at three. Less urgent now that ±2 points is a measured
   noise floor.

7. **VQ-16 / VQ-128 in control.** The gap table below used to say the VQ comparison was
   done; that is true only in latent space. **No VQ variant has ever produced a success
   rate here**, and whether the VQ `*_object.ckpt` pickle path and an actual rollout work
   at all is still unverified.

8. **d = 25 and d = 75 locally.** The CEM checks refuse d != 50 because the 5 + 5 token
   split is hard-wired; d = 25 and 75 split unevenly (2 + 3, 7 + 8) and need the per-stage
   reference generalised first.

9. **Diagnosis step 5, second half:** noise added to oracle subgoals, to measure low-level
   sensitivity. The oracle half is done; this half has not been started.

10. **Check the paper text on Hi-LeWM-C's zero-residual candidates** — our summary says one
    per anchor, the code has one per iteration.

11. **Done 2026-10-05:** all four decoded panels at 16 rows, Phase A and B, committed in
    `analysis/figures/` (tracked from 2026-10-06).

Keep `SEED` and `NUM_EVAL` fixed within a comparison; the same seed gives the same 50
episodes, which is what makes the runs pairable. And set
`planning.low.plan_config.horizon` explicitly in anything new, now that the two code paths
are known to disagree on it.

## Open questions

- **How were the paper's unconstrained Hi-LeWM numbers produced?** With the
  published `stable_worldmodel` the plain-CEM path cannot run; the empirical-macro
  path can. Either the authors used an unpublished version, or something differs.
  Worth asking them.
- **Is the paper's 73.3 % oracle staged and its 38.7 % online?** If so, their
  oracle-vs-hierarchy gap mixes the same two variables ours did. Not checkable from
  the artifact; worth asking alongside the question above.
- **Why does the shipped eval config run the low level at horizon 5** when the
  authors' own matrix row and diagnostics both use 2, and 2 is 34 points better
  with oracle subgoals? Either the setting interacts with generated subgoals
  differently, or the shipped config is simply not the swept best.
- **Does the macro-action encoder memorise its training spans?** The dataset we
  measure against is its training set, and no held-out split exists. The
  disjoint-episode check rules out reference overfitting, not encoder
  memorisation.
- ~~**Is the horizon-2 cost/subgoal mismatch real?**~~ **Answered 2026-09-24:
  no.** At n=64 over 4 draws, Spearman +0.595 (+0.566 to +0.652), significant in
  4 of 4. The objective is aligned; the problem is the cost it is pointed at.
- **Why does VQ-128 leave half its codebook unused (66 of 128)?**

## Known gaps against the plan

| plan item | state |
| --- | --- |
| Timeline "now -> next week": one baseline eval | **done 2026-09-26** — 36.0 % at d=50, seed 42, paper budget |
| Diagnosis steps 1, 2 | done |
| Diagnosis steps 3, 4 | step 3 done in the model-only form; **step 4 now done in the environment too** (2026-10-01) — failures reach progress 0.76 under oracle subgoals and 0.12 under the model's |
| Diagnosis step 5 | **partial** — the oracle half is done (70.0 % at the paper budget); the noise-sensitivity half has not been started |
| Hi-LeWM-C comparison | done in latent space (6 paired draws); **done in control too, and it does not win**: 34.0 % against 36.0 %, paired p = 1.00. **Staged** Hi-LeWM-C — the paper's biggest claim — reaches 46.0 % against its 64.0 (unpaired) |
| VQ comparison | **latent space only** — no VQ variant has ever produced a success rate, and the object-checkpoint path is unverified |
| >=3 seeds | **not done** — the local diagnostics are one seed family (draws 2000-2005/2009); the eval is one seed (42) |
| d=25 / d=75 | **not done** — all d=50 |
| Flat-vs-hierarchical comparison of our own | **not done** — the baseline conversion is broken, so ~52.7 % is still the paper's implied number |
| Like-for-like oracle vs planner | **done 2026-10-01** — +22.0 subgoals, +12.0 execution mode, summing to the +34.0 |
| Per-episode reachability from the saved `.npz` | **done 2026-10-01** — all six runs, with a threshold sweep; manifests now scripted |

## Presentation material — what is ready

The interim presentation is behind us; this is the inventory for the final showcase.
**Every panel below is in `analysis/figures/`, regenerated on 2026-10-05 at 16 rows and
committed.** The d32 and VQ-16 panels' audit cross-checks reproduce to the digit.

- Figure 1: `render_subgoals.py --draw 0 --with-empirical` on the main checkpoint —
  expert, plain CEM and Hi-LeWM-C subgoals side by side on the same segments; the
  encode-decode column proves the probe is not the source of blur. **Caveat to
  state:** the 6 rows shown are harder than their draw's median for plain CEM;
  prefer the all-16-rows render once it exists.
- Figure 2: the same panel for VQ-16 — expert and CEM columns look alike, so
  the limit is the representation, not the planner.
- The two-axis story, now at the paper budget: every variant exploits the
  model; leaving the support amplifies it and makes it grow with CEM budget;
  in-support search still exploits at a lower level. Backed by paired sign tests
  (d32 > d8 in 10 of 10 draws, p=0.002).
- **The exploitation-vs-accuracy trade-off can now be presented as established**
  (6 paired draws, paper budget): VQ's accuracy floor is ~8x the continuous
  variants' and its achievable subgoal ~9-12x, while its planner sits at that
  representation's ceiling (x0.94 / x1.02) and plain CEM sits x18.64 from its
  own. This is the slide that answers "do the two fixes work the same way?" —
  they do not. Still not tied to success rates: no VQ variant has been run in control.
- **The success-rate story, with its caveat stated on the slide:** plain CEM 36.0 % and
  the oracle 70.0 % both reproduce the paper (38.7 and 73.3), Hi-LeWM-C shows neither its
  online +10 nor its staged +25 (34.0 and 46.0 against 48.7 and 64.0), and the matched
  subgoal effect is **+22 at p = 0.035**. The +34 must not be shown as a subgoal effect
  without saying that it is +22 subgoals and +12 execution mode.
- A methods story worth telling on its own: **three** conclusions that looked solid
  reversed under scrutiny — two when the CEM budget matched the paper's, and the +34
  oracle gap when the two code paths were read against each other.
- Two code defects in the artifact, each verified and, for the solver bug, fixed; plus a
  silent configuration divergence between the artifact's own eval and diagnostics paths.

## Session log

### 2026-10-05 — reconstruction

The working tree was deleted; a folder survived (`inzva-final`) with the artifact, the
analysis code, STATUS, FINDINGS, the Colab outputs and the checkpoints zip, but without
git history, `docs/`, most of `results/`, four scripts, the session notebook and the
current `CLAUDE.md`. Merged it into the inzva `stable-worldmodel` repo as `hilewm/`,
pinned the toolkit's `stable-worldmodel` download to 0.1.1, and set the analysis up on a
Windows machine, where the first CPU re-run reproduced the Intel Mac's numbers to the
digit. Rebuilt `compare_eval_runs`, `summarize_eval_runs` and `audit_macro_bank` from
FINDINGS' descriptions and checked each against the numbers it quotes; regenerated every
Colab-derived record from the surviving manifests and `.npz`; rebuilt `runs.csv` from
records rather than prose. Found along the way: a finished staged Hi-LeWM-C run (46.0 %,
2026-10-01) that had been logged but never written up; that the folder's `CLAUDE.md` was
the 2026-09-19 snapshot still asserting the retracted box-bound claim; and that the
Cube checkpoint was never in the zip. `docs/RECONSTRUCTION.md` is the ledger.

### 2026-10-01 — sixth session: the budget, then the confound

Two cheap tests on the oracle's 60 %, both prompted by an objection to the previous
session's reading. The budget was the explanation: at the paper's `max_steps = 100` the
oracle reaches **70.0 %** against the paper's 73.3 %, so a second paper cell reproduces,
and the 50-step and 100-step results are **exactly nested** — five discordant pairs, all
one way, which is stronger evidence than the exact test's p = 0.0625 suggests. The rerun
at 50 steps gave 29/50 against the first run's 30/50 under strict determinism, putting the
project's noise floor at **±2 points**. Then an audit of this file against the code found
that the **+34 headline mixes the subgoal source with staged-vs-online execution** — the
oracle comes from the diagnostics, which execute staged, while the planner rows replan
online. Qualified it, kept the matched +16 (p = 0.15), and made
`generated_subgoal_acting --max-steps 100` the next run, at 4 minutes. The audit's first
attempt got the cause wrong, blaming a low-level horizon mismatch between the eval config
(5) and the diagnostics (2); `colab_hi.ipynb` cell 26 passes the authors' matrix row,
which sets 2, on every eval command, so all our runs were matched at 2 and that
qualification was withdrawn within the session. The real lesson is the one now in
CLAUDE.md: **read the recorded command, not the config file**. The same audit found that
`analyse_acting_npz.py` had only ever been run on synthetic input, that no VQ variant has
ever produced a success rate, and that `CLAUDE.md` still carried the superseded 60 %.

Then the missing cell was run and the picture closed. `generated_subgoal_acting` at the
paper's 100-step budget reached **48.0 %**, which splits the +34 into **+22.0 subgoals
(p = 0.035)** and **+12.0 execution mode (p = 0.21)** — the central claim, attributed and
significant at one seed for the first time. The six saved `.npz` then answered diagnosis
step 4 in the environment: failures reach progress 0.76 under the expert's subgoals and
0.12 under the model's, and a high-level failure ends off the expert's path (0.811) where a
low-level one ends on it but short (0.138). Three process fixes fell out along the way —
`analyse_acting_npz.py` gained `--write-manifest`, so the acting manifests have a script
behind them for the first time (all four hand-built ones verified, one differing at exactly
one episode, 14497, which is the documented rerun); the script skips
`low_level_reality_gap`, whose npz has a different schema; and a sensitivity sweep caught
that the off-path/stopped-short split is threshold-dependent, so the reading now rests on
the threshold-free quantities and the script reports the split at three cuts.

### 2026-09-26 to 2026-09-27 — fifth session: the first success rates

Took the notebook to Colab and got the project's first numbers. Nine fixes stood between
the artifact and a run — eight of them mismatches with the released `stable_worldmodel`
0.1.1, one internal to the artifact (the missing pickle aliases), and only one touching
`code/` (four empty `__init__.py` files). Then: plain CEM **36.0 %** at d=50, which
reproduces the paper's 38.7, and Hi-LeWM-C **34.0 %** on the same 50 episodes, where the
paper's +10 does not appear. The acting diagnostics turned out to cost 4 minutes rather
than 30, because the oracle path skips the high level, so the rest of the suite ran the
same night: oracle **60.0 %**, generated staged **44.0 %**, oracle at low horizon 5
**26.0 %**. That last row is the largest effect in the project and reframed the whole
reading — the low level's configuration, not the subgoals. (One recorded timestamp was
wrong: the chain noted as starting "~04:40" actually started at 11:48 on 2026-09-22.)

### 2026-09-19 to 2026-09-21 — first session

Started with nothing installed and the checkpoints still zipped. Found
`stable_worldmodel` uninstallable on the Intel Mac and built
`analysis/hilewm_local` to work around it. Downloaded and verified the PushT
dataset (the first download script lost 2.3 GB to a `curl --retry` that
restarts rather than resumes; fixed). Found the `CEMSolver` env-count bug by
tripping over it, proved it against the real policy class, and patched it
outside `code/`. Measured support distance, then found the quantile box is never
applied and retracted an earlier claim built on it. Explained why d_l=32 leaves
the support and d_l=8 does not — after a first explanation turned out wrong.
Measured exploitation, subgoal quality and reachability across four variants,
and rendered decoded subgoals. A user-requested audit then found the
dimensionality numbers came from an unsaved snippet and three figures were
wrong; corrected them, made the audit a permanent script, and put the repo under
git with every measurement recorded to disk.

### 2026-09-26 — fourth session: preparing the Colab session

The interim presentation was behind us, so the one remaining gap was the Colab
run. Went at it by reading code rather than by starting a session: confirmed
`stable_worldmodel` installs on Linux x86_64 (every Mac blocker has a manylinux
wheel), then found five traps that would each have cost a session — the declared
conda environment omits the `format` extra although `formats/hdf5.py` imports
`hdf5plugin` unconditionally and the PushT pixels are blosc-compressed; the
dataset is extracted to a path the reader does not read from, while preflight
checks the path it *is* written to; `run_pusht_smoke.sh` trains a one-epoch model
instead of evaluating the released one; preflight cannot be narrowed away from
the Cube baseline; and the 46 GB dataset is 46 GB of pixels, everything else
being 0.16 GB, which opens a 1 GB Drive-resident stand-in for later sessions.
Also found that the old `colab_setup.ipynb` was syntactically broken — six code
cells had `source` lines with no trailing newline, so Jupyter would have
concatenated them (`!nvidia-smiimport torch`). Rebuilt it from a generator and
validated the result. Wrote `docs/COLAB_PLAN.md`. Nothing was measured.

### 2026-09-23 to 2026-09-24 — third session

Colab was judged too risky three days before the interim presentation, so the
session went after the provisional numbers instead. Timed `measure_subgoal` at
the paper budget (22 min per cell, three quarters of it reachability), added a
Hi-LeWM-C branch to it and verified that branch against audit draw 0 on ten
numbers with a plain-CEM regression check beside it, then ran five variants x
six draws overnight. All 30 cells reproduce the audit's exploitation per draw,
which also retro-verified d8 and the VQ variants — something the previous
session had recorded as impossible. Two readings changed: reachability does not
follow support (d32 and the in-support d8 tie, both worse than every
constrained search), and the VQ accuracy trade-off is larger than the single
draw suggested.
