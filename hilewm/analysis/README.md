# analysis/

Our code. Nothing here modifies the authors' artifact under `code/`; everything
imports from it.

## Why this exists

`stable_worldmodel` cannot be installed on this machine (Intel Mac, x86_64):

| package | required | newest macOS x86_64 wheel |
| --- | --- | --- |
| `torch` | — | **2.2.2** (no x86_64 macOS wheels from 2.3 on) |
| `lancedb` | `>=0.30.0` | 0.25.3 |
| `pylance` | `>=4.0.0` | 0.39.0 |
| `stable-pretraining` | `torch>=2.4` | conflicts with the torch ceiling |

`lancedb` is not optional: `stable_worldmodel/data/__init__.py` does an
unconditional `from .formats.lance import LanceDataset`, so `import
stable_worldmodel` fails outright.

But the model itself does not need any of that. Every Hi-LeWM component except
the pixel encoder is plain `torch` + `einops`, and the encoder is a stock
HuggingFace ViT. So `hilewm_local` rebuilds the model from the `*_weights.ckpt`
state dicts and skips the package entirely.

## What runs locally and what does not

Locally on CPU:

- macro-action encoding, support distance, Mahalanobis / kNN
- codebook statistics and VQ tie counting
- high-level rollouts (`rollout_high`) and planning cost (`get_cost_high`)
- low-level rollouts and cost (`rollout_low`, `get_cost_low`)
- pixel encoding through the ViT, with `with_encoder=True`

On Colab, because they need the environment and the CEM solvers:

- episode rollouts and success rates
- the acting diagnostics (`oracle_subgoal_acting`, `low_level_reality_gap`, ...)
- anything compared directly against the paper's tables

## Usage

```bash
export PYTHONPATH="$PWD/code:$PWD/analysis"
```

```python
from hilewm_local import build_model

model, spec = build_model("checkpoints/pusht/vq/vq16/pusht_hi_lewm_vq16_epoch50_weights.ckpt")
print(spec.describe())        # VQ-16  d_l=16  d_z=192  high_ctx=4 ...

cost = model.get_cost_high({"z_init": z0, "z_goal": zg}, candidates)
```

`build_model` infers every dimension from tensor shapes, so the continuous,
fixed-stride and VQ checkpoints all load through the same call. Only the
attention head counts come from the `config.yaml` shipped beside each
checkpoint (a state dict records `heads * dim_head`, not the split); the
resulting inner dimension is checked against the checkpoint, so a wrong value
raises rather than loading a silently wrong model.

`with_encoder=True` additionally builds the ViT and needs `transformers`.

On first use the module downloads the `stable-worldmodel` wheel from PyPI and
extracts one file (`wm/lewm/module.py`, MIT licensed) into `analysis/.cache/`.
Nothing is installed, and the cache is gitignored. Where a real
`stable_worldmodel` install exists — on Colab — that is used instead.

## Modules

| module | what it does |
| --- | --- |
| `hilewm_local/swm_compat.py` | imports `stable_worldmodel` submodules past the broken package `__init__`; gives `lewm_module()` and `cem_solver_class()` |
| `hilewm_local/loader.py` | `build_model(ckpt)` -> a working `HiJEPA` plus the inferred `HiLeWMSpec` |
| `hilewm_local/data.py` | `HDF5Columns` (the slice of the dataset API the artifact's planner code needs), `build_action_scaler`, `write_episode_subset` |
| `hilewm_local/probe.py` | `load_decoder` / `decode_latents` for the Phase A/B decoder probes |
| `hilewm_local/patches.py` | opt-in runtime fixes: the CEM env-count fix, the legacy pickle aliases without which the eval cannot load the released `*_object.ckpt`, and the missing `World.evaluate_from_dataset` |
| `measure_high_cem.py` | runs the artifact's real `CEMSolver` over `get_cost_high` and counts cost ties |
| `measure_support.py` | axis 1 of the diagnosis: is the selected macro-action inside the support of the training macro-actions? |
| `measure_subgoal.py` | axis 2: is the waypoint it produces a good control target? model exploitation, cost/subgoal mismatch, subgoal realism, reachability |
| `audit_dimensionality.py` | re-derives the dimensionality and support-distance numbers, with estimator/ridge/draw sensitivity and bootstrap CIs |
| `render_subgoals.py` | decodes the subgoals with the Phase A/B probes, with an encode-decode control column |
| `run_eval.py` | the artifact's eval with our fixes applied; same Hydra arguments |
| `sitecustomize.py` | applies the fixes to subprocesses, only when `HILEWM_PATCH_CEM=1` |
| `build_colab_notebook.py` | generates and validates `colab_setup.ipynb`, the Colab session script (install, setup, timing probe, first eval). Edit the generator, never the notebook — the hand-written first version had six code cells whose lines Jupyter would have concatenated |

`measure_high_cem.py` takes about 10 seconds per run on CPU at the paper's d=50
budget (1500 samples x 20 steps):

```bash
python analysis/measure_high_cem.py \
  --checkpoint checkpoints/pusht/vq/vq16/pusht_hi_lewm_vq16_epoch50_weights.ckpt \
  --dataset code/data/stablewm/pusht_expert_train.h5
```

## The diagnosis has two axes

Keep them apart. `measure_support.py` answers "does the search leave the data?"
and `measure_subgoal.py` answers "is what it produces usable?". They dissociate:
fixed-stride d_l=8 and both VQ variants search in-support and still do not beat
continuous d_l=32, so support alone does not explain the paper's numbers.

## Reported numbers need a runnable source

`audit_dimensionality.py` exists because the "~5 dimensions" figure was first
produced by an inline snippet that was never saved, so it could not be
re-checked. The audit found it should have been "5-7, depending on the
estimator", and that a companion figure ("27 empty directions") was wrong
outright. Anything that reaches a report or a slide should come from a script in
here, not from a throwaway heredoc.

## Two traps worth knowing

**`CEMSolver` reads the env count off the first info-dict value.**
`total_envs = len(next(iter(info_dict.values())))`. The artifact puts the string
`planner_level` first, so the high level plans for `len("high") == 4` envs and
the low level for `len("low") == 3`. No env count satisfies both, so the
hierarchical planner does not run unpatched. Use `run_eval.py`, or
`HILEWM_PATCH_CEM=1` for the shell scripts. Details in docs/FINDINGS.md.

**`stable_pretraining` may be installed and still unusable.** Importing
`spt.data` raises `AttributeError: module 'torchvision.transforms.v2' has no
attribute 'GaussianNoise'` under torchvision 0.17.2. `probe.py` falls back to the
standard ImageNet constants and `decoder_stats_source()` reports which path was
taken.

## Verified on 2026-09-19

All five PushT checkpoints load with `strict=True` (VQ uses `strict=False` for
its training-only action-chunk decoder, which is not on the planning path):

```
main (continuous)   continuous  d_l=32  high_ctx=4  low_ctx=3
fixed_stride d32    continuous  d_l=32  high_ctx=3  low_ctx=3
fixed_stride d8     continuous  d_l=8   high_ctx=3  low_ctx=3
VQ-16               VQ-16       d_l=16  high_ctx=4  low_ctx=3
VQ-128              VQ-128      d_l=16  high_ctx=4  low_ctx=3
```
