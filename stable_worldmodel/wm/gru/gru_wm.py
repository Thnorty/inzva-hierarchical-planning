"""Fine GRU world model for coarse-to-fine planning on PushT.

This is the *fine* half of the two-speed world model in the project spec: an
image encoder into a flat latent, plus a recurrent dynamics model that predicts
the latent one environment step ahead. The coarse model (stride ``k``) will
share this encoder and latent space.

It mirrors LeWM wherever LeWM already works on this data: the same ViT-tiny
encoder trained from scratch, the same BatchNorm projector, the same action
embedder, and the same SIGReg regularizer during training to stop the latent
collapsing. The one deliberate change is the predictor. LeWM attends over a
window of context frames; ours is a GRU cell that is **Markovian in the
latent**: the next latent depends only on the current latent and action.

That property is what the hierarchy needs. A rollout can start from a single
encoded frame (``history_len: 1`` in ``inzva_gru.yaml``), and a coarse model can
hand the fine model any latent as a waypoint without also inventing a history
to go with it.

Planning reaches this model through the unmodified harness: it satisfies
``stable_worldmodel.protocols.Dynamics`` and is scored by
``ShootingCostEvaluator`` with ``GoalMSE``, exactly like LeWM.
"""

import torch
from einops import rearrange
from torch import nn


class GRUPredictor(nn.Module):
    """One-step latent dynamics, ``z' = z + out(GRUCell(a, in(z)))``.

    Two choices here are load-bearing.

    **Residual output.** At one environment step per prediction, consecutive
    latents are nearly identical, so the dynamics are close to the identity. A
    plain ``GRUCell`` whose hidden state *is* the latent cannot represent that
    well: its candidate state is squashed through ``tanh`` into ``(-1, 1)``,
    while SIGReg pushes the encoder's latents toward a unit Gaussian, where
    values beyond one standard deviation are routine. Predicting a residual
    removes both problems, and zero-initialising the output layer makes the
    untrained model start as "nothing moves", a sensible baseline to improve on.

    **The GRU state is recomputed from the latent at every step.** Nothing is
    carried between steps except ``z`` itself, so the model is Markovian in the
    latent. That is what lets any single encoded frame, or any coarse waypoint,
    serve as a starting point.

    Args:
        latent_dim: Size of the latent ``z`` produced by the encoder.
        action_dim: Size of the embedded action fed to the cell.
        hidden_dim: Width of the GRU cell. Defaults to ``latent_dim``, in which
            case the latent feeds the cell directly with no input projection.
    """

    def __init__(
        self, latent_dim: int, action_dim: int, hidden_dim: int | None = None
    ):
        super().__init__()
        hidden_dim = hidden_dim or latent_dim
        self.latent_dim = latent_dim
        self.hidden_dim = hidden_dim
        self.in_proj = (
            nn.Identity()
            if hidden_dim == latent_dim
            else nn.Linear(latent_dim, hidden_dim)
        )
        self.cell = nn.GRUCell(action_dim, hidden_dim)
        self.out_proj = nn.Linear(hidden_dim, latent_dim)
        nn.init.zeros_(self.out_proj.weight)
        nn.init.zeros_(self.out_proj.bias)

    def forward(self, z: torch.Tensor, a: torch.Tensor) -> torch.Tensor:
        """Advance one step.

        Args:
            z: Current latent, ``(N, latent_dim)``.
            a: Embedded action taken from that latent, ``(N, action_dim)``.

        Returns:
            The predicted next latent, ``(N, latent_dim)``.
        """
        return z + self.out_proj(self.cell(a, self.in_proj(z)))


class GRUWorldModel(nn.Module):
    """Image encoder plus Markovian GRU dynamics over a flat latent.

    Constructed from a Hydra config the same way ``LeWM`` is, so a checkpoint
    written with ``save_pretrained`` loads back through ``load_pretrained`` and
    therefore through ``scripts/plan/eval_wm.py`` with no special handling.

    The attribute names ``encoder`` and ``predictor`` are not cosmetic:
    ``eval_wm.py`` reaches for exactly those two when ``compile: true``.

    Args:
        encoder: Image backbone. Either a HuggingFace-style model whose output
            has ``last_hidden_state`` (the first token is used, as in LeWM), or
            any module returning ``(N, D)`` directly.
        predictor: One-step dynamics, normally a :class:`GRUPredictor`.
        action_encoder: Maps actions ``(N, T, action_dim)`` to embeddings. For a
            coarse model its input is the ``stride`` actions spanned by one
            prediction, so ``input_dim`` is ``stride * env_action_dim``.
        projector: Maps the encoder output to the latent. Defaults to identity.
        stride: Environment steps advanced by one call to ``predictor``. 1 for
            the fine model. The coarse model of the hierarchy sets ``k``, and
            planning reads this to convert between its own steps and
            environment steps. It is metadata: nothing here behaves
            differently, because a strided model is just a model trained on
            strided data.
    """

    def __init__(
        self,
        encoder: nn.Module,
        predictor: nn.Module,
        action_encoder: nn.Module,
        projector: nn.Module | None = None,
        stride: int = 1,
        **kwargs,
    ):
        super().__init__()
        self.encoder = encoder
        self.predictor = predictor
        self.action_encoder = action_encoder
        self.projector = projector or nn.Identity()
        self.stride = stride

    def _embed(self, pixels: torch.Tensor) -> torch.Tensor:
        """Encode a flat batch of images, ``(N, C, H, W) -> (N, D)``."""
        out = self.encoder(pixels, interpolate_pos_encoding=True)
        if hasattr(out, 'last_hidden_state'):
            out = out.last_hidden_state[:, 0]
        return self.projector(out)

    def encode(self, info: dict) -> dict:
        """Embed observations into the latent space.

        Reads ``pixels`` of shape ``(B, T, C, H, W)`` and writes ``emb`` of
        shape ``(B, T, D)``. Actions are optional: the planner's goal encoder
        strips them before calling this, since a goal prescribes a state, not an
        action. When ``action`` is present it is embedded into ``act_emb``.
        """
        pixels = info['pixels'].to(next(self.encoder.parameters()).dtype)
        b = pixels.size(0)
        emb = self._embed(rearrange(pixels, 'b t ... -> (b t) ...'))
        info['emb'] = rearrange(emb, '(b t) d -> b t d', b=b)
        if 'action' in info:
            info['act_emb'] = self.action_encoder(info['action'])
        return info

    def unroll(self, z: torch.Tensor, act_emb: torch.Tensor) -> torch.Tensor:
        """Roll the dynamics open-loop from one latent.

        Shared by training and planning, so the two cannot drift apart.

        Args:
            z: Starting latent, ``(N, D)``.
            act_emb: Embedded actions to apply in order, ``(N, T, A)``.

        Returns:
            The ``T`` predicted latents, ``(N, T, D)``. The starting latent is
            not included.
        """
        preds = []
        for t in range(act_emb.size(1)):
            z = self.predictor(z, act_emb[:, t])
            preds.append(z)
        return torch.stack(preds, dim=1)

    def rollout(self, info: dict, action_sequence: torch.Tensor) -> dict:
        """Roll candidate action sequences forward, for planning.

        Satisfies ``stable_worldmodel.protocols.Dynamics``.

        Args:
            info: Planner state. ``pixels`` holds ``H`` context frames of shape
                ``(B, S, H, C, h, w)``. With ``history_len: 1``, the setting
                this model is designed for, ``H`` is 1. Larger ``H`` is
                accepted: every context frame is encoded and returned, but only
                the last one seeds the rollout, because the dynamics are
                Markovian and earlier frames carry no extra information.
            action_sequence: Strictly-future candidates, ``(B, S, T, action_dim)``.

        Returns:
            ``info`` with ``predicted_emb`` of shape ``(B, S, H + T, D)``, whose
            first ``H`` entries are the encoded context frames.
        """
        assert 'pixels' in info, 'pixels not in info_dict'
        B, S, T = action_sequence.shape[:3]

        # The observation is identical across the S candidates, so encode it
        # once and share it. The solver passes the same info_dict across its
        # iterations, so the cached 'emb' also saves re-encoding every step.
        if 'emb' not in info:
            first = {
                k: v[:, 0]
                for k, v in info.items()
                if torch.is_tensor(v) and k not in ('action', 'action_history')
            }
            # detach, as LeWM does: planning never trains the encoder, but a
            # gradient-based solver still needs gradients to reach the actions.
            ctx = self.encode(first)['emb'].detach()  # (B, H, D)
            info['emb'] = ctx.unsqueeze(1).expand(B, S, -1, -1)

        ctx = rearrange(info['emb'], 'b s h d -> (b s) h d')
        act_emb = self.action_encoder(
            rearrange(action_sequence, 'b s t a -> (b s) t a')
        )
        preds = self.unroll(ctx[:, -1], act_emb)
        emb = torch.cat([ctx, preds.to(ctx.dtype)], dim=1)
        info['predicted_emb'] = rearrange(
            emb, '(b s) ... -> b s ...', b=B, s=S
        )
        return info


__all__ = ['GRUWorldModel', 'GRUPredictor']
