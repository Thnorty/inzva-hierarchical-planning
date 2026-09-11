"""Deterministic train/validation split for the PushT expert dataset.

The HuggingFace dataset repo ships exactly one file and no validation split, so
we define our own. The split is held **at episode granularity**: steps from one
episode never straddle the boundary, because consecutive steps of the same
episode are near-duplicates and a step-level split leaks the validation set into
training almost perfectly.

The split is a *rule*, not a stored list: given the same episode count, seed and
fraction, every machine derives the same held-out episodes. The JSON this writes
is for auditing and for catching drift, not the source of truth.

Import it from a training script:

    from scripts.inzva_split import split_episodes
    train_eps, val_eps = split_episodes(num_episodes=18685)

Or inspect and record it:

    python scripts/inzva_split.py --out splits/

Print the fingerprint alone, to compare two machines quickly:

    python scripts/inzva_split.py --fingerprint-only
"""

import argparse
import hashlib
import json
import os

import numpy as np

# Locked in the shared config. Changing either invalidates every loss curve
# and every checkpoint comparison made before the change, so do not change
# them without telling the whole team.
SPLIT_SEED = 20260910
VAL_FRACTION = 0.05

# Measured on quentinll/lewm-pusht; see INZVA_README.md section 5.1. Passing a
# different count is allowed but warned about, because it means the dataset is
# not the one the split was designed against.
EXPECTED_EPISODES = 18685


def split_episodes(
    num_episodes: int = EXPECTED_EPISODES,
    val_fraction: float = VAL_FRACTION,
    seed: int = SPLIT_SEED,
) -> tuple[np.ndarray, np.ndarray]:
    """Split episode indices into train and validation sets.

    Args:
        num_episodes: Total number of episodes in the dataset.
        val_fraction: Fraction of episodes held out for validation.
        seed: Seed for the permutation. Fixed across the whole team.

    Returns:
        ``(train_episodes, val_episodes)``, both sorted ascending. Sorting
        matters: the HDF5 reader is much slower on out-of-order indices.
    """
    if not 0.0 < val_fraction < 1.0:
        raise ValueError(f'val_fraction must be in (0, 1), got {val_fraction}')

    n_val = max(1, round(num_episodes * val_fraction))
    order = np.random.default_rng(seed).permutation(num_episodes)
    val = np.sort(order[:n_val])
    train = np.sort(order[n_val:])
    return train, val


def fingerprint(val_episodes: np.ndarray) -> str:
    """Short stable hash of the validation set, for cross-machine comparison.

    Args:
        val_episodes: The held-out episode indices.

    Returns:
        The first 16 hex characters of the SHA-256 of the sorted indices.
    """
    payload = ','.join(str(int(e)) for e in np.sort(val_episodes))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default=None, help='directory for split JSON')
    parser.add_argument(
        '--num-episodes',
        type=int,
        default=EXPECTED_EPISODES,
        help='episode count of the dataset being split',
    )
    parser.add_argument(
        '--val-fraction',
        type=float,
        default=VAL_FRACTION,
        help='held-out share',
    )
    parser.add_argument('--seed', type=int, default=SPLIT_SEED)
    parser.add_argument(
        '--fingerprint-only',
        action='store_true',
        help='print just the fingerprint and exit',
    )
    args = parser.parse_args()

    if args.num_episodes != EXPECTED_EPISODES:
        print(
            f'WARNING: splitting {args.num_episodes} episodes, but the shared '
            f'dataset has {EXPECTED_EPISODES}. This split will not match '
            "anyone else's."
        )

    train, val = split_episodes(
        args.num_episodes, args.val_fraction, args.seed
    )
    fp = fingerprint(val)

    if args.fingerprint_only:
        print(fp)
        return

    print(f'episodes    : {args.num_episodes}')
    print(f'seed        : {args.seed}')
    print(f'val fraction: {args.val_fraction}')
    print(f'train       : {len(train)} episodes')
    print(f'val         : {len(val)} episodes')
    print(f'val[:10]    : {val[:10].tolist()}')
    print(f'fingerprint : {fp}')
    print('\nCompare the fingerprint across machines before trusting any two')
    print('loss curves against each other.')

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, 'inzva_split.json')
        with open(path, 'w') as fh:
            json.dump(
                {
                    'seed': args.seed,
                    'val_fraction': args.val_fraction,
                    'num_episodes': args.num_episodes,
                    'num_train': len(train),
                    'num_val': len(val),
                    'fingerprint': fp,
                    'val_episodes': val.tolist(),
                },
                fh,
                indent=2,
            )
        print(f'\nwrote {path}')


if __name__ == '__main__':
    main()
