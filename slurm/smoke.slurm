#!/bin/bash
# CPU-only preflight. Submit this before spending a GPU slot.
#
#   slurm/submit.sh slurm/smoke.slurm
#
# It asks for no GPU on purpose. The debug partition usually has idle non-GPU
# nodes even when every V100 is allocated, so this starts in seconds while a
# GPU job waits hours. It catches the failures that are not about the GPU:
# missing dataset, checkpoints that will not load, no video driver on a
# headless node, a config that no longer composes.
#SBATCH --job-name=swm-smoke
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=slurm/logs/%x_%j.log
#SBATCH --error=slurm/logs/%x_%j.log

set -euo pipefail
source slurm/truba_env.sh

# This node has no GPU, so preflight cannot detect what it must support.
# sm_70 is the V100 in akya-cuda; sm_60 (the P100s in barbun-cuda) is in
# the same cu126 build, so checking the one covers both.
export PREFLIGHT_REQUIRE_ARCH=sm_70

srun python scripts/preflight.py
