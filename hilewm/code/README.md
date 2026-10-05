# Hi-LeWM Code

This directory contains the Hi-LeWM implementation, experiment configs,
diagnostic scripts, tests, and environment files.

## Setup

```bash
conda env create -f environment-gpu.yml
conda activate lewm-gpu
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
export STABLEWM_HOME="$PWD/data/stablewm"
```

Use `environment-gpu.yml` for reproduction. `environment.yml` is only for
lightweight inspection.

## External LeWorldModel Source

This artifact does not redistribute the upstream LeWorldModel source. Fetch it
into `third_party/lewm` before running baseline-dependent commands:

```bash
mkdir -p third_party
git clone https://github.com/lucas-maes/le-wm.git third_party/lewm
```

See `THIRD_PARTY_LEWM.md` for details.

## Datasets

```bash
source scripts/setup_paper_datasets.sh --home "$STABLEWM_HOME"
```

## Commands

```bash
bash scripts/validate_preflight.sh
bash scripts/run_pusht_smoke.sh --dry-run
bash scripts/run_paper_reproduction.sh
bash scripts/run_paper_from_scratch.sh
```

Outputs are written under `STABLEWM_HOME/repro/`; trained runs live under
`STABLEWM_HOME/runs/`.
