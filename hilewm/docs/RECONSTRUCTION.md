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
| `results/audit_dimensionality/20260921-194945_draws_d32_d8_d50.json` | PENDING | |
| `results/audit_dimensionality/20260921-175756_draws_vq16_vq128_d50.json` | PENDING | |
| `results/audit_dimensionality/20260922-001913_draws_hilewm_c_d32_d50.json` | PENDING | |
| `results/audit_dimensionality/*_draws_hilewm_c_lam{0.05,0.3,1}_d50.json` | PENDING | |
| `results/audit_dimensionality/20260922-114829_spectrum_estimators_d32_d8_fs32_d50.json` | PENDING | |
| `results/audit_dimensionality/20260922-114851_draws_fs32_d50.json` | PENDING | |
| `results/backfill/2026-09-19_session/audit__draw_intervals_exploitation_and_support.txt` | PENDING | the 20-iteration draws, which predated recording and survived only as 1-decimal text. Regenerated as a full JSON record, so `compare_draws.py` now reads exact values |
| `results/compare_draws/` | PENDING | |
| `results/inspect_empirical_residual/20260922-002009_d50_sequence.json` | PENDING | |
| `results/measure_subgoal/` (horizon-2 check, seeds 2000-2003) | PENDING | |
| `results/measure_subgoal/` + `results/subgoal_sweep/20260923-194639_index.jsonl` (axis-2 sweep) | PENDING | |
| `results/compare_subgoal_sweep/` | PENDING | |
| `results/render_subgoals/`, `analysis/figures/` | PENDING | figures were gitignored and regenerated on demand by design |
| `results/backfill/2026-09-19_session/MANIFEST.md` | **lost** | listed the commands behind numbers from before recording existed. Every such number was later superseded by a recorded measurement |
| `results/backfill/2026-09-19_session/env__pusht_download.log` | covered | the download log. The same file's verification is recorded in `INZVA_README.md` §5.1 (13,136,247,974-byte archive, `zstd -t` -> 46,300,921,856 bytes), and the file here matches it to the byte |

### Not missing, just not shipped

| cited | where it is |
| --- | --- |
| the model weights | `checkpoints.zip` in the received folder; unzip into `checkpoints/` (gitignored, 2.1 GB) |
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
