"""Train the fine GRU world model on PushT.

    python scripts/train_gru.py
    python scripts/train_gru.py output_model_name=gru_fine_v2 train.precision=fp16

Config: scripts/train/config/gru.yaml. Model: stable_worldmodel/wm/gru/.

What it optimises. Each sample is a clip of ``rollout_steps + 1`` consecutive
frames. Every frame is encoded; the dynamics then roll open-loop from the first
latent through the clip's actions, and the loss is the mean squared error
against the encoded later frames, plus SIGReg on all the latents to stop the
encoder collapsing them. This is LeWM's objective with the prediction made by
rolling forward rather than by attending over context, because planning rolls
40 steps forward and one-step teacher forcing never exposes compounding error.

What it writes, all under ``$STABLEWM_HOME/checkpoints/<output_model_name>/``:

- ``weights.pt`` and ``config.json``: the latest epoch. Pass
  ``policy=<output_model_name>`` to eval_wm.py to plan with it.
- ``epochs/epoch_NNN/``: a loadable snapshot per epoch, in its own folder
  because ``load_pretrained`` refuses a folder holding more than one ``.pt``.
- ``train_state.ckpt``: optimiser and scheduler state for resuming. Named
  ``.ckpt`` rather than ``.pt`` for the same reason.
- ``metrics.jsonl``: one line per epoch.

Rerunning the same command resumes from ``train_state.ckpt``, so a job killed
by a cluster time limit loses at most one epoch.
"""

import json
import math
import sys
import time
from pathlib import Path

import hydra
import numpy as np
import torch
from omegaconf import DictConfig, OmegaConf

# scripts/ is not a package on sys.path when this file runs as a script; the
# repo root is what makes ``scripts.inzva_split`` importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import stable_worldmodel as swm  # noqa: E402
from scripts.inzva_split import fingerprint, split_episodes  # noqa: E402
from stable_worldmodel.data import column_normalizer  # noqa: E402
from stable_worldmodel.wm.loss import SIGReg  # noqa: E402
from stable_worldmodel.wm.utils import save_pretrained  # noqa: E402

# INZVA_README.md section 6.2. A different fingerprint means a different
# validation set, and every loss curve after that is incomparable with ours.
EXPECTED_SPLIT_FINGERPRINT = '2d5f8c4f85e918f8'

PRECISIONS = {'bf16': torch.bfloat16, 'fp16': torch.float16, 'fp32': None}


def build_dataset(cfg: DictConfig):
    """Clips of consecutive frames, preprocessed exactly as evaluation does.

    Evaluation normalises pixels with ImageNet statistics and standardises
    actions with a z-score fit on the whole dataset (eval_wm.py). The same two
    transforms are applied here, and the action statistics were checked equal
    to evaluation's to every printed digit.
    """
    from stable_pretraining import data as dt

    dataset = swm.data.load_dataset(
        cfg.dataset_name,
        num_steps=cfg.rollout_steps + 1,
        frameskip=1,
        keys_to_load=['pixels', 'action'],
        keys_to_cache=['action'],
    )
    stats = dt.dataset_stats.ImageNet
    dataset.transform = dt.transforms.Compose(
        dt.transforms.ToImage(**stats, source='pixels', target='pixels'),
        dt.transforms.Resize(cfg.img_size, source='pixels', target='pixels'),
        column_normalizer(dataset, 'action', 'action'),
    )
    return dataset


def split_clips(dataset) -> tuple[np.ndarray, np.ndarray]:
    """Clip indices for the locked episode-level train/validation split.

    Splitting by clip, as LeWM's trainer does, would put overlapping clips of
    one episode on both sides of the boundary and let validation loss measure
    memorisation.
    """
    train_eps, val_eps = split_episodes(num_episodes=len(dataset.lengths))
    got = fingerprint(val_eps)
    if got != EXPECTED_SPLIT_FINGERPRINT:
        raise SystemExit(
            f'validation split fingerprint is {got}, expected '
            f'{EXPECTED_SPLIT_FINGERPRINT}. The dataset or the split rule '
            'differs from the one the team locked; see INZVA_README.md 6.2.'
        )
    clip_eps = np.fromiter(
        (ep for ep, _ in dataset.clip_indices),
        dtype=np.int64,
        count=len(dataset.clip_indices),
    )
    return (
        np.flatnonzero(np.isin(clip_eps, train_eps)),
        np.flatnonzero(np.isin(clip_eps, val_eps)),
    )


def lr_lambda(total_steps: int, warmup_fraction: float):
    """Linear warmup, then cosine decay to zero."""
    warmup = max(1, int(warmup_fraction * total_steps))

    def fn(step: int) -> float:
        if step < warmup:
            return (step + 1) / warmup
        progress = (step - warmup) / max(1, total_steps - warmup)
        return 0.5 * (1.0 + math.cos(math.pi * min(1.0, progress)))

    return fn


def compute_losses(model, sigreg, batch, cfg, device, amp_dtype):
    """One forward pass. Returns the loss and detached diagnostics."""
    pixels = batch['pixels'].to(device, non_blocking=True)
    action = torch.nan_to_num(batch['action'].to(device, non_blocking=True))

    with torch.autocast(
        device_type=device.type,
        dtype=amp_dtype or torch.float32,
        enabled=amp_dtype is not None,
    ):
        out = model.encode({'pixels': pixels, 'action': action})
        # The action leaving the last frame has no target inside the clip.
        preds = model.unroll(out['emb'][:, 0], out['act_emb'][:, :-1])

    # Losses in float32: SIGReg evaluates cosines and sines of projections,
    # which is where half precision tends to go wrong first.
    emb = out['emb'].float()
    preds = preds.float()
    target = emb[:, 1:]

    pred_loss = (preds - target).pow(2).mean()
    sigreg_loss = sigreg(emb.transpose(0, 1))
    loss = pred_loss + cfg.loss.sigreg.weight * sigreg_loss

    with torch.no_grad():
        metrics = {
            'loss': loss.item(),
            'pred_loss': pred_loss.item(),
            'sigreg_loss': sigreg_loss.item(),
            # What an untrained model scores: predict that nothing moves. The
            # model is only learning dynamics if pred_loss falls below this.
            'hold_still_loss': (emb[:, :1] - target).pow(2).mean().item(),
            # Error at the end of the rollout, where compounding shows first.
            'final_step_loss': (preds[:, -1] - target[:, -1])
            .pow(2)
            .mean()
            .item(),
        }
    return loss, metrics


def average(rows: list[dict]) -> dict:
    return {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}


@hydra.main(version_base=None, config_path='./train/config', config_name='gru')
def run(cfg: DictConfig):
    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    amp_dtype = PRECISIONS[cfg.train.precision]

    # -- data
    dataset = build_dataset(cfg)
    if dataset.get_dim('action') != cfg.model.action_encoder.input_dim:
        raise SystemExit(
            f'dataset actions have {dataset.get_dim("action")} dims but '
            f'the action encoder expects {cfg.model.action_encoder.input_dim}'
        )
    train_idx, val_idx = split_clips(dataset)
    print(
        f'clips: {len(train_idx)} train, {len(val_idx)} val '
        f'({cfg.rollout_steps + 1} frames each)',
        flush=True,
    )

    generator = torch.Generator().manual_seed(cfg.seed)
    train_set = torch.utils.data.Subset(dataset, train_idx.tolist())
    val_pick = np.sort(
        np.random.default_rng(cfg.seed).choice(
            val_idx,
            size=min(cfg.train.val_samples, len(val_idx)),
            replace=False,
        )
    )
    loader_kwargs = dict(
        batch_size=cfg.train.batch_size,
        num_workers=cfg.train.num_workers,
        pin_memory=device.type == 'cuda',
        persistent_workers=cfg.train.num_workers > 0,
    )
    train_loader = torch.utils.data.DataLoader(
        train_set,
        sampler=torch.utils.data.RandomSampler(
            train_set,
            num_samples=cfg.train.samples_per_epoch,
            generator=generator,
        ),
        drop_last=True,
        **loader_kwargs,
    )
    val_loader = torch.utils.data.DataLoader(
        torch.utils.data.Subset(dataset, val_pick.tolist()),
        shuffle=False,
        **loader_kwargs,
    )

    # -- model and optimiser
    model_cfg = OmegaConf.to_container(cfg.model, resolve=True)
    model = hydra.utils.instantiate(cfg.model).to(device)
    sigreg = SIGReg(**cfg.loss.sigreg.kwargs).to(device)
    optimizer = torch.optim.AdamW(
        [
            {
                'params': [
                    *model.encoder.parameters(),
                    *model.projector.parameters(),
                ],
                'lr': cfg.optim.encoder_lr,
            },
            {
                'params': [
                    *model.predictor.parameters(),
                    *model.action_encoder.parameters(),
                ],
                'lr': cfg.optim.dynamics_lr,
            },
        ],
        weight_decay=cfg.optim.weight_decay,
    )
    steps_per_epoch = len(train_loader)
    total_steps = steps_per_epoch * cfg.train.max_epochs
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer, lr_lambda(total_steps, cfg.optim.warmup_fraction)
    )
    scaler = torch.amp.GradScaler(
        device.type, enabled=cfg.train.precision == 'fp16'
    )

    run_name = cfg.output_model_name
    run_dir = swm.data.utils.get_cache_dir(sub_folder='checkpoints') / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    state_path = run_dir / 'train_state.ckpt'

    start_epoch, step = 0, 0
    if cfg.train.resume and state_path.exists():
        state = torch.load(state_path, map_location=device, weights_only=False)
        model.load_state_dict(state['model'])
        optimizer.load_state_dict(state['optimizer'])
        scheduler.load_state_dict(state['scheduler'])
        scaler.load_state_dict(state['scaler'])
        generator.set_state(state['generator'])
        start_epoch, step = state['epoch'], state['step']
        print(f'resumed {run_name} at epoch {start_epoch}', flush=True)

    params = sum(p.numel() for p in model.parameters())
    print(
        f'model: {params / 1e6:.1f}M params | device {device} | '
        f'precision {cfg.train.precision} | {steps_per_epoch} steps/epoch',
        flush=True,
    )

    # -- train
    for epoch in range(start_epoch, cfg.train.max_epochs):
        model.train()
        window, t0, seen = [], time.time(), 0
        for batch in train_loader:
            loss, metrics = compute_losses(
                model, sigreg, batch, cfg, device, amp_dtype
            )
            optimizer.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(
                model.parameters(), cfg.train.grad_clip
            )
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()

            step += 1
            seen += batch['pixels'].shape[0]
            window.append(metrics)
            if step % cfg.train.log_every == 0:
                row = average(window)
                elapsed = time.time() - t0
                print(
                    json.dumps(
                        {
                            'epoch': epoch + 1,
                            'step': step,
                            **{k: round(v, 5) for k, v in row.items()},
                            'lr_dynamics': scheduler.get_last_lr()[1],
                            'clips_per_s': round(seen / elapsed, 1),
                        }
                    ),
                    flush=True,
                )
                window = []

        # -- validate
        model.eval()
        with torch.no_grad():
            val = average(
                [
                    compute_losses(
                        model, sigreg, batch, cfg, device, amp_dtype
                    )[1]
                    for batch in val_loader
                ]
            )
        record = {
            'epoch': epoch + 1,
            'step': step,
            'minutes': round((time.time() - t0) / 60, 2),
            **{f'val_{k}': round(v, 5) for k, v in val.items()},
        }
        print(json.dumps(record), flush=True)

        # -- checkpoint: loadable latest, loadable snapshot, resumable state
        save_pretrained(model, run_name, config=model_cfg)
        save_pretrained(
            model, f'{run_name}/epochs/epoch_{epoch + 1:03d}', config=model_cfg
        )
        torch.save(
            {
                'model': model.state_dict(),
                'optimizer': optimizer.state_dict(),
                'scheduler': scheduler.state_dict(),
                'scaler': scaler.state_dict(),
                'generator': generator.get_state(),
                'epoch': epoch + 1,
                'step': step,
            },
            state_path,
        )
        with open(run_dir / 'metrics.jsonl', 'a') as f:
            f.write(json.dumps(record) + '\n')

    print(f'done: {run_dir}', flush=True)


if __name__ == '__main__':
    run()
