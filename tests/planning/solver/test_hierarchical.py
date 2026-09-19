"""Tests for the coarse-to-fine solver.

Two of these matter more than the rest.

``test_refinement_never_worsens_its_own_cost`` is the property Experiment C
rests on: a gap search starts from the coarse plan's own actions and keeps the
incumbent in its population, so it cannot return something worse under its own
cost. At ``k = 1`` the coarse model is the fine model, the coarse plan already
hits its own waypoints exactly, and the solver should therefore reproduce plain
CEM.

``test_plan_shape_matches_flat_cem`` is what lets ``WorldModelPolicy`` drive
this solver without knowing it is hierarchical.
"""

import gymnasium as gym
import pytest
import torch
from torch import nn

from stable_worldmodel.planning import GoalMSE, ShootingCostEvaluator
from stable_worldmodel.planning.solver import HierarchicalSolver, Solver
from stable_worldmodel.policy import PlanConfig
from stable_worldmodel.wm.gru import GRUPredictor, GRUWorldModel
from stable_worldmodel.wm.lewm.module import Embedder

B, D, A, IMG = 2, 8, 2, 28
K = 2
HORIZON = 4  # environment steps, so 2 waypoints at k = 2


class TinyEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 8, 5, stride=4),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(8, D),
        )

    def forward(self, x, **kwargs):
        return self.net(x)


def _model(stride: int, seed: int = 0) -> GRUWorldModel:
    torch.manual_seed(seed)
    model = GRUWorldModel(
        encoder=TinyEncoder(),
        predictor=GRUPredictor(latent_dim=D, action_dim=D),
        action_encoder=Embedder(input_dim=stride * A, emb_dim=D),
        stride=stride,
    )
    # Untrained dynamics are the identity, which would make every plan equally
    # good and hide ordering bugs.
    nn.init.normal_(model.predictor.out_proj.weight, std=0.3)
    return model.eval()


def _solver(monkeypatch, coarse, fine, k=K, **kwargs) -> HierarchicalSolver:
    import stable_worldmodel.wm.utils as wm_utils

    monkeypatch.setattr(wm_utils, 'load_pretrained', lambda *a, **kw: coarse)
    solver = HierarchicalSolver(
        cost=ShootingCostEvaluator(fine, GoalMSE()),
        coarse_policy='irrelevant',
        k=k,
        num_samples=8,
        n_steps=2,
        topk=2,
        fine_num_samples=6,
        fine_n_steps=2,
        fine_topk=2,
        seed=0,
        **kwargs,
    )
    solver.configure(
        action_space=gym.spaces.Box(-1.0, 1.0, shape=(B, A)),
        n_envs=B,
        config=PlanConfig(
            horizon=HORIZON, receding_horizon=HORIZON, action_block=1
        ),
    )
    return solver


def _info() -> dict:
    return {
        'pixels': torch.randn(B, 1, 3, IMG, IMG),
        'goal': torch.randn(B, 1, 3, IMG, IMG),
        'action': torch.randn(B, 1, A),
    }


def test_satisfies_solver_protocol(monkeypatch):
    solver = _solver(monkeypatch, _model(K), _model(1, seed=1))
    assert isinstance(solver, Solver)
    assert solver.horizon == HORIZON
    assert solver.action_dim == A
    assert solver.n_waypoints == HORIZON // K


def test_plan_shape_matches_flat_cem(monkeypatch):
    """WorldModelPolicy reshapes the plan; it must not know which solver ran."""
    solver = _solver(monkeypatch, _model(K), _model(1, seed=1))
    out = solver.solve(_info())
    assert out['actions'].shape == (B, HORIZON, A)
    assert out['actions'].device.type == 'cpu'
    assert torch.isfinite(out['actions']).all()


def test_refinement_never_worsens_its_own_cost(monkeypatch):
    """The gap search keeps the coarse plan as a candidate, so it cannot lose.

    This is what Experiment C checks end to end: at k = 1 the coarse plan
    already reaches its own waypoints, so refinement has nothing to improve and
    the hierarchy collapses to plain CEM.
    """
    fine = _model(1, seed=1)
    solver = _solver(monkeypatch, _model(K), fine)

    torch.manual_seed(0)
    z = torch.randn(B, D)
    seed_actions = torch.randn(B, K, A)
    # A target the seed actions reach exactly: the k = 1 situation, where the
    # coarse and fine models agree by construction.
    target = solver._advance(z, seed_actions)

    refined = solver._refine(z, target, seed_actions)
    seed_cost = (solver._advance(z, seed_actions) - target).pow(2).sum(-1)
    refined_cost = (solver._advance(z, refined) - target).pow(2).sum(-1)
    assert torch.all(refined_cost <= seed_cost + 1e-6)


def test_waypoints_come_from_the_coarse_rollout(monkeypatch):
    coarse = _model(K)
    solver = _solver(monkeypatch, coarse, _model(1, seed=1))
    info = _info()
    coarse_actions = torch.randn(B, solver.n_waypoints, K * A)

    waypoints, z0 = solver._waypoints(info, coarse_actions)
    assert waypoints.shape == (B, solver.n_waypoints, D)
    assert z0.shape == (B, D)

    expected = coarse.rollout(
        {k: v.unsqueeze(1) for k, v in info.items()},
        coarse_actions.unsqueeze(1),
    )['predicted_emb'][:, 0]
    assert torch.allclose(waypoints, expected[:, -solver.n_waypoints :])
    assert torch.allclose(z0, expected[:, 0])


def test_rejects_configs_it_cannot_honour(monkeypatch):
    coarse, fine = _model(K), _model(1, seed=1)
    space = gym.spaces.Box(-1.0, 1.0, shape=(B, A))

    solver = _solver(monkeypatch, coarse, fine)
    with pytest.raises(ValueError, match='action_block'):
        solver.configure(
            action_space=space,
            n_envs=B,
            config=PlanConfig(horizon=4, receding_horizon=4, action_block=2),
        )
    with pytest.raises(ValueError, match='divisible'):
        solver.configure(
            action_space=space,
            n_envs=B,
            config=PlanConfig(horizon=5, receding_horizon=5, action_block=1),
        )


def test_rejects_a_coarse_model_of_the_wrong_stride(monkeypatch):
    """A coarse model only predicts correctly at the stride it was trained on."""
    with pytest.raises(ValueError, match='stride'):
        _solver(monkeypatch, _model(4), _model(1, seed=1), k=2)
