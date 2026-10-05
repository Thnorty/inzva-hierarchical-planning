"""CPU-only, stable_worldmodel-free access to the released Hi-LeWM checkpoints.

Our machine is an Intel Mac, where ``stable_worldmodel`` cannot be installed
(see :mod:`hilewm_local.swm_compat`). These helpers rebuild the model from the
plain ``*_weights.ckpt`` state dicts so that every analysis that works on
latents -- macro-action support, codebook statistics, high-level rollouts and
planning costs -- runs locally. Environment rollouts and success rates still
need the full stack and belong on Colab.
"""

from __future__ import annotations

from .data import HDF5Columns, build_action_scaler, write_episode_subset
from .loader import HiLeWMSpec, build_model, infer_spec, read_state_dict
from .probe import DecoderSpec, decode_latents, load_decoder
from .swm_compat import lewm_module

__all__ = [
    "HiLeWMSpec",
    "build_model",
    "infer_spec",
    "read_state_dict",
    "lewm_module",
    "HDF5Columns",
    "build_action_scaler",
    "write_episode_subset",
    "DecoderSpec",
    "load_decoder",
    "decode_latents",
]
