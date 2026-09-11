# Eval results

Generated 2026-09-11 09:14 UTC by `scripts/collect_results.py`.
Do not edit by hand; rerun the script instead.

Source: `$STABLEWM_HOME/checkpoints/quentinll/inzva_pusht_results.txt`

## Environment

| | |
|---|---|
| commit (at collection) | `90de485` |
| torch | `2.11.0+cu128` |
| cuda | `12.8` |
| gpu | `NVIDIA GeForce RTX 3060 Laptop GPU` |
| transformers | `5.16.1` |

## Runs

| Policy | Seed | Episodes | Samples | CEM steps | Success | Seconds |
|--------|------|----------|---------|-----------|---------|---------|
| `quentinll/lewm-pusht` | 0 | 50 | 300 | 30 | 42/50 = 84% | 207 |
| `quentinll/lewm-pusht` | 1 | 50 | 300 | 30 | 48/50 = 96% | 298 |
| `quentinll/lewm-pusht` | 2 | 50 | 300 | 30 | 41/50 = 82% | 131 |

## Full-protocol summary

3 runs at 50 episodes, 300 samples, 30 CEM steps.

| | |
|---|---|
| Mean | 87.3% |
| Std | 7.6 |
| Range | 82% to 96% |
| Pooled | 131/150 = 87.3% |

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
