"""Rebuild a Hi-LeWM model from a ``*_weights.ckpt`` file, CPU-only.

The artifact's own loading path goes through ``stable_worldmodel``, which does
not install on macOS x86_64 (see :mod:`hilewm_local.swm_compat`). This module
reconstructs the model from the plain Lightning state dict instead, inferring
every architectural dimension from tensor shapes so that the continuous,
fixed-stride and VQ checkpoints all load without per-variant configuration.

Only two numbers cannot be recovered from shapes -- the attention head counts,
since a state dict records ``heads * dim_head`` but not the split. They are
read from the ``config.yaml`` shipped next to each checkpoint when present, and
otherwise fall back to the paper's values (16 predictor heads, 4 macro-encoder
heads). Either way the resulting inner dimension is checked against the
checkpoint, so a wrong guess raises instead of loading a silently wrong model.

The encoder is a stock HuggingFace ViT, so it needs ``transformers`` but not
``stable_pretraining``. Pass ``with_encoder=False`` (the default) to skip it
when the analysis only touches macro-actions and waypoint latents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch
from torch import nn

from .swm_compat import lewm_module

__all__ = ["HiLeWMSpec", "read_state_dict", "infer_spec", "build_model"]

_STATE_PREFIX = "model."
_PAPER_PREDICTOR_HEADS = 16
_PAPER_MACRO_HEADS = 4


@dataclass(frozen=True)
class HiLeWMSpec:
    """Architecture recovered from a checkpoint."""

    embed_dim: int
    latent_action_dim: int
    num_codes: int | None

    macro_input_dim: int
    macro_model_dim: int
    macro_mlp_dim: int
    macro_num_layers: int
    macro_num_heads: int
    macro_max_seq_len: int

    high_num_frames: int
    high_depth: int
    low_num_frames: int
    low_depth: int
    predictor_heads: int
    predictor_dim_head: int
    predictor_mlp_dim: int

    action_input_dim: int
    proj_hidden_dim: int
    has_encoder: bool
    encoder_layers: int
    macro_to_condition_is_linear: bool
    source: Path | None = field(default=None, compare=False)

    @property
    def is_vq(self) -> bool:
        return self.num_codes is not None

    def describe(self) -> str:
        kind = f"VQ-{self.num_codes}" if self.is_vq else "continuous"
        return (
            f"{kind}  d_l={self.latent_action_dim}  d_z={self.embed_dim}  "
            f"high_ctx={self.high_num_frames}  low_ctx={self.low_num_frames}  "
            f"macro_layers={self.macro_num_layers}  encoder={'yes' if self.has_encoder else 'no'}"
        )


def read_state_dict(path: str | Path) -> dict[str, torch.Tensor]:
    """Load a ``*_weights.ckpt`` and strip the Lightning ``model.`` prefix."""
    checkpoint = torch.load(str(path), map_location="cpu", weights_only=False)
    raw = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
    if not isinstance(raw, dict):
        raise ValueError(f"{path} does not contain a state dict")
    state = {k[len(_STATE_PREFIX):]: v for k, v in raw.items() if k.startswith(_STATE_PREFIX)}
    return state or dict(raw)


def _count_indexed(state: dict[str, torch.Tensor], pattern: str) -> int:
    regex = re.compile(pattern)
    found = {m.group(1) for k in state if (m := regex.match(k))}
    return len(found)


def _run_config(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    sibling = Path(path).parent / "config.yaml"
    if not sibling.exists():
        return {}
    try:
        import yaml
    except ModuleNotFoundError:
        return {}
    try:
        return yaml.safe_load(sibling.read_text()) or {}
    except Exception:  # noqa: BLE001 - a malformed config just means defaults
        return {}


def infer_spec(state: dict[str, torch.Tensor], *, source: str | Path | None = None) -> HiLeWMSpec:
    """Recover every architectural dimension from tensor shapes."""
    config = _run_config(source)
    predictor_heads = int(
        (config.get("predictor_high") or config.get("predictor") or {}).get(
            "heads", _PAPER_PREDICTOR_HEADS
        )
    )
    macro_heads = int((config.get("latent_action_encoder") or {}).get("num_heads", _PAPER_MACRO_HEADS))

    high_pos = state["high_predictor.pos_embedding"]
    low_pos = state["low_predictor.pos_embedding"]
    embed_dim = int(high_pos.shape[2])

    qkv = state["high_predictor.transformer.layers.0.attn.to_qkv.weight"]
    inner_dim = int(qkv.shape[0]) // 3
    if inner_dim % predictor_heads != 0:
        raise ValueError(
            f"predictor inner dim {inner_dim} is not divisible by heads={predictor_heads}; "
            "the checkpoint and the head count disagree"
        )

    macro_in_proj = state["latent_action_encoder.input_proj.weight"]
    macro_out_proj = state["latent_action_encoder.output_proj.weight"]
    macro_pos = state["latent_action_encoder.pos_embedding"]
    macro_model_dim = int(macro_in_proj.shape[0])
    if macro_model_dim % macro_heads != 0:
        raise ValueError(
            f"macro encoder dim {macro_model_dim} is not divisible by heads={macro_heads}"
        )

    codebook = state.get("latent_action_encoder.quantizer.codebook.weight")
    encoder_keys = [k for k in state if k.startswith("encoder.")]

    return HiLeWMSpec(
        embed_dim=embed_dim,
        latent_action_dim=int(macro_out_proj.shape[0]),
        num_codes=int(codebook.shape[0]) if codebook is not None else None,
        macro_input_dim=int(macro_in_proj.shape[1]),
        macro_model_dim=macro_model_dim,
        macro_mlp_dim=int(state["latent_action_encoder.encoder.layers.0.linear1.weight"].shape[0]),
        macro_num_layers=_count_indexed(state, r"latent_action_encoder\.encoder\.layers\.(\d+)\."),
        macro_num_heads=macro_heads,
        macro_max_seq_len=int(macro_pos.shape[1]) - 1,
        high_num_frames=int(high_pos.shape[1]),
        high_depth=_count_indexed(state, r"high_predictor\.transformer\.layers\.(\d+)\."),
        low_num_frames=int(low_pos.shape[1]),
        low_depth=_count_indexed(state, r"low_predictor\.transformer\.layers\.(\d+)\."),
        predictor_heads=predictor_heads,
        predictor_dim_head=inner_dim // predictor_heads,
        predictor_mlp_dim=int(state["high_predictor.transformer.layers.0.mlp.net.1.weight"].shape[0]),
        action_input_dim=int(state["action_encoder.patch_embed.weight"].shape[1]),
        proj_hidden_dim=int(state["projector.net.0.weight"].shape[0]),
        has_encoder=bool(encoder_keys),
        encoder_layers=_count_indexed(state, r"encoder\.encoder\.layer\.(\d+)\."),
        macro_to_condition_is_linear="macro_to_condition.weight" in state,
        source=Path(source) if source is not None else None,
    )


def _sub_state(state: dict[str, torch.Tensor], prefix: str) -> dict[str, torch.Tensor]:
    return {k[len(prefix):]: v for k, v in state.items() if k.startswith(prefix)}


def _build_predictor(module: Any, spec: HiLeWMSpec, *, num_frames: int, depth: int) -> nn.Module:
    return module.Predictor(
        num_frames=num_frames,
        depth=depth,
        heads=spec.predictor_heads,
        mlp_dim=spec.predictor_mlp_dim,
        input_dim=spec.embed_dim,
        hidden_dim=spec.embed_dim,
        output_dim=spec.embed_dim,
        dim_head=spec.predictor_dim_head,
        dropout=0.0,
        emb_dropout=0.0,
    )


def _build_macro_encoder(spec: HiLeWMSpec) -> nn.Module:
    kwargs = dict(
        input_dim=spec.macro_input_dim,
        latent_dim=spec.latent_action_dim,
        model_dim=spec.macro_model_dim,
        num_layers=spec.macro_num_layers,
        num_heads=spec.macro_num_heads,
        mlp_dim=spec.macro_mlp_dim,
        dropout=0.0,
        max_seq_len=spec.macro_max_seq_len,
    )
    if spec.is_vq:
        from h_le_wm.models.vq import VQActionEncoder

        return VQActionEncoder(num_codes=spec.num_codes, decoder_hidden_dim=768, **kwargs)

    from h_le_wm.models.latent_action import LatentActionEncoder

    return LatentActionEncoder(**kwargs)


def _build_mlp(module: Any, spec: HiLeWMSpec) -> nn.Module:
    return module.MLP(
        input_dim=spec.embed_dim,
        hidden_dim=spec.proj_hidden_dim,
        output_dim=spec.embed_dim,
        norm_fn=nn.BatchNorm1d,
    )


def _build_encoder(spec: HiLeWMSpec) -> nn.Module:
    from transformers import ViTConfig, ViTModel

    config = ViTConfig(
        hidden_size=spec.embed_dim,
        num_hidden_layers=spec.encoder_layers,
        num_attention_heads=3,
        intermediate_size=4 * spec.embed_dim,
        image_size=224,
        patch_size=14,
    )
    return ViTModel(config, add_pooling_layer=False)


def build_model(
    path: str | Path,
    *,
    with_encoder: bool = False,
    device: str | torch.device = "cpu",
    strict: bool = True,
) -> tuple[nn.Module, HiLeWMSpec]:
    """Rebuild a ``HiJEPA`` from ``path`` and return it together with its spec.

    With ``with_encoder=False`` the pixel encoder is replaced by ``nn.Identity``.
    ``rollout_high``, ``get_cost_high``, ``rollout_low`` and ``get_cost_low``
    all work either way, since they consume latents rather than pixels.
    """
    from h_le_wm.models.jepa import HiJEPA

    module = lewm_module()
    state = read_state_dict(path)
    spec = infer_spec(state, source=path)

    high_predictor = _build_predictor(module, spec, num_frames=spec.high_num_frames, depth=spec.high_depth)
    high_predictor.load_state_dict(_sub_state(state, "high_predictor."), strict=strict)

    low_predictor = _build_predictor(module, spec, num_frames=spec.low_num_frames, depth=spec.low_depth)
    low_predictor.load_state_dict(_sub_state(state, "low_predictor."), strict=strict)

    macro_encoder = _build_macro_encoder(spec)
    # VQ checkpoints carry a training-only action-chunk decoder; it is not part
    # of the planning path, so a non-strict load is correct for them.
    macro_encoder.load_state_dict(_sub_state(state, "latent_action_encoder."), strict=strict and not spec.is_vq)

    action_encoder = module.Embedder(
        input_dim=spec.action_input_dim,
        smoothed_dim=spec.action_input_dim,
        emb_dim=spec.embed_dim,
        mlp_scale=int(state["action_encoder.embed.0.weight"].shape[0]) // spec.embed_dim,
    )
    action_encoder.load_state_dict(_sub_state(state, "action_encoder."), strict=strict)

    if spec.macro_to_condition_is_linear:
        macro_to_condition: nn.Module = nn.Linear(spec.latent_action_dim, spec.embed_dim)
        macro_to_condition.load_state_dict(_sub_state(state, "macro_to_condition."), strict=strict)
    else:
        macro_to_condition = nn.Identity()

    projections: dict[str, nn.Module] = {}
    for name in ("projector", "low_pred_proj", "high_pred_proj"):
        head = _build_mlp(module, spec)
        head.load_state_dict(_sub_state(state, f"{name}."), strict=strict)
        projections[name] = head

    if with_encoder:
        if not spec.has_encoder:
            raise ValueError(f"{path} carries no encoder weights")
        encoder: nn.Module = _build_encoder(spec)
        missing = encoder.load_state_dict(_sub_state(state, "encoder."), strict=False)
        if missing.missing_keys:
            raise ValueError(f"encoder is missing {len(missing.missing_keys)} tensors, e.g. {missing.missing_keys[:3]}")
    else:
        encoder = nn.Identity()

    model = HiJEPA(
        encoder=encoder,
        low_predictor=low_predictor,
        action_encoder=action_encoder,
        high_predictor=high_predictor,
        latent_action_encoder=macro_encoder,
        macro_to_condition=macro_to_condition,
        projector=projections["projector"],
        low_pred_proj=projections["low_pred_proj"],
        high_pred_proj=projections["high_pred_proj"],
    )
    return model.to(device).eval(), spec
