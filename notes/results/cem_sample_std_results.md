# Eval results

Generated 2026-09-11 11:44 UTC by `scripts/collect_results.py`.
Do not edit by hand; rerun the script instead.

Source: `$STABLEWM_HOME/checkpoints/quentinll/cem_sample_std_results.txt`

## Environment

| | |
|---|---|
| commit (at collection) | `0751317` |
| torch | `2.11.0+cu128` |
| cuda | `12.8` |
| gpu | `NVIDIA GeForce RTX 3060 Laptop GPU` |
| transformers | `5.16.1` |

## Runs

| Policy | Seed | Episodes | Samples | CEM steps | Success | Seconds |
|--------|------|----------|---------|-----------|---------|---------|
| `quentinll/lewm-pusht` | 0 | 50 | 300 | 30 | 47/50 = 94% | 131 |
| `quentinll/lewm-pusht` | 1 | 50 | 300 | 30 | 45/50 = 90% | 132 |
| `quentinll/lewm-pusht` | 2 | 50 | 300 | 30 | 40/50 = 80% | 133 |

## Full-protocol summary

3 runs at 50 episodes, 300 samples, 30 CEM steps.

| | |
|---|---|
| Mean | 88.0% |
| Std | 7.2 |
| Range | 80% to 94% |
| Pooled | 132/150 = 88.0% |

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
