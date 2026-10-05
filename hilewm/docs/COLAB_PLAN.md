# Colab plan

**Rewritten 2026-10-05; the original is lost** (see `docs/RECONSTRUCTION.md`).
Assembled from what survived: `analysis/build_colab_notebook.py` and the
notebook it generates, FINDINGS *Colab feasibility* and the nine mismatch
entries, the Hydra overrides of every eval in `code/outputs/`, and the settings
each acting result recorded about itself. Nothing here is a recollection of the
old file.

## What has to run on Colab, and what does not

`stable_worldmodel` 0.1.1 installs on Linux x86_64, and the episode rollouts need
it plus a GPU. Everything else runs locally on CPU through `analysis/hilewm_local`
(see `analysis/README.md`).

| on Colab (GPU) | local (CPU) |
| --- | --- |
| success rates: `analysis/run_eval.py` | every `audit_*`, `measure_*`, `compare_*` script |
| acting diagnostics: `analysis/run_diagnostics.py` | `analyse_acting_npz.py` on the saved `.npz` |
| | decoded figures: `render_subgoals.py` |

## Session setup

Use `analysis/colab_setup.ipynb`, and edit `analysis/build_colab_notebook.py`
rather than the notebook. It handles each of the nine artifact/library
mismatches in the cell where it bites, checks the guards before the 45-minute
dataset download, and takes about 10 minutes end to end. Environment of record:
Python 3.13, `torch` 2.11.0+cu128, `stable-worldmodel` 0.1.1,
`stable-pretraining` 0.1.8, `numpy` 2.1.3, `transformers<5.9`.

## The eval command

Cell 26, `eval_cmd()`, builds every eval command. Two things in it are not
optional:

- **The D50 matrix row**: high horizon 2, low horizon 2, receding 1/1, replan
  interval 5, action blocks 1/5. The shipped `config/eval/hi_pusht.yaml` says
  low horizon **5**, which costs 34 points with oracle subgoals; an eval launched
  without these overrides lands on it silently.
- **The paper's Table 5 budget** from `hilewm_local/budgets.py`: at d=50, high
  1500/40/10, low 900/30/150, goal budget 100.

The exact overrides of every eval that ran are in
`code/outputs/<date>/<time>/.hydra/overrides.yaml`:

| run | log | variant |
| --- | --- | --- |
| plain CEM, 36.0 % | `2026-09-26/17-37-07` | `planning.mode=hierarchical` |
| Hi-LeWM-C, 34.0 % | `2026-09-26/19-26-10` | `+ planning.high.empirical_macro.enabled=true` |
| staged Hi-LeWM-C, 46.0 % | `2026-10-01/10-58-05` | `planning.mode=hierarchical_staged`, empirical macro on |
| timing probes | the `eval_budget=10` runs | 4 and 50 envs; rates meaningless |

## The acting suite

The lost session notebook ran these from a loop over a `SUITE` table (its cell
39). Reconstructed from the fields each `results/colab/acting/*.json` records
(`experiment_kind`, horizons, receding horizon, seed, episode count, device)
and the file-name suffixes:

```bash
P=runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15
COMMON="--policy $P --device cuda --num-eval 50 --seed 42 --goal-offset-steps 50 --low-receding-horizon 1"

# name                                              kind                      hh  lh  extra
python analysis/run_diagnostics.py $COMMON --experiment-kind oracle_subgoal_acting    --high-horizon 2 --low-horizon 2 --save-npz ... --save-json ...
python analysis/run_diagnostics.py $COMMON --experiment-kind oracle_subgoal_acting    --high-horizon 2 --low-horizon 2 --max-steps 100 --save-npz ... --save-json ...
python analysis/run_diagnostics.py $COMMON --experiment-kind oracle_subgoal_acting    --high-horizon 2 --low-horizon 5 --save-npz ... --save-json ...
python analysis/run_diagnostics.py $COMMON --experiment-kind generated_subgoal_acting --high-horizon 2 --low-horizon 2 --save-npz ... --save-json ...
python analysis/run_diagnostics.py $COMMON --experiment-kind generated_subgoal_acting --high-horizon 2 --low-horizon 2 --max-steps 100 --save-npz ... --save-json ...
python analysis/run_diagnostics.py $COMMON --experiment-kind generated_subgoal_acting --high-horizon 1 --low-horizon 2 --save-npz ... --save-json ...
python analysis/run_diagnostics.py $COMMON --experiment-kind low_level_reality_gap    --high-horizon 2 --low-horizon 2 --save-npz ... --save-json ...
```

The CEM budget is the diagnostic's own defaults: high 1500/40/10, low
900/**20**/150. Its low-level iteration count is 20 where the eval's is 30.
`--max-steps` is ours (`run_diagnostics.py`); without it the oracle and
generated paths run exactly `goal_offset_steps` steps, which is half the
paper's goal budget. A run with it is not the authors' configuration. About 4
minutes each on an A100, because the oracle path skips the high level.

Always pass `--save-npz`: `analyse_acting_npz.py` needs it, and its
`--write-manifest` is what makes an acting run pairable.

## Before the session ends

Copy the per-episode manifests (`<output>/None/*_episodes.tsv`) to Drive after
**every** run. A run without its manifest can be quoted but never paired, and
pairing is what makes a 10-point difference visible at 50 episodes. Two runs
have already been lost this way: the first 50-step oracle run, and staged
Hi-LeWM-C. The notebook's appendix reports how many manifests are still only on
local disk.

## Runtime

One high and one low solve per 5 environment steps at the d=50 budget: at 4 envs
A100 3.9 s / 2.5 s, L4 15.9 s / 7.4 s. At 50 envs on the A100, 47.3 s / 31.7 s,
roughly linear in the env count. A 100-step, 50-episode eval takes ~37 min and
an acting diagnostic ~4 min. Peak GPU memory stayed under 1 GB of 40.

## What is next on Colab

From `STATUS.md`: online Hi-LeWM-C at d=75; seeds 43 and 44 for the d=50 pair;
the VQ variants in control (never run); the flat LeWM baseline; noise on oracle
subgoals. Keep `SEED` and `NUM_EVAL` fixed within a comparison, and copy the
manifests.
