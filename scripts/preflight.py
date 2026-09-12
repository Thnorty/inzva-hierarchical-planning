"""Check a machine can run the experiments, without asking for a GPU.

Most ways a run dies are not GPU problems: a missing dataset, a checkpoint
that will not load, a headless node with no video driver, a config that no
longer composes. On TRUBA those failures are expensive to find the slow way,
because a GPU job can sit in the queue for half a day before it gets far
enough to tell you the dataset path was wrong.

Everything here runs on CPU, so it can be submitted to an idle node and
answer in a couple of minutes. It reports the GPU situation but never
requires one.

Usage:
    python scripts/preflight.py
"""

import os
import subprocess
import sys
import traceback

# From INZVA_README.md section 5.1. Anything else is a different dataset.
EXPECTED_EPISODES = 18685
EXPECTED_STEPS = 2336736

CHECKPOINTS = ('quentinll/lewm-pusht', 'dinowm_kotmul_adapted')
CONFIGS = ('inzva_pusht', 'inzva_gru')

results = []


def check(name):
    """Register a check; the decorated function returns a detail string."""

    def wrap(fn):
        print(f'--- {name}', flush=True)
        try:
            detail = fn()
            results.append((True, name, detail))
            print(f'    PASS  {detail}', flush=True)
        except Exception as exc:  # noqa: BLE001 - report every failure
            results.append((False, name, f'{type(exc).__name__}: {exc}'))
            print(f'    FAIL  {type(exc).__name__}: {exc}', flush=True)
            traceback.print_exc()
        return fn

    return wrap


def main():
    home = os.environ.get('STABLEWM_HOME')
    if not home:
        raise SystemExit(
            'STABLEWM_HOME is not set; see INZVA_README.md section 3'
        )

    @check('torch build')
    def _torch():
        import torch

        # Read the compile-time flags, not torch.cuda.get_arch_list(). The
        # latter returns [] whenever no GPU is visible, which looks identical
        # to a build with no kernels at all (README section 12.2).
        flags = torch._C._cuda_getArchFlags()

        if torch.cuda.is_available():
            major, minor = torch.cuda.get_device_capability(0)
            required = f'sm_{major}{minor}'
            device = torch.cuda.get_device_name(0)
        else:
            # No GPU here, so the target has to be stated rather than
            # detected. The TRUBA smoke job sets this because the check is
            # worth running on an idle CPU node hours before a GPU frees up.
            required = os.environ.get('PREFLIGHT_REQUIRE_ARCH')
            device = 'no GPU on this node'

        if required and required not in flags:
            raise RuntimeError(
                f'torch {torch.__version__} has arch flags "{flags}", with no '
                f'{required}. It has no kernels for the target GPU. '
                'See README section 12.2.'
            )
        target = required or 'unverified, no GPU and no PREFLIGHT_REQUIRE_ARCH'
        return f'{torch.__version__} [{flags}], {device}, target {target}'

    @check('torchvision build matches torch')
    def _tv():
        import torchvision
        from torchvision.ops import nms  # noqa: F401

        return torchvision.__version__

    @check('dataset')
    def _dataset():
        import stable_worldmodel as swm

        path = os.path.join(home, 'datasets', 'pusht_expert_train.h5')
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        ds = swm.data.load_dataset(path)
        episodes, steps = len(ds.lengths), int(ds.lengths.sum())
        if (episodes, steps) != (EXPECTED_EPISODES, EXPECTED_STEPS):
            raise RuntimeError(
                f'fingerprint mismatch: {episodes} episodes / {steps} steps, '
                f'expected {EXPECTED_EPISODES} / {EXPECTED_STEPS}'
            )
        return f'{episodes} episodes, {steps} steps, fingerprint matches'

    @check('headless rendering')
    def _render():
        # The failure this catches is a compute node with no display. Without
        # SDL_VIDEODRIVER=dummy this raises before returning a frame.
        import gymnasium as gym

        import stable_worldmodel  # noqa: F401

        env = gym.make('swm/PushT-v1', render_mode='rgb_array').unwrapped
        env.reset(seed=0)
        frame = env.render()
        if frame is None or frame.size == 0:
            raise RuntimeError('render() returned nothing')
        driver = os.environ.get('SDL_VIDEODRIVER', '(unset)')
        return f'{frame.shape} frame, SDL_VIDEODRIVER={driver}'

    for name in CHECKPOINTS:

        @check(f'checkpoint {name}')
        def _ckpt(name=name):
            from stable_worldmodel.wm.utils import load_pretrained

            model = load_pretrained(name)
            params = sum(p.numel() for p in model.parameters())
            return f'{type(model).__name__}, {params / 1e6:.1f}M params'

    for name in CONFIGS:

        @check(f'config {name}')
        def _config(name=name):
            out = subprocess.run(
                [
                    sys.executable,
                    'scripts/plan/eval_wm.py',
                    '--config-name',
                    name,
                    'policy=quentinll/lewm-pusht',
                    'seed=0',
                    '--cfg',
                    'job',
                ],
                capture_output=True,
                text=True,
                timeout=900,
            )
            if out.returncode != 0:
                raise RuntimeError(out.stderr.strip()[-400:])
            return 'composes'

    failed = [name for ok, name, _ in results if not ok]
    print()
    print(f'{len(results) - len(failed)}/{len(results)} checks passed')
    for ok, name, detail in results:
        print(f'  {"PASS" if ok else "FAIL"}  {name}: {detail}')
    if failed:
        raise SystemExit(1)
    print('PREFLIGHT OK')


if __name__ == '__main__':
    main()
