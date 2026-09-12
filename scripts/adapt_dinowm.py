"""Fetch the DINO-WM checkpoint and make it loadable.

`kotmul/dinowm_patch_prop_pusht` is the only published DINO-WM checkpoint that
fits this repo's layout, and it does not load as published: its `config.json`
carries a `pixel_token` key that this repo's `PreJEPA.__init__` does not accept,
because the checkpoint came from a fork. See INZVA_README.md section 11.

Section 11 spelled the fix out as shell to copy and paste, which meant every
machine repeated it by hand and could repeat it differently. This does the same
thing, idempotently, and then proves the result loads.

It does not touch the downloaded copy. The adapted checkpoint is a separate
directory, so the original stays byte-identical to what HuggingFace served.

Usage:
    python scripts/adapt_dinowm.py
"""

import json
import os
import shutil
import urllib.request
from pathlib import Path

REPO = 'kotmul/dinowm_patch_prop_pusht'
ADAPTED = 'dinowm_kotmul_adapted'
FILES = ('config.json', 'weights.pt')

# Not an argument of this repo's PreJEPA.__init__; see section 11.
DROP_KEYS = ('pixel_token',)


def main():
    home = os.environ.get('STABLEWM_HOME')
    if not home:
        raise SystemExit(
            'STABLEWM_HOME is not set; see INZVA_README.md section 3'
        )
    cache = Path(home) / 'checkpoints'
    src = cache / f'models--{REPO.replace("/", "--")}'
    dst = cache / ADAPTED

    src.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        target = src / name
        if target.exists() and target.stat().st_size > 0:
            print(f'have    {target}')
            continue
        url = f'https://huggingface.co/{REPO}/resolve/main/{name}'
        print(f'fetch   {url}')
        # Download beside the target and rename, so an interrupted run cannot
        # leave a truncated file that the next run mistakes for complete.
        tmp = target.with_suffix(target.suffix + '.part')
        urllib.request.urlretrieve(url, tmp)
        tmp.rename(target)
        print(f'wrote   {target} ({target.stat().st_size} bytes)')

    if dst.exists():
        config = json.loads((dst / 'config.json').read_text())
        stale = [k for k in DROP_KEYS if k in config]
        if not stale:
            print(f'have    {dst} (already adapted)')
        else:
            print(f'redo    {dst} still carries {stale}')
            shutil.rmtree(dst)
    if not dst.exists():
        shutil.copytree(src, dst)
        path = dst / 'config.json'
        config = json.loads(path.read_text())
        removed = {k: config.pop(k) for k in DROP_KEYS if k in config}
        path.write_text(json.dumps(config, indent=2) + '\n')
        print(f'wrote   {dst}, removed {removed or "nothing"}')

    # Prove it. A config that merely parses is not the same as a checkpoint
    # that instantiates and accepts its own weights.
    from stable_worldmodel.wm.utils import load_pretrained

    model = load_pretrained(ADAPTED)
    params = sum(p.numel() for p in model.parameters())
    print(f'loaded  {type(model).__name__}, {params / 1e6:.1f}M params')
    print(f'\nUse it as: policy={ADAPTED} objective=goal_mse_pixels_proprio')


if __name__ == '__main__':
    main()
