#!/bin/bash
# Submit a job script from this directory with the right working directory.
#
# SLURM #SBATCH directives cannot expand shell variables, so --chdir cannot be
# written into the job scripts without hardcoding somebody's username. This
# wrapper computes it instead.
#
# Usage:
#   slurm/submit.sh slurm/eval.slurm --export=ALL,POLICY=quentinll/lewm-pusht
#
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$REPO/slurm/logs"
exec sbatch --chdir="$REPO" "$@"
