# Checkpoints

This directory contains trained Hi-LeWM checkpoints and decoder probe weights
for the paper artifact.

## Main Files

```text
pusht/main/pusht_hi_lewm_epoch15_object.ckpt
cube/main/cube_hi_lewm_epoch15_object.ckpt
pusht/probes/phase_a/pusht_decoder_probe_phase_a.pt
pusht/probes/phase_b/pusht_decoder_probe_phase_b.pt
```

These are the paper-facing Hi-LeWM and decoder-probe files.

## Extra Variants

The archive also includes supplementary trained variants used for exploratory
representation and diagnostic comparisons:

```text
pusht/fixed_stride_dim32/
pusht/fixed_stride_dim8/
pusht/vq/vq16/
pusht/vq/vq128/
```

Both object checkpoints and training-weight checkpoints are kept where
available. The paper-facing workflows use the object checkpoints.

## Baseline Checkpoints

The two flat LeWorldModel baseline checkpoints are not redistributed here. From
`../code`, fetch them with:

```bash
bash scripts/setup_baseline_checkpoints.sh fetch-baselines
```

## Staging

From `../code`, stage the included files into `STABLEWM_HOME` with:

```bash
bash scripts/setup_checkpoints.sh \
  --checkpoint hierarchical/pusht/default_epoch15="$PWD/../checkpoints/pusht/main/pusht_hi_lewm_epoch15_object.ckpt" \
  --checkpoint hierarchical/cube/default_epoch15="$PWD/../checkpoints/cube/main/cube_hi_lewm_epoch15_object.ckpt" \
  --checkpoint probe/pusht/phase_a="$PWD/../checkpoints/pusht/probes/phase_a/pusht_decoder_probe_phase_a.pt" \
  --checkpoint probe/pusht/phase_b="$PWD/../checkpoints/pusht/probes/phase_b/pusht_decoder_probe_phase_b.pt"
```

## Config Files

Each run directory includes a sanitized `config.yaml` sidecar for inspection.
The original cluster-local paths were replaced with portable paths or removed.
