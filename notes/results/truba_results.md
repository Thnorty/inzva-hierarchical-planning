# Eval results

Generated 2026-09-13 01:00 UTC by `scripts/collect_results.py`.
Do not edit by hand; rerun the script instead.

Source: `$STABLEWM_HOME/checkpoints/quentinll/truba_results.txt`

## Environment

| | |
|---|---|
| commit (at collection) | `8a3fe3a` |
| torch | `2.11.0+cu126` |
| cuda | `12.6` |
| gpu | `Tesla V100-SXM2-16GB` |
| transformers | `5.16.1` |

## Runs

| Policy | Seed | Episodes | Samples | CEM steps | Success | Seconds |
|--------|------|----------|---------|-----------|---------|---------|
| `quentinll/lewm-pusht` | 0 | 50 | 300 | 30 | 42/50 = 84% | 69 |
| `quentinll/lewm-pusht` | 1 | 50 | 300 | 30 | 47/50 = 94% | 64 |
| `quentinll/lewm-pusht` | 2 | 50 | 300 | 30 | 41/50 = 82% | 68 |
| `quentinll/lewm-pusht` | 0 | 50 | 300 | 30 | 42/50 = 84% | 69 |
| `quentinll/lewm-pusht` | 1 | 50 | 300 | 30 | 48/50 = 96% | 66 |
| `quentinll/lewm-pusht` | 2 | 50 | 300 | 30 | 42/50 = 84% | 69 |

## Full-protocol summary

6 runs at 50 episodes, 300 samples, 30 CEM steps.

| | |
|---|---|
| Mean | 87.3% |
| Std | 6.0 |
| Range | 82% to 96% |
| Pooled | 262/300 = 87.3% |

## Commands

The shared config, three seeds:

```bash
python scripts/plan/eval_wm.py --config-name inzva_pusht -m \
    policy=quentinll/lewm-pusht seed=0,1,2
```

A single run at the upstream config (needs the `+`, see README §7):

```bash
python scripts/plan/eval_wm.py \
    policy=quentinll/lewm-pusht +plan_config.history_len=3
```
