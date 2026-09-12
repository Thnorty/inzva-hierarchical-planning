#!/bin/bash
# Evaluate a world-model checkpoint under the shared eval protocol.
#
# Submit through the wrapper so --chdir is set:
#
#   slurm/submit.sh slurm/eval.slurm --export=ALL,POLICY=quentinll/lewm-pusht
#   slurm/submit.sh slurm/eval.slurm --export=ALL,POLICY=dinowm_kotmul_adapted,OBJECTIVE=goal_mse_pixels_proprio
#
# Variables (all optional except POLICY):
#   POLICY     checkpoint name, as load_pretrained resolves it
#   CONFIG     eval config name          (default inzva_pusht)
#   SEEDS      comma-separated seed list (default 0,1,2)
#   OBJECTIVE  hydra objective override  (default: leave the config's own)
#   EXTRA      any further hydra overrides, space separated
#   STEM       basename for the tracked record in notes/results
#              (default truba; use a distinct one per policy)
#
# debug is the default partition because its GPU nodes are a subset of
# akya-cuda and it reaches the front of the queue sooner. Its ceiling is 4
# hours, which fits an eval but not a training run. Override for long jobs:
#   slurm/submit.sh slurm/eval.slurm -p akya-cuda -t 1-00:00:00 --export=...
#SBATCH --job-name=swm-eval
#SBATCH --partition=debug
#SBATCH --constraint=akya-cuda
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --time=03:59:00
#SBATCH --output=slurm/logs/%x_%j.log
#SBATCH --error=slurm/logs/%x_%j.log

set -euo pipefail
source slurm/truba_env.sh

: "${POLICY:?set POLICY, e.g. --export=ALL,POLICY=quentinll/lewm-pusht}"
CONFIG="${CONFIG:-inzva_pusht}"
SEEDS="${SEEDS:-0,1,2}"
EXTRA="${EXTRA:-}"
STEM="${STEM:-truba}"
[ -n "${OBJECTIVE:-}" ] && EXTRA="objective=$OBJECTIVE $EXTRA"

echo "policy      : $POLICY"
echo "config      : $CONFIG"
echo "seeds       : $SEEDS"
echo "extra       : $EXTRA"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

# -m has to come before the overrides. Hydra parses the overrides as one
# trailing positional list, so an option written after them ends that list
# and argparse rejects the rest: "unrecognized arguments: seed=0,1,2".
# shellcheck disable=SC2086
srun python scripts/plan/eval_wm.py --config-name "$CONFIG" -m \
    policy="$POLICY" seed="$SEEDS" $EXTRA

# Collect inside the allocation, while the GPU is still visible. Collected
# afterwards on a login node it records "gpu: cpu", which is worse than no
# provenance at all: the table exists to say which card produced the numbers.
#
# eval_wm.py appends to checkpoints/<dirname of policy>/<output.filename>
# (eval_wm.py:137), so a policy id with no slash lands directly in
# checkpoints/. Copy that file under STEM first, so two policies sharing one
# config do not overwrite each other's record.
POLICY_DIR=$(dirname "$POLICY")
RESULTS_DIR="$STABLEWM_HOME/checkpoints/$POLICY_DIR"
SRC=$(python -c "import sys, yaml; print(yaml.safe_load(open('scripts/plan/config/' + sys.argv[1] + '.yaml'))['output']['filename'])" "$CONFIG")
cp "$RESULTS_DIR/$SRC" "$RESULTS_DIR/${STEM}_results.txt"
srun python scripts/collect_results.py \
    --results-file "${STEM}_results.txt" --policy-dir "$POLICY_DIR"
