"""Coarse-to-fine planning: the contribution of the inzva project.

Plain CEM searches every action of the horizon at once. With a 10-step horizon
and 2-dimensional actions that is a 20-dimensional search, and the cost of
covering it grows with the horizon. This solver splits it in two:

1. **Coarse.** Run CEM on a coarse world model whose every step spans ``k``
   environment steps. A 10-step horizon becomes 5 decisions instead of 10, so
   the search is half the width. Roll the chosen plan forward and keep the
   latents it passes through: those are the waypoints.
2. **Fine.** For each gap between consecutive waypoints, search the ``k``
   environment actions that get there, using the fine model and scoring against
   the waypoint rather than the episode goal. Each gap is its own small search,
   seeded with the coarse plan's own actions for that gap.

The two stages share one latent space, which is the whole reason the shared
frozen encoder was locked in INZVA_README.md section 6.5: a waypoint produced by
the coarse model is directly a target the fine model can be scored against, with
no translation between representations.

**Why seeding the fine stage from the coarse plan matters.** The coarse actions
are already a complete, executable plan; refinement starts there and can only
improve on it under its own cost. That is also what makes Experiment C
meaningful: at ``k = 1`` the coarse model *is* the fine model, the coarse plan
already hits its own waypoints exactly, and the refinement has nothing to fix,
so the solver should reproduce plain CEM. If it does not, the bug is here.

Costs. Stage 1 uses the harness's own cost object, so the coarse search is
scored exactly like the flat baseline. Stage 2 scores squared error to the
waypoint latent, summed over the latent dimension, matching ``GoalMSE``'s
default reduction so the two stages agree on what "close" means.
"""

import logging
import time
from dataclasses import replace
from typing import Any

import gymnasium as gym
import numpy as np
import torch

from stable_worldmodel.planning.evaluator import ShootingCostEvaluator

from .cem import CEMSolver
from .solver import Costable

logger = logging.getLogger(__name__)


class HierarchicalSolver:
    """Plan coarse waypoints, then fill the gaps with fine actions.

    The harness builds ``cost`` around the **fine** model, because the actions
    this solver returns are fine-grained and that is the model they will be
    executed against. The coarse model is named here and loaded on construction.

    Args:
        cost: Cost object built on the fine model (a ``ShootingCostEvaluator``).
        coarse_policy: Checkpoint name of the coarse model, resolved with
            ``load_pretrained``. Its stride must equal ``k``.
        k: Environment steps spanned by one coarse step.
        num_samples: CEM population for the coarse stage.
        var_scale: Initial CEM standard deviation for the coarse stage.
        n_steps: CEM iterations for the coarse stage.
        topk: Elites kept per CEM iteration in the coarse stage.
        fine_num_samples: Population for each gap search. Defaults to
            ``num_samples``, but each gap is a far smaller problem.
        fine_n_steps: Iterations per gap search. Defaults to ``n_steps``.
        fine_topk: Elites per gap search. Defaults to ``topk``.
        fine_var_scale: Initial standard deviation for a gap search, as a
            fraction of ``var_scale``. Smaller than 1 by default because the
            search starts from the coarse plan rather than from nothing.
        batch_size: Environments per batch in the coarse stage.
        device: Device for planning.
        seed: Seed for both stages' sampling.
        callbacks: Forwarded to the coarse CEM stage.
    """

    def __init__(
        self,
        cost: Costable,
        coarse_policy: str,
        k: int = 2,
        num_samples: int = 300,
        var_scale: float = 1.0,
        n_steps: int = 30,
        topk: int = 30,
        fine_num_samples: int | None = None,
        fine_n_steps: int | None = None,
        fine_topk: int | None = None,
        fine_var_scale: float = 0.5,
        batch_size: int = 1,
        device: str | torch.device = 'cpu',
        seed: int = 1234,
        callbacks: list | None = None,
    ) -> None:
        from stable_worldmodel.wm.utils import load_pretrained

        self.cost = cost
        self.k = int(k)
        self.device = device
        self.fine_num_samples = fine_num_samples or num_samples
        self.fine_n_steps = fine_n_steps or n_steps
        self.fine_topk = fine_topk or topk
        self.fine_var_scale = fine_var_scale * var_scale
        self.torch_gen = torch.Generator(device=device).manual_seed(seed + 1)

        coarse_model = load_pretrained(coarse_policy)
        coarse_model = coarse_model.to(device).eval().requires_grad_(False)
        stride = getattr(coarse_model, 'stride', None)
        if stride is not None and stride != self.k:
            raise ValueError(
                f'{coarse_policy} was trained with stride {stride} but the '
                f'solver is configured for k={self.k}. A coarse model only '
                'predicts correctly at the stride it was trained on.'
            )
        self.coarse_model = coarse_model

        # Same objective as the fine stage, so both stages agree on the goal.
        self.coarse_cost = ShootingCostEvaluator(
            coarse_model, getattr(cost, 'objective', None)
        )
        self.coarse_solver = CEMSolver(
            cost=self.coarse_cost,
            batch_size=batch_size,
            num_samples=num_samples,
            var_scale=var_scale,
            n_steps=n_steps,
            topk=topk,
            device=device,
            seed=seed,
            callbacks=callbacks,
        )

    def configure(
        self, *, action_space: gym.Space, n_envs: int, config: Any
    ) -> None:
        """Configure both stages from the outer planning config.

        The outer config describes the actions this solver returns, so it is
        the fine one: ``action_block: 1`` and a horizon counted in environment
        steps. The coarse stage is configured from a copy of it with the
        horizon divided by ``k`` and the block set to ``k``.
        """
        if config.action_block != 1:
            raise ValueError(
                'HierarchicalSolver returns fine-grained actions, so the outer '
                f'config needs action_block: 1, got {config.action_block}'
            )
        if config.horizon % self.k:
            raise ValueError(
                f'horizon {config.horizon} is not divisible by k={self.k}'
            )

        self._action_space = action_space
        self._n_envs = n_envs
        self._config = config
        self._env_action_dim = int(np.prod(action_space.shape[1:]))
        self.n_waypoints = config.horizon // self.k

        self.coarse_solver.configure(
            action_space=action_space,
            n_envs=n_envs,
            config=replace(
                config, horizon=self.n_waypoints, action_block=self.k
            ),
        )

    @property
    def n_envs(self) -> int:
        return self._n_envs

    @property
    def action_dim(self) -> int:
        """Flattened action dimension of the returned plan."""
        return self._env_action_dim * self._config.action_block

    @property
    def horizon(self) -> int:
        return self._config.horizon

    def __call__(self, *args: Any, **kwargs: Any) -> dict:
        return self.solve(*args, **kwargs)

    @torch.inference_mode()
    def solve(
        self, info_dict: dict, init_action: torch.Tensor | None = None
    ) -> dict:
        """Plan coarse, then refine each gap.

        Returns the same shape plain CEM does, ``(n_envs, horizon,
        action_dim)``, so ``WorldModelPolicy`` cannot tell the two apart.
        """
        start_time = time.time()
        k, W = self.k, self.n_waypoints

        coarse_out = self.coarse_solver.solve(
            info_dict, init_action=self._to_coarse(init_action)
        )
        coarse_actions = coarse_out['actions'].to(self.device)  # (B, W, k*A)

        waypoints, z = self._waypoints(info_dict, coarse_actions)

        segments = []
        for w in range(W):
            seed_actions = coarse_actions[:, w].reshape(
                -1, k, self._env_action_dim
            )
            seg = self._refine(z, waypoints[:, w], seed_actions)
            segments.append(seg)
            # Advance along what the fine model says those actions actually do,
            # not along the waypoint. The waypoint is a target, and the gap
            # search may not have reached it; planning the next gap from the
            # wish rather than the outcome would compound the error silently.
            z = self._advance(z, seg)

        actions = torch.cat(segments, dim=1)  # (B, horizon, A)
        outputs = {
            'actions': actions.detach().cpu(),
            'costs': coarse_out['costs'],
            'mean': [actions.detach().cpu()],
            'var': coarse_out.get('var', []),
        }
        if 'callbacks' in coarse_out:
            outputs['callbacks'] = coarse_out['callbacks']
        print(
            f'Hierarchical solve time: {time.time() - start_time:.4f} seconds'
        )
        return outputs

    # -- internals

    def _to_coarse(self, init_action: torch.Tensor | None):
        """Regroup a warm-start plan from fine steps into coarse ones."""
        if init_action is None:
            return None
        b, t, a = init_action.shape
        if t % self.k:
            return None  # partial block: not worth guessing, start fresh
        return init_action.reshape(b, t // self.k, self.k * a)

    def _waypoints(self, info_dict: dict, coarse_actions: torch.Tensor):
        """Roll the coarse plan forward; return its waypoints and the start.

        Returns ``(waypoints (B, W, D), z0 (B, D))``, where ``z0`` is the
        latent of the current observation.
        """
        single = {}
        for key, value in info_dict.items():
            if torch.is_tensor(value):
                value = value.to(self.device)
                if value.is_floating_point():
                    value = value.to(self.coarse_solver.dtype)
                single[key] = value.unsqueeze(1)  # one candidate
        rolled = self.coarse_model.rollout(single, coarse_actions.unsqueeze(1))
        emb = rolled['predicted_emb'][:, 0]  # (B, H + W, D)
        return emb[:, -self.n_waypoints :], emb[:, -self.n_waypoints - 1]

    def _fine_rollout(self, z: torch.Tensor, actions: torch.Tensor):
        """Roll the fine model from latent ``z``; return the reached latents.

        ``z`` is ``(B, D)`` or ``(B, S, D)``; ``actions`` is ``(B, S, T, A)``.
        Feeding ``emb`` directly skips re-encoding pixels, which is what makes
        a per-gap search cheap.
        """
        if z.dim() == 2:
            z = z.unsqueeze(1).expand(-1, actions.shape[1], -1)
        info = {'emb': z.unsqueeze(2)}  # (B, S, 1, D): one context frame
        rolled = self.cost.model.rollout(info, actions)
        return rolled['predicted_emb'][:, :, -1]  # (B, S, D)

    def _refine(
        self,
        z: torch.Tensor,
        target: torch.Tensor,
        seed_actions: torch.Tensor,
    ) -> torch.Tensor:
        """CEM over the ``k`` actions of one gap, seeded with the coarse plan."""
        b, t, a = seed_actions.shape
        n = self.fine_num_samples
        mean = seed_actions.to(self.device)
        var = torch.full_like(mean, self.fine_var_scale)
        rows = torch.arange(b, device=self.device)

        # Elitist, unlike the plain CEM of the coarse stage, which returns the
        # mean of its elites. That mean can be worse than the plan it started
        # from, and this search starts from the coarse plan: refinement that
        # can degrade a good coarse plan would make Experiment C fail for a
        # reason that has nothing to do with the hierarchy. Keeping the best
        # plan seen makes "refine" mean what it says.
        best = mean
        best_cost = self._gap_cost(z, target, mean.unsqueeze(1))[:, 0]

        for _ in range(self.fine_n_steps):
            noise = torch.randn(
                b,
                n,
                t,
                a,
                generator=self.torch_gen,
                device=self.device,
                dtype=mean.dtype,
            )
            candidates = mean.unsqueeze(1) + var.unsqueeze(1) * noise
            candidates[:, 0] = mean

            cost = self._gap_cost(z, target, candidates)  # (B, S)

            low_cost, low_idx = cost.min(dim=1)
            better = low_cost < best_cost
            best = torch.where(
                better[:, None, None], candidates[rows, low_idx], best
            )
            best_cost = torch.where(better, low_cost, best_cost)

            _, elite_idx = torch.topk(
                cost, k=min(self.fine_topk, n), dim=1, largest=False
            )
            elites = candidates[rows.unsqueeze(1), elite_idx]
            mean = elites.mean(dim=1)
            var = elites.std(dim=1, correction=0)

        return best

    def _gap_cost(
        self, z: torch.Tensor, target: torch.Tensor, candidates: torch.Tensor
    ) -> torch.Tensor:
        """Squared error from each candidate's end latent to the waypoint.

        Summed over the latent dimension, matching ``GoalMSE``'s default
        reduction, so both stages mean the same thing by "close".
        """
        reached = self._fine_rollout(z, candidates)  # (B, S, D)
        return (reached - target.unsqueeze(1)).pow(2).sum(dim=-1)

    def _advance(self, z: torch.Tensor, actions: torch.Tensor) -> torch.Tensor:
        """Latent reached by executing one gap's actions, ``(B, D)``."""
        return self._fine_rollout(z, actions.unsqueeze(1))[:, 0]


__all__ = ['HierarchicalSolver']
