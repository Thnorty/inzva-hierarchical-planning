"""Contract tests for the fine GRU world model.

These are the first two checks INZVA_README.md section 10 asks of any model
before it is trained: it satisfies the ``Dynamics`` protocol with the documented
shapes, and a checkpoint round-trips through ``save_pretrained`` and
``load_pretrained``. They also pin down two properties the rest of the project
leans on: planning and training roll the dynamics out through the same code,
and gradients reach the action candidates, so gradient-based solvers still work.

Everything runs on CPU at toy sizes.
"""

import pytest
import torch
from torch import nn

from stable_worldmodel.planning import GoalMSE, ShootingCostEvaluator
from stable_worldmodel.protocols import Dynamics
from stable_worldmodel.wm.gru import GRUPredictor, GRUWorldModel
from stable_worldmodel.wm.lewm.module import Embedder
from stable_worldmodel.wm.utils import load_pretrained, save_pretrained

B, S, T, D, A = 2, 3, 5, 16, 2
IMG = 28


class TinyEncoder(nn.Module):
    """Stands in for the ViT: images to ``(N, D)``, accepting its kwargs."""

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


def _model(perturb: bool = False) -> GRUWorldModel:
    torch.manual_seed(0)
    model = GRUWorldModel(
        encoder=TinyEncoder(),
        predictor=GRUPredictor(latent_dim=D, action_dim=D),
        action_encoder=Embedder(input_dim=A, emb_dim=D),
    )
    if perturb:
        # The output layer starts at zero, which makes every rollout the
        # identity. Tests that compare two rollout paths need real dynamics,
        # or they would pass trivially.
        nn.init.normal_(model.predictor.out_proj.weight, std=0.5)
    return model.eval()


def _plan_info(h: int = 1) -> dict:
    """An info_dict shaped the way CEM hands one to get_cost."""
    return {
        'pixels': torch.randn(B, S, h, 3, IMG, IMG),
        'goal': torch.randn(B, S, 1, 3, IMG, IMG),
        'action': torch.randn(B, S, h, A),
    }


def test_satisfies_dynamics_protocol():
    assert isinstance(_model(), Dynamics)


def test_encode_shapes_and_optional_action():
    model = _model()
    info = model.encode({'pixels': torch.randn(B, T, 3, IMG, IMG)})
    assert info['emb'].shape == (B, T, D)
    assert 'act_emb' not in info, 'goal encoding passes no action'

    info = model.encode(
        {
            'pixels': torch.randn(B, T, 3, IMG, IMG),
            'action': torch.randn(B, T, A),
        }
    )
    assert info['act_emb'].shape == (B, T, D)


def test_untrained_dynamics_are_the_identity():
    """Zero-initialised output: the starting model predicts that nothing moves."""
    model = _model()
    z = torch.randn(B, D)
    preds = model.unroll(z, torch.randn(B, T, D))
    assert preds.shape == (B, T, D)
    assert torch.allclose(preds, z.unsqueeze(1).expand(B, T, D))


@pytest.mark.parametrize('h', [1, 3])
def test_rollout_shape_and_context_prefix(h):
    model = _model(perturb=True)
    info = model.rollout(_plan_info(h), torch.randn(B, S, T, A))
    pred = info['predicted_emb']
    assert pred.shape == (B, S, h + T, D)

    # The first H entries are the encoded context: the same observation for
    # every candidate, so they must agree across the sample axis.
    assert torch.allclose(pred[:, :, :h], pred[:, :1, :h].expand(B, S, h, D))


def test_rollout_matches_training_unroll():
    """Planning and training must advance the latent identically."""
    model = _model(perturb=True)
    info = _plan_info(1)
    actions = torch.randn(B, S, T, A)
    pixels = info['pixels'][:, 0]
    pred = model.rollout(info, actions)['predicted_emb']

    z0 = model.encode({'pixels': pixels})['emb'][:, -1]
    for s in range(S):
        expected = model.unroll(z0, model.action_encoder(actions[:, s]))
        # Relative tolerance on purpose. Planning runs every candidate as one
        # batch and this loop runs them one at a time, so float32 rounding
        # differs by ~1e-5 relative once the test's large weights compound it
        # over T steps. Measured in float64 the two paths agree to ~1e-15; a
        # real divergence would be of order one.
        assert torch.allclose(pred[:, s, 1:], expected, rtol=1e-4, atol=1e-5)


def test_plans_through_shooting_cost_evaluator():
    model = _model(perturb=True)
    cost = ShootingCostEvaluator(model, GoalMSE()).get_cost(
        _plan_info(1), torch.randn(B, S, T, A)
    )
    assert cost.shape == (B, S)
    assert torch.isfinite(cost).all()


def test_gradients_reach_action_candidates():
    """Gradient-based solvers differentiate the cost with respect to actions."""
    model = _model(perturb=True)
    actions = torch.randn(B, S, T, A, requires_grad=True)
    cost = ShootingCostEvaluator(model, GoalMSE()).get_cost(
        _plan_info(1), actions
    )
    cost.sum().backward()
    assert actions.grad is not None
    assert actions.grad.abs().sum() > 0


def test_checkpoint_round_trips_through_load_pretrained(tmp_path):
    """The real config: ViT encoder, BatchNorm projector, loaded by Hydra."""
    pytest.importorskip('stable_pretraining')
    config = {
        '_target_': 'stable_worldmodel.wm.gru.GRUWorldModel',
        'encoder': {
            '_target_': 'stable_pretraining.backbone.utils.vit_hf',
            'size': 'tiny',
            'patch_size': 14,
            'image_size': IMG,
            'pretrained': False,
            'use_mask_token': False,
        },
        'projector': {
            '_target_': 'stable_worldmodel.wm.lewm.module.MLP',
            'input_dim': 192,
            'output_dim': 192,
            'hidden_dim': 64,
            'norm_fn': {'_target_': 'torch.nn.BatchNorm1d', '_partial_': True},
        },
        'action_encoder': {
            '_target_': 'stable_worldmodel.wm.lewm.module.Embedder',
            'input_dim': A,
            'emb_dim': 32,
        },
        'predictor': {
            '_target_': 'stable_worldmodel.wm.gru.GRUPredictor',
            'latent_dim': 192,
            'action_dim': 32,
        },
    }
    from hydra.utils import instantiate

    torch.manual_seed(0)
    model = instantiate(config)
    nn.init.normal_(model.predictor.out_proj.weight, std=0.1)
    model.eval()

    save_pretrained(model, 'gru_rt', config=config, cache_dir=str(tmp_path))
    loaded = load_pretrained('gru_rt', cache_dir=str(tmp_path)).eval()

    original = model.state_dict()
    restored = loaded.state_dict()
    assert original.keys() == restored.keys()
    for key in original:
        assert torch.equal(original[key], restored[key]), key

    torch.manual_seed(1)
    info = _plan_info(1)
    actions = torch.randn(B, S, T, A)
    a = model.rollout({k: v.clone() for k, v in info.items()}, actions)
    b = loaded.rollout({k: v.clone() for k, v in info.items()}, actions)
    assert torch.allclose(a['predicted_emb'], b['predicted_emb'])
