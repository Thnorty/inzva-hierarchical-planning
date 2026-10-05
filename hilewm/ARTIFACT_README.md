# Hi-LeWM Artifact

This archive accompanies the paper "Mind the Gap: Promises and Pitfalls of
Hierarchical Planning in LeWorldModel".

## Layout

```text
code/         Hi-LeWM source code, configs, scripts, tests, environments
checkpoints/  Hi-LeWM checkpoints and decoder probe weights
```

Start with:

- `code/README.md` for code setup and commands.
- `checkpoints/README.md` for included checkpoints and staging.
- `code/THIRD_PARTY_LEWM.md` for the external LeWorldModel source dependency.

## Minimal Reproduction Flow

```bash
cd code
conda env create -f environment-gpu.yml
conda activate lewm-gpu
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
export STABLEWM_HOME="$PWD/data/stablewm"

source scripts/setup_paper_datasets.sh --home "$STABLEWM_HOME"
bash scripts/setup_baseline_checkpoints.sh fetch-baselines
bash scripts/setup_checkpoints.sh \
  --checkpoint hierarchical/pusht/default_epoch15="$PWD/../checkpoints/pusht/main/pusht_hi_lewm_epoch15_object.ckpt" \
  --checkpoint hierarchical/cube/default_epoch15="$PWD/../checkpoints/cube/main/cube_hi_lewm_epoch15_object.ckpt" \
  --checkpoint probe/pusht/phase_a="$PWD/../checkpoints/pusht/probes/phase_a/pusht_decoder_probe_phase_a.pt" \
  --checkpoint probe/pusht/phase_b="$PWD/../checkpoints/pusht/probes/phase_b/pusht_decoder_probe_phase_b.pt"

bash scripts/validate_preflight.sh
bash scripts/run_paper_reproduction.sh
```

The archive does not redistribute the upstream LeWorldModel source code. Fetch
it separately as described in `code/THIRD_PARTY_LEWM.md`.
