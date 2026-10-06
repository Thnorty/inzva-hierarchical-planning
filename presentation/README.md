# presentation/

The final showcase deck goes here as a self-contained HTML page, alongside the
decks that came before it.

| path | what it is |
| --- | --- |
| `previous/presentation-3.pptx` | presentation 3, as given ("Proj Presentation #3"): Push-T, VLA vs world models, the GRU predictor, CEM, MPC, temporal hierarchy |
| `../notes/inzva-report-4.html` | the spec sent before presentation 4. Frozen, never edited; its 40-step horizon and stride 8 are out of date (`INZVA_README.md` §13) |

## The rule for slides

Every number on a slide comes from a record, never from memory or a terminal
snippet. The two projects keep their records in different places and use
different goal offsets (d=25 for ours, d=50 for Hi-LeWM), so **their success
rates never share an axis**.

## Where each headline number lives

### Project 1: coarse-to-fine planning (`notes/`, `INZVA_README.md`)

Seeds 0, 1, 2; 50 episodes each; d=25, horizon 10.

| claim | number | record | context |
| --- | --- | --- | --- |
| flat CEM on our GRU | 69.3 % | `notes/results/inzva_gru_results.md` | §14 |
| Experiment C, ours at k = 1 (the control) | 70.0 %, passed | `notes/results/expC_results.md` | §14 |
| coarse model alone | 76.0 % | `notes/results/inzva_gru_coarse_results.md` | §14 |
| ours at k = 2 | 76.0 % | `notes/results/inzva_gru_hier_results.md` | §14 |
| horizon 40 vs 10, before the replanning change | 15.3 % vs 64.0 % | `notes/results/gru_horizon40_results.md`; the 64.0 % is `inzva_gru_results.md` at commit `04d5008`, since overwritten by the 69.3 % run | §13 |
| DINO-WM reference | 84.0 % | `notes/results/dinowm_romer_results.md` | §11 |
| LeWM baseline of record | 87.3 % ± 7.6 (never the published 96 %) | `notes/results/inzva_pusht_results.md` | §6.1b |

The story so far, in the progress page's words: the method runs, and the
refinement has yet to earn its keep. One budget only; Experiment A's budget
sweep is where the claim lives.

### Project 2: the Hi-LeWM diagnosis (`hilewm/`)

Seed 42, 50 episodes, d=50, the paper's Table 5 budget. Read
`hilewm/docs/RECONSTRUCTION.md` before quoting anything, and the slide-ready
inventory in `hilewm/docs/STATUS.md` (*Presentation material*).

| claim | number | record |
| --- | --- | --- |
| success rates, with intervals | plain CEM 36.0, Hi-LeWM-C 34.0, staged Hi-LeWM-C 46.0, oracle 70.0 | `hilewm/results/runs.csv`, `hilewm/results/summarize_eval_runs/` |
| oracle vs plain CEM | +34, p = 0.0015 | `hilewm/results/compare_eval_runs/*_oracle_vs_plain_scripted_manifest.json` |
| ...of which matched subgoal effect | +22, p = 0.035 | `*_subgoal_effect_at_paper_budget.json` |
| ...and execution mode | +12, p = 0.21 | `*_execution_mode_at_paper_budget.json` |
| oracle subgoals at low horizon 2 vs the shipped 5 | +32 for 2, p = 0.0015 | `*_lh5_vs_lh2_rerun_manifest.json` |
| Hi-LeWM-C vs plain CEM, same checkpoint and segments | exploitation x0.83 vs x9.5, first-waypoint error 22.1 vs 76.4, 10 of 10 draws, p = 0.002 | `hilewm/results/audit_dimensionality/*_draws_hilewm_c_d32_lam0.1_d50.json`, `hilewm/results/compare_draws/`; FINDINGS *Hi-LeWM-C vs plain CEM* |
| decoded subgoals | 16-row panels, Phase A and B | `hilewm/analysis/figures/*.png` |

The +34 is never shown as a subgoal effect on its own: it is +22 subgoals and
+12 execution mode (`hilewm/docs/FINDINGS.md`). Likewise, d32 exploiting more
than d8 in 10 of 10 draws is confounded (FINDINGS changelog, 2026-09-22) and
not evidence that leaving the support causes exploitation.
