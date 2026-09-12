#!/bin/bash
# Submit a job script from this directory with the right working directory.
#
# Two cluster facts make a wrapper worth having.
#
# 1. SLURM #SBATCH directives cannot expand shell variables, so --chdir cannot
#    be written into the job scripts without hardcoding somebody's username.
#    Jobs are rejected unless they run from under /arf/scratch, so it has to be
#    set somewhere.
#
# 2. sbatch parses its command line as `sbatch [options] script [job args]`.
#    Anything written after the script path is handed to the job rather than to
#    sbatch, so
#
#        sbatch slurm/eval.slurm --export=ALL,POLICY=...
#
#    silently ignores the --export and the job then dies on an unset variable.
#    A -t written there is ignored just as quietly, and the job keeps whatever
#    time limit the script declared. This wrapper finds the script in the
#    argument list and moves it last, so the options can be written in whatever
#    order reads best.
#
# Usage:
#   slurm/submit.sh slurm/eval.slurm --export=ALL,POLICY=quentinll/lewm-pusht
#   slurm/submit.sh slurm/eval.slurm -t 00:45:00 --export=ALL,POLICY=...
#
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$REPO/slurm/logs"

script=""
opts=()
for arg in "$@"; do
    case "$arg" in
        *.slurm)
            if [ -z "$script" ]; then script="$arg"; else opts+=("$arg"); fi
            ;;
        *)
            opts+=("$arg")
            ;;
    esac
done

if [ -z "$script" ]; then
    echo "usage: slurm/submit.sh <job.slurm> [sbatch options]" >&2
    exit 2
fi

exec sbatch --chdir="$REPO" "${opts[@]}" "$script"
