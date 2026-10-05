"""Decode Hi-LeWM waypoint latents back into images with the released probes.

`h_le_wm/probe/model.py` holds the decoder we want (`LatentToPixelDecoder`),
but its module-level imports pull `stable_pretraining` and
`h_le_wm.baseline.adapter`, neither of which resolves on this machine. Both are
used only inside functions we do not call -- `spt` for the ImageNet statistics
and `BASELINE_ROOT` for a checkpoint search path -- so we install small stand-ins
before loading the file and otherwise run the authors' decoder unchanged.

Denormalisation is a second, separate trap. `stable_pretraining` may well be
installed and still be unusable: on this machine importing `spt.data` raises
`AttributeError: module 'torchvision.transforms.v2' has no attribute
'GaussianNoise'`, because that transform arrived in torchvision 0.18 and torch
2.2.2 -- the Intel Mac ceiling -- ships 0.17.2. So we probe the artifact's own
`imagenet_mean_std()` once and fall back to the standard torchvision constants,
which is what `stable_pretraining` records anyway. `decoder_stats_source` says
which one was used; if a decode ever looks systematically off in colour, check
that first.
"""

from __future__ import annotations

import importlib
import importlib.util
import re
import sys
import types
from pathlib import Path
from typing import Any

import torch
from torch import nn

__all__ = [
    "load_decoder",
    "decode_latents",
    "probe_model_module",
    "decoder_stats_source",
    "DecoderSpec",
]

_MODULE_NAME = "_hilewm_local_probe_model"
_CODE_ROOT = Path(__file__).resolve().parents[2] / "code"

_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]


def _install_stubs() -> None:
    if "stable_pretraining" not in sys.modules:
        try:
            importlib.import_module("stable_pretraining")
        except Exception:  # noqa: BLE001 - build the stand-in instead
            spt = types.ModuleType("stable_pretraining")
            data = types.ModuleType("stable_pretraining.data")
            stats = types.ModuleType("stable_pretraining.data.dataset_stats")
            stats.ImageNet = {"mean": _IMAGENET_MEAN, "std": _IMAGENET_STD}
            data.dataset_stats = stats
            spt.data = data
            sys.modules["stable_pretraining"] = spt
            sys.modules["stable_pretraining.data"] = data
            sys.modules["stable_pretraining.data.dataset_stats"] = stats

    if "h_le_wm.baseline.adapter" not in sys.modules:
        try:
            importlib.import_module("h_le_wm.baseline.adapter")
        except Exception:  # noqa: BLE001
            adapter = types.ModuleType("h_le_wm.baseline.adapter")
            adapter.BASELINE_ROOT = _CODE_ROOT / "third_party" / "lewm"
            sys.modules["h_le_wm.baseline.adapter"] = adapter


def probe_model_module() -> Any:
    """Return `h_le_wm.probe.model`, loading it past its unresolvable imports."""
    if _MODULE_NAME in sys.modules:
        return sys.modules[_MODULE_NAME]

    _install_stubs()
    path = _CODE_ROOT / "h_le_wm" / "probe" / "model.py"
    if not path.exists():
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(_MODULE_NAME, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot build a module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


class DecoderSpec(dict):
    """Decoder geometry recovered from a probe bundle."""

    def describe(self) -> str:
        return (
            f"latent_dim={self['latent_dim']}  hidden={self['hidden_dim']}  "
            f"depth={self['depth']}  heads={self['heads']}  "
            f"patch={self['patch_size']}  img={self['img_size']}"
        )


def _infer_decoder_spec(state: dict[str, torch.Tensor], cfg: Any) -> DecoderSpec:
    latent_proj = state["latent_proj.weight"]          # (hidden, latent)
    query_tokens = state["query_tokens"]               # (1, num_patches, hidden)
    patch_head = state["patch_head.weight"]            # (patch_dim, hidden)

    hidden_dim, latent_dim = int(latent_proj.shape[0]), int(latent_proj.shape[1])
    num_patches = int(query_tokens.shape[1])
    grid = int(round(num_patches**0.5))
    if grid * grid != num_patches:
        raise ValueError(f"{num_patches} patch queries is not a square grid")

    patch_dim = int(patch_head.shape[0])
    out_channels = 3
    patch_area = patch_dim // out_channels
    patch_size = int(round(patch_area**0.5))
    if patch_size * patch_size * out_channels != patch_dim:
        raise ValueError(f"cannot split patch_dim={patch_dim} into a square RGB patch")

    depth = len({m.group(1) for k in state if (m := re.match(r"blocks\.(\d+)\.", k))})

    # heads and mlp_ratio are not recoverable from shapes; take the bundle's cfg.
    decoder_cfg: dict[str, Any] = {}
    try:
        decoder_cfg = dict(cfg["probe"]["decoder"]) if cfg is not None else {}
    except Exception:  # noqa: BLE001 - a missing cfg just means defaults
        decoder_cfg = {}

    return DecoderSpec(
        latent_dim=latent_dim,
        hidden_dim=hidden_dim,
        depth=depth,
        heads=int(decoder_cfg.get("heads", 4)),
        mlp_ratio=float(decoder_cfg.get("mlp_ratio", 4.0)),
        patch_size=patch_size,
        img_size=grid * patch_size,
        out_channels=out_channels,
    )


def load_decoder(
    path: str | Path,
    *,
    device: str | torch.device = "cpu",
) -> tuple[nn.Module, DecoderSpec]:
    """Load a probe bundle (`*_probe.pt` / `*_phase_[ab].pt`) into a decoder."""
    module = probe_model_module()
    payload = torch.load(str(Path(path).expanduser()), map_location="cpu", weights_only=False)
    state = module.load_decoder_state_dict(path)
    cfg = payload.get("cfg") if isinstance(payload, dict) else None
    spec = _infer_decoder_spec(state, cfg)

    decoder = module.LatentToPixelDecoder(
        latent_dim=spec["latent_dim"],
        img_size=spec["img_size"],
        patch_size=spec["patch_size"],
        hidden_dim=spec["hidden_dim"],
        depth=spec["depth"],
        heads=spec["heads"],
        mlp_ratio=spec["mlp_ratio"],
        dropout=0.0,
        out_channels=spec["out_channels"],
    )
    decoder.load_state_dict(state, strict=True)
    return decoder.to(device).eval(), spec


_stats_source: str | None = None


def decoder_stats_source() -> str:
    """Whether denormalisation used the artifact's stats or our fallback."""
    _imagenet_stats()
    return _stats_source or "unknown"


def _imagenet_stats() -> tuple[torch.Tensor, torch.Tensor]:
    global _stats_source
    if _stats_source is None:
        try:
            mean, std = probe_model_module().imagenet_mean_std()
            _stats_source = "h_le_wm.probe.model.imagenet_mean_std"
        except Exception:  # noqa: BLE001 - stable_pretraining is unusable here
            mean = torch.tensor(_IMAGENET_MEAN, dtype=torch.float32).view(1, -1, 1, 1)
            std = torch.tensor(_IMAGENET_STD, dtype=torch.float32).view(1, -1, 1, 1)
            _stats_source = "hilewm_local fallback (torchvision ImageNet constants)"
        _imagenet_stats.cached = (mean, std)  # type: ignore[attr-defined]
    return _imagenet_stats.cached  # type: ignore[attr-defined]


@torch.inference_mode()
def decode_latents(
    decoder: nn.Module,
    latents: torch.Tensor,
    *,
    denormalize: bool = True,
) -> torch.Tensor:
    """Decode ``(N, D)`` latents into ``(N, 3, H, W)`` images.

    With ``denormalize=True`` the ImageNet normalisation the encoder expects is
    undone and the result is clamped to ``[0, 1]``, ready for `save_image`.
    """
    if latents.ndim == 1:
        latents = latents.unsqueeze(0)
    if latents.ndim != 2:
        raise ValueError(f"latents must be (N, D), got {tuple(latents.shape)}")

    device = next(decoder.parameters()).device
    images = decoder(latents.to(device))
    if denormalize:
        mean, std = _imagenet_stats()
        mean = mean.to(device=images.device, dtype=images.dtype)
        std = std.to(device=images.device, dtype=images.dtype)
        images = (images * std + mean).clamp(0.0, 1.0)
    return images
