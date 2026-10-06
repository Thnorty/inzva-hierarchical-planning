# presentation/

The final showcase deck goes here as a self-contained HTML page, alongside the
decks that came before it.

| path | what it is |
| --- | --- |
| `refined.html` | **the refined deck**: the same story for a general audience, 11 slides, 8 minutes. Opens on real footage, introduces the team, explains why a VLA is not enough before world models, and keeps statistics off the slides |
| `index.html` | the detailed deck: the same results with intervals and p-values; backup for questions |
| `assets/pusht-wall.gif`, `assets/pusht-episode.gif` | real episodes of our planner, made by `make_gifs.py` from the Experiment A sweep's videos (600 samples, seed 4, successful episodes only; run it with `--videos` and `--results` pointing into `$STABLEWM_HOME/checkpoints/`) |
| `assets/team/` | **put `defne.jpg`, `oguz.jpg` and `arda.jpg` here**, square crops work best. Until then the refined deck shows initials |
| `assets/subgoal-strip.png` | slide 9's figure, made by `make_subgoal_strip.py` from hilewm's own 16-row panel |
| `previous/presentation-3.pptx` | presentation 3, as given ("Proj Presentation #3"): Push-T, VLA vs world models, the GRU predictor, CEM, MPC, temporal hierarchy |
| `../notes/inzva-report-4.html` | the spec sent before presentation 4. Frozen, never edited; its 40-step horizon and stride 8 are out of date (`INZVA_README.md` §13) |

## Presenting

Open `refined.html` (or `index.html`) in a browser, from this folder so it finds `assets/`. GIFs play and loop on their own. It needs
the internet only for its two fonts, and falls back to Georgia and Consolas
without it.

| key | does |
| --- | --- |
| → , space, Page Down | next slide (a presenter clicker sends these) |
| ← , Page Up | previous slide |
| N | speaker notes, with each slide's time budget and a running clock |
| F | full screen |

The timer starts on the first move. The slide budgets add up to 8:00:

| slide | seconds | | slide | seconds |
| --- | --- | --- | --- | --- |
| 1 title | 20 | | 7 Hi-LeWM reproduction | 50 |
| 2 the idea | 50 | | 8 splitting the gap | 60 |
| 3 two parts | 30 | | 9 why subgoals are wrong | 60 |
| 4 test bench | 40 | | 10 same lesson twice | 30 |
| 5 horizon | 50 | | 11 takeaways | 30 |
| 6 Experiment A, budget sweep | 60 | | | |

`index.html#6` opens on slide 6.

## The rule for slides

Every number on a slide comes from a record, never from memory or a terminal
snippet. The project's two parts keep their records in different places and
use different goal offsets (d=25 for our planner, d=50 for Hi-LeWM), so **their
success rates never share an axis**.

## Where each headline number lives

### Part 1: coarse-to-fine planning (`notes/`, `INZVA_README.md`)

Seeds 0, 1, 2; 50 episodes each; d=25, horizon 10.

| claim | number | record | context |
| --- | --- | --- | --- |
| Experiment A: success against budget, three planners | 25 to 600 samples, 5 seeds, 250 episodes per point | `notes/results/expA_sweep_results.md` | §14 |
| coarse beats flat at equal compute | +12.0 at 15,000 evaluations (p = 0.0003), +9.6 at 7,500 (p = 0.0007), +6.4 at 90,000 (p = 0.04) | `expA_sweep_results.md`, last three paired rows | §14 |
| refinement adds nothing | ours vs coarse alone: +2.4, 0.0, 0.0, -2.4, +0.4, none significant | `expA_sweep_results.md` | §14 |
| flat CEM on our GRU | 69.3 % | `notes/results/inzva_gru_results.md` | §14 |
| Experiment C, ours at k = 1 (the control) | 70.0 %, passed | `notes/results/expC_results.md` | §14 |
| coarse model alone | 76.0 % | `notes/results/inzva_gru_coarse_results.md` | §14 |
| ours at k = 2 | 76.0 % | `notes/results/inzva_gru_hier_results.md` | §14 |
| horizon 40 vs 10, before the replanning change | 15.3 % vs 64.0 % | `notes/results/gru_horizon40_results.md`; the 64.0 % is `inzva_gru_results.md` at commit `04d5008`, since overwritten by the 69.3 % run | §13 |
| DINO-WM reference | 84.0 % | `notes/results/dinowm_romer_results.md` | §11 |
| LeWM baseline of record | 87.3 % ± 7.6 (never the published 96 %) | `notes/results/inzva_pusht_results.md` | §6.1b |
| three machines agree | 87.3 / 86.7 / 87.3 % | `inzva_pusht_results.md` (RTX 3060), `truba_results.md` (V100, its first three rows), `a4000_results.md` | §6.4 |

The story, in the progress page's words: planning in bigger steps pays, most
when compute is scarce; the refinement does not. Slide 6 shows the sweep; the
three-seed numbers at 300 samples above are the earlier single point.

### Part 2: the Hi-LeWM diagnosis (`hilewm/`)

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
| failed episodes' progress to the goal | 0.76 with expert subgoals, 0.12 with the model's | `hilewm/results/analyse_acting_npz/`; STATUS *Where we are* |
| the search exploits the model | plans scored x9.5 better than the expert's actions; macro-actions use 5-7 of 32 dimensions | `audit_dimensionality/`; FINDINGS *Synthesis so far* |
| low-level horizon 2 vs the shipped 5 | 58.0 vs 26.0 %, expert subgoals, 50-step budget | `runs.csv` rows `oracle_staged_hh2_lh2_steps50_rerun`, `oracle_staged_hh2_lh5_steps50` |
| decoded subgoals | 16-row panels, Phase A and B; slide 9 shows all 16 of the Phase B one | `hilewm/analysis/figures/*.png` |

The +34 is never shown as a subgoal effect on its own: it is +22 subgoals and
+12 execution mode (`hilewm/docs/FINDINGS.md`). Likewise, d32 exploiting more
than d8 in 10 of 10 draws is confounded (FINDINGS changelog, 2026-09-22) and
not evidence that leaving the support causes exploitation.
