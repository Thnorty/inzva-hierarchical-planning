# Reconstruction ledger

**Written 2026-10-05.** The project arrived as a folder (`inzva-final`) after the
working tree it came from had been deleted. Its documents cite 50-odd files that
were not in the folder. This is the account of each one: what was rebuilt, how
it was checked, and what is gone for good.

**Read this before quoting a number from docs/FINDINGS.md.** Most of FINDINGS
traces to records that exist again, and most of those reproduce exactly. A few
numbers do not, and a few now rest on text alone. They are listed here.

## The rule that was followed

Nothing was written to look like a lost original. Every regenerated record is a
new run with a 2026-10-05 timestamp and this repository's commit in it, made by
the project's own scripts on the project's own data. Four scripts had to be
rewritten; each says so in its first paragraph and was checked against the
numbers FINDINGS quotes from the original. Where neither was possible, the item
is marked **lost** and is not replaced by anything.

## Why the CPU re-runs can be trusted to match

Every local measurement is deterministic given its seed, and the dataset here is
the same file the teammate used: 18685 episodes, 2,336,736 rows, 46,300,921,856
bytes, the same `zstd -t`-verified download recorded in `INZVA_README.md` §5.1.
The first re-run, draw 0 of the d32 audit, reproduced the maximums of FINDINGS'
ten-draw ranges exactly (exploitation x24.7, support x1034, 81 %), on a different
CPU, OS and `torch` version from the original Intel Mac.

## Ledger

Status: **exact** = regenerated and identical to every number FINDINGS quotes;
**differs** = regenerated, with the difference explained below; **rewritten** =
a new document from surviving material; **lost** = cannot be recovered.

### Scripts

| missing | status | notes |
| --- | --- | --- |
| `analysis/compare_eval_runs.py` | rewritten, exact | McNemar, Wald and Fisher results match FINDINGS to the digit on every pairing whose manifests survived |
| `analysis/summarize_eval_runs.py` | rewritten, exact | 36.0 %: SE 6.8, Wilson 24.1-49.9, Clopper-Pearson 22.9-50.8 |
| `analysis/audit_macro_bank.py` | rewritten, exact | all six rows of FINDINGS' table, including max diff 2.9e-6 |
| `analysis/resolve_run_provenance.py` | **lost** | it mapped a content fingerprint (`sha:bb14f7e89a2b`) to a commit. The fingerprint scheme lived only in the lost notebook and the history it searched is gone. The two fingerprints in `results/runs.csv` cannot be resolved |
| `analysis/rebuild_runs_csv.py` | new | regenerates `results/runs.csv` from records; did not exist before |

### Documents

| missing | status | notes |
| --- | --- | --- |
| `docs/FINDINGS.md` | not missing | it was at the folder root; moved to `docs/`, where both documents cite it |
| `docs/STATUS.md` | not missing | cited once by that path; the file is `STATUS.md` at the project root |
| `docs/COLAB_PLAN.md` | rewritten | from `build_colab_notebook.py`, FINDINGS *Colab feasibility* and the surviving run configs. Says so at the top |
| `results/README.md` | rewritten | layout and recording conventions, from `hilewm_local/results.py` |
| `colab_hi.ipynb` | **lost**, partly covered | the session notebook the evals ran from. Its cell 26, which FINDINGS cites four times, is cell 26 of the surviving `analysis/colab_setup.ipynb`, and it does pass the D50 row with low horizon 2. Its cell 39 (the acting suite) is gone; the commands are reconstructed in `docs/COLAB_PLAN.md` from what each acting result recorded about itself |
| the current `CLAUDE.md` | **lost**, replaced | the folder's copy is dated 2026-09-19, two days before its results were moved to FINDINGS, and it still stated the box-bound claim FINDINGS retracted that day. Its stale sections now point to FINDINGS, and a *Gotchas* section collects the traps STATUS and FINDINGS say were recorded in the lost version |
| git history | **lost** | commits FINDINGS cites (`8e23bd2`, `bf8a064`, `6f93f3c`, `56c397f`, `ff6eb38` ..) cannot be resolved. The teammate's code is preserved as received in commit `7c2be18` of this repository |

### Evaluation records (Colab, GPU)

None of these were re-run: they need the environment and a GPU, and every one
whose per-episode manifest survived is fully recoverable without that.

| missing | status | notes |
| --- | --- | --- |
| `results/runs.csv` | rebuilt | by `rebuild_runs_csv.py`, every rate read from a manifest or JSON and cross-checked. A `source` column marks the one text-only row and two timing runs |
| `results/summarize_eval_runs/20260926-213028.json` | exact | now `20261005-103325.json` |
| `results/compare_eval_runs/*` (paper budget, and plain vs Hi-LeWM-C) | exact | `d50_seed42`, `subgoal_effect_at_paper_budget`, `execution_mode_at_paper_budget`, `stages_two_vs_one`, `oracle_vs_plain_scripted_manifest`, `online_vs_staged`, plus `oracle_vs_hi_c_at_paper_budget` |
| `results/compare_eval_runs/*` (50-step oracle) | **differs** | see *The first oracle run* below |
| `results/colab/manifests/oracle_subgoal_acting_d50_seed42_episodes.tsv` | **lost** | the hand-built manifest of the first 50-step oracle run, 30/50 |
| `results/analyse_acting_npz/20261001-1310*.json` | exact | six records, now `20261005-1029*`-`1030*`. Every median and threshold split in FINDINGS' step-4 table matches |
| `results/audit_macro_bank/20260926-232444_distrust_check.json` | exact | now `20261005-103331_distrust_check.json` |
| per-episode manifest of staged Hi-LeWM-C (46.0 %) | **lost** | never copied off Colab. The rate and full config survive (`runs_rows.csv`, `code/outputs/2026-10-01/10-58-05/`), so it can be quoted but not paired |

### Local CPU records

| missing | status | notes |
| --- | --- | --- |
| `results/audit_dimensionality/20260921-194945_draws_d32_d8_d50.json` | exact | `20261005-102140_draws_d32_d8_d50.json`: x9.51 / x793 / 81 %, x3.86 / x1.47 / 75 % |
| `results/audit_dimensionality/20260921-175756_draws_vq16_vq128_d50.json` | **differs** | `20261005-102140_draws_vq16_vq128_d50.json`. See *VQ and cost ties* below |
| `results/audit_dimensionality/20260922-001913_draws_hilewm_c_d32_d50.json` | exact | `20261005-102140_draws_hilewm_c_d32_lam0.1_d50.json` (the script now tags lambda_res): x0.83, 22.1 vs 76.4, 10/10 |
| `results/audit_dimensionality/*_draws_hilewm_c_lam{0.05,0.3,1}_d50.json` | exact | every cell of FINDINGS' lambda_res table |
| `results/audit_dimensionality/20260922-114829_spectrum_estimators_d32_d8_fs32_d50.json` | exact | `20261005-155612_*`: d32 7 / 25 by spectral gap, 8 / 24 by threshold |
| `results/audit_dimensionality/20260922-114851_draws_fs32_d50.json` | exact | `20261005-124219_draws_fs32_d50.json`: support x829; fs32 vs d8 10/10 |
| `results/backfill/2026-09-19_session/audit__draw_intervals_exploitation_and_support.txt` | exact, and better | `20261005-162047_draws_d32_d8_d50.json` (n_steps 20): d32 x5.35, support x694. The budget test reproduces (9/10, p = 0.02; d8 6/2/2, p = 0.29) | the 20-iteration draws, which predated recording and survived only as 1-decimal text. Regenerated as a full JSON record, so `compare_draws.py` now reads exact values |
| `results/compare_draws/` | exact except VQ-128 | `20261005-225122_d50_paired.json`. `compare_draws.py` now finds records by content and reads the 20-iteration draws at full precision |
| `results/inspect_empirical_residual/20260922-002009_d50_sequence.json` | exact | `20261005-123651_d50_sequence.json`: 160 of 240,000 pure-bank candidates, never elite |
| `results/measure_subgoal/` (horizon-2 check, seeds 2000-2003) | **not regenerated**, by decision | four 64-segment runs, ~4 h of CPU, for a candidate explanation FINDINGS had already closed (Spearman +0.595, 4 of 4 draws). Skipped on 2026-10-05; the numbers in *The horizon-2 cost/subgoal mismatch is not real* rest on that text alone. Regenerate with `measure_subgoal.py --num-eval 64 --skip-reachability --seed 200k` before presenting them |
| `results/measure_subgoal/` + `results/subgoal_sweep/20260923-194639_index.jsonl` (axis-2 sweep) | exact for d32 and Hi-LeWM-C; **differs** slightly for d8 and VQ | 30 cells, 0 failures, finished 2026-10-06 02:30. Index `20261005-174557_index.jsonl`; the two earlier indexes log the runs the memory guard interrupted, kept as the record of what happened. See *The axis-2 sweep* below |
| `results/compare_subgoal_sweep/` | regenerated | `20261006-083906_d50_paired_5variants.json`. All 30 cells reproduce the regenerated audit to one decimal. Its pairing check prints FAIL on a 1e-6 difference; see below |
| `results/render_subgoals/`, `analysis/figures/` | exact, and extended | all four panels at 16 rows, Phase A and B (FINDINGS had d8 and VQ-128 at 6). The d32 and VQ-16 cross-checks reproduce FINDINGS to the digit (10.02 / 51.80 / 38.31; 73.69 / 76.85). The PNGs stay gitignored by design |
| `results/backfill/2026-09-19_session/MANIFEST.md` | **lost** | listed the commands behind numbers from before recording existed. Every such number was later superseded by a recorded measurement |
| `results/backfill/2026-09-19_session/env__pusht_download.log` | covered | the download log. The same file's verification is recorded in `INZVA_README.md` §5.1 (13,136,247,974-byte archive, `zstd -t` -> 46,300,921,856 bytes), and the file here matches it to the byte |

### Not missing, just not shipped

| cited | where it is |
| --- | --- |
| the model weights | extracted into `checkpoints/` (gitignored) and verified member by member against the received zip's sizes and CRC32s; the zip itself was removed with the received folder on 2026-10-06. Elsewhere, from the authors' Zenodo artifact (doi:10.5281/zenodo.21353240) |
| `checkpoints/cube/main/cube_hi_lewm_epoch15_object.ckpt` | not in the zip at all. Public in the authors' Zenodo artifact (doi:10.5281/zenodo.21353240); this project is PushT-only and never loaded it |
| `checkpoints/runs/...` | a staging directory `setup_checkpoints.sh` creates under `STABLEWM_HOME` on Colab, not a file |
| `code/data/stablewm/pusht_expert_train.h5` | the dataset; on this machine `../.stable-wm/datasets/pusht_expert_train.h5` |
| `code/third_party/lewm` | fetched, not redistributed. The teammate's copy was upstream commit `8edfeb336732b5f3ce7b8b210d0ba370a09e2cac`, which fills the `<PINNED_COMMIT>` blank in `code/THIRD_PARTY_LEWM.md` |
| `analysis/.cache/` | extracted automatically on first use (now pinned to `stable-worldmodel` 0.1.1) |

## The first oracle run

The 50-step oracle run was measured twice: 30/50 on 2026-09-27, then 29/50 on
2026-10-01 under strict determinism, which is FINDINGS' measured ±1-episode noise
floor. The first run's manifest was hand-built and is lost; the rerun's was
scripted and survives. Five comparisons FINDINGS reports from the first run were
regenerated from the rerun under `*_rerun_manifest` tags:

| comparison | FINDINGS (first run, 30/50) | regenerated (rerun, 29/50) |
| --- | --- | --- |
| plain CEM -> oracle, paired | +24.0, 18:6, p = 0.023 | +22.0, 18:7, p = 0.043 |
| Hi-LeWM-C -> oracle, paired | +26.0, 19:6, p = 0.015 | +24.0, 19:7, p = 0.029 |
| plain CEM -> oracle, unpaired | Fisher p = 0.027 | Fisher p = 0.045 |
| generated staged -> oracle | +16.0, 16:8, p = 0.152 | +14.0, 16:9, p = 0.230 |
| oracle low horizon 5 -> 2 | +34.0, 20:3, p = 0.0005 | +32.0, 20:4, p = 0.0015 |
| oracle 50 -> 100 steps | +10.0, 5:0, p = 0.0625 | +12.0, 6:0, p = 0.031 |

The one flipped episode moves each comparison by one discordant pair. Nothing
significant becomes insignificant; the budget comparison becomes significant,
and stays exactly nested. Quote the regenerated values, since they are the ones a
reader can check.

## VQ and cost ties

The VQ audit is the one local record that does not reproduce exactly. Its
medians move slightly (VQ-128 exploitation x3.70 against x3.6, VQ-16 x2.12
against x2.2; minima x2.26 against x2.5), while every continuous variant
reproduces to the digit on the same machine, seeds and code.

The likely cause is ties. Quantisation snaps many CEM candidates onto the same
code and therefore the same cost (FINDINGS *Cost ties under quantisation*: VQ-16
collapses 1500 candidates to as few as 5 distinct costs). Which of the tied
candidates become elites depends on how this `torch` build breaks ties in its
top-k, which need not match the Intel Mac's `torch` 2.2.2. The regenerated VQ
numbers are internally consistent: audit draw 0 equals the sweep's draw 0
(x3.67, x2.54) and the VQ-16 panel's cross-check (73.69 / 76.85) matches FINDINGS.

One conclusion moves. FINDINGS reports d32 exploiting more than VQ-128 in 9 of 10
draws (p = 0.02); here it is **8 of 10 (p = 0.11)**. Every other paired
comparison keeps its verdict, including VQ-128 over VQ-16 in 10 of 10. So
"d32 exploits more than every other variant" holds against d8 and VQ-16 on both
platforms and against VQ-128 on one, and should be stated that way.

## The axis-2 sweep

Medians against FINDINGS' *Axis 2 at the paper budget* table:

| variant | result |
| --- | --- |
| d32, Hi-LeWM-C | every column identical |
| d8 | identical except first-waypoint error 61.40 (61.36) and realism MD² 112.55 (112.59) |
| VQ-128 | exploitation x3.90 (x3.55), first-waypoint error 41.06 (41.92), realism NN 6.98 (7.09), reach 0.02 (0.03) |
| VQ-16 | wins 91 % (88 %), first-waypoint error 65.32 (61.19), achieved/achievable x1.05 (x1.02) |
| per-variant references, true-waypoint reference | identical |

The VQ shifts are the tie effect described above. The d8 shifts are in the third
significant figure and their cause was not isolated; numerical differences
between thread counts are the likely one, since d8's exploitation still
reproduces the audit per draw. **Every conclusion FINDINGS draws from the sweep
holds**: VQ sits at its representation's ceiling (x0.94, x1.05), plain CEM sits
x18.64 from its own, Hi-LeWM-C keeps the continuous accuracy floor (15.16) and
closes about two thirds of the gap, and reachability splits constrained from
unconstrained search (0.02-0.03 against 0.08).

**The pairing check prints FAIL, and the pairing holds.** It requires the
expert's first-waypoint error to agree within 1e-9 between d32 and Hi-LeWM-C on
every draw. Five draws agree exactly; draw 1 differs in the seventh significant
figure (7.7155867 against 7.7155786). Its d32 cell ran in the sweep interrupted
on 2026-10-05 at 4 threads, its Hi-LeWM-C cell in the restarted sweep at 6, and a
different thread count changes the order of floating-point reductions. The
segments are the same. A future sweep should keep one thread count throughout.

## The received folder was removed

On 2026-10-06, after the reconstruction, the received `inzva-final` folder was
moved to the Recycle Bin. Before that, every file in it was checked against this
repository by content (`.runlogs/verify_inzva_final.py`, gitignored): 539
identical to the working tree or to the as-received commit `7c2be18`; all 24
weight files in `checkpoints.zip` present here with matching size and CRC32; 51
files of an unmodified clone of public upstream LeWM commit `8edfeb3`; 53
`__pycache__` and `.DS_Store` files. One file had no copy: the older
`analyse_acting_npz.py` (2026-10-01 05:12) from the duplicate `analysis/analysis/`
tree. It is kept byte for byte in `analysis/archive/`.
