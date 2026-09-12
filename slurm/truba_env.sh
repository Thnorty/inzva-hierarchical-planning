# shellcheck shell=bash
# Shared environment for every TRUBA job. Source this, do not execute it.
# (No shebang on purpose: it is sourced, never executed. The directive above
# is what tells shellcheck which shell to assume.)
#
# Everything here is a fact about the cluster rather than a choice about the
# experiment. Experiment parameters live in scripts/plan/config/inzva_*.yaml so
# that they stay identical between TRUBA and everyone's laptop.

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export REPO

# Same layout as every other machine: STABLEWM_HOME is .stable-wm inside the
# checkout. See INZVA_README.md section 3.
export STABLEWM_HOME="$REPO/.stable-wm"

# The HF cache is shared across projects on purpose. It holds facebook/dinov2-small,
# which DINO-WM pulls at construction time, and re-downloading it per job is waste.
export HF_HOME="${HF_HOME:-/arf/scratch/$USER/.hf_cache}"
export UV_CACHE_DIR="/arf/scratch/$USER/.uv-cache"

# Compute nodes have no display. PushT renders through pygame, so without a dummy
# video driver every eval dies at the first render() with "No available video
# device". This is the single most common way a TRUBA job fails in the first
# ten seconds.
export SDL_VIDEODRIVER=dummy
export MUJOCO_GL=egl
export PYGAME_HIDE_SUPPORT_PROMPT=1

# Do not let BLAS grab every core on a shared node.
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-10}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK:-10}"

cd "$REPO" || return 1
# shellcheck disable=SC1091
source .venv/bin/activate

echo "node        : $(hostname)"
echo "repo        : $REPO"
echo "STABLEWM_HOME: $STABLEWM_HOME"
python -c "import torch; print('torch       :', torch.__version__); print('gpu         :', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE')"
