#!/usr/bin/env python3
"""
Synthetic credential-dataset generator (Section V-A)

It writes <OUT_DIR>/ground_truth_sequences.csv and, for every percentage
and experiment index, <OUT_DIR>/crs<percentage>_(<experiment>).csv.

"""

from __future__ import annotations

import csv
import hashlib
import random
import string
from pathlib import Path


# ==========================================================================
# CONFIGURATION -- edit these values, then run the file
# ==========================================================================

# Output directory for the ground-truth file and the generated datasets.
OUT_DIR = "GT_and_CSV_files"

# Base random seed. The same seed with the same settings below produces
# byte-identical files on any machine and Python build. Change it to obtain
# a different but equally valid dataset.
SEED = 1

# Number of ground-truth chains (maximum 26: one capital letter per chain).
# The i-th chain uses the i-th letter, e.g. A, B, C, ...
CHAINS = 10

# Length of the SHORTEST chain. Chain lengths increase by one per chain, so
# the lengths run MIN_LENGTH .. MIN_LENGTH + CHAINS - 1.
# With MIN_LENGTH = 2 and CHAINS = 10 -> lengths 2..11 (A1<A2 up to J1<..<J11).
MIN_LENGTH = 2

# Ground-truth chains mixed into each wallet:
#   1     -> single-chain wallets  
#   2, 3  -> mixed-chain wallets (several chains co-exist in one wallet)
CHAINS_PER_IDENTITY = 1

# Identities (wallets) generated per primary chain. The total number of
# wallets per file is CHAINS * IDENTITIES_PER_CHAIN.
# With CHAINS = 10 and IDENTITIES_PER_CHAIN = 100 -> 1000 wallets per file.
IDENTITIES_PER_CHAIN = 100

# Size of the miscellaneous ("noise") credential pool cr1..cr<NOISE_SIZE>.
# The reported experiments use 100; the trust-variant experiments use 20
# (Section V-C).
NOISE_SIZE = 100

# Number of miscellaneous credentials added to each wallet is chosen
# uniformly between these two bounds (inclusive). MISC_MAX must not exceed
# NOISE_SIZE.
MISC_MIN = 2
MISC_MAX = 11

# Ground-truth percentages to generate: the percentage of a chain's elements
# that appear in each wallet drawn from it. One set of files per value.
PERCENTAGES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

# Number of experiment (replicate) files per percentage, named _(0).._(N-1).
EXPERIMENTS = 5

# ==========================================================================
# END OF CONFIGURATION -- no need to edit below this line
# ==========================================================================


def stable_seed(base_seed: int, experiment: int, percentage: int) -> int:
    """Deterministic per-file seed, independent of the built-in hash().

    A short key string is hashed with BLAKE2b and reduced to a 64-bit
    integer, so the seed depends only on the arguments and never on
    PYTHONHASHSEED or the interpreter build.
    """
    key = f"{base_seed}-{experiment}-{percentage}".encode()
    digest = hashlib.blake2b(key, digest_size=8).digest()
    return int.from_bytes(digest, "big")


def ground_truth_chains(n_chains: int, min_length: int) -> list[list[str]]:
    """Chains A1<A2, B1<B2<B3, ... of increasing length."""
    return [[f"{string.ascii_uppercase[i]}{j}"
             for j in range(1, min_length + i + 1)]
            for i in range(n_chains)]


def in_order_subset(chain: list[str], keep_prob: float,
                    rng: random.Random) -> list[str]:
    """Keep each element with probability keep_prob; order preserved."""
    return [c for c in chain if rng.random() < keep_prob]


def misc_credentials(rng: random.Random, lo: int, hi: int,
                     pool: int) -> list[str]:
    """A random subset of distinct miscellaneous credentials cr1..crpool."""
    k = rng.randint(lo, hi)
    return [f"cr{n}" for n in rng.sample(range(1, pool + 1), k)]


def interleave(sequences: list[list[str]], rng: random.Random) -> list[str]:
    """Merge sequences, preserving each sequence's internal order."""
    pools = [list(s) for s in sequences if s]
    out: list[str] = []
    while pools:
        pool = rng.choice(pools)
        out.append(pool.pop(0))
        if not pool:
            pools.remove(pool)
    return out


def build_dataset(gt_chains: list[list[str]], percentage: int,
                  rng: random.Random) -> list[list[str]]:
    """One dataset: IDENTITIES_PER_CHAIN identities per primary chain."""
    keep_prob = percentage / 100
    rows: list[list[str]] = []
    for primary_idx, primary in enumerate(gt_chains):
        others = [c for i, c in enumerate(gt_chains) if i != primary_idx]
        extra = min(CHAINS_PER_IDENTITY - 1, len(others))
        for _ in range(IDENTITIES_PER_CHAIN):
            selected = [primary]
            if extra > 0:
                selected += rng.sample(others, extra)
            parts = [in_order_subset(chain, keep_prob, rng)
                     for chain in selected]
            parts.append(misc_credentials(rng, MISC_MIN, MISC_MAX, NOISE_SIZE))
            row = interleave(parts, rng)
            if row:
                rows.append(row)
    return rows


def validate() -> None:
    """Stop with a clear message if the configuration is inconsistent."""
    if not 1 <= CHAINS <= len(string.ascii_uppercase):
        raise SystemExit("CHAINS must be between 1 and 26")
    if not 1 <= CHAINS_PER_IDENTITY <= CHAINS:
        raise SystemExit("CHAINS_PER_IDENTITY must be between 1 and CHAINS")
    if MISC_MIN < 0 or MISC_MAX < MISC_MIN:
        raise SystemExit("require 0 <= MISC_MIN <= MISC_MAX")
    if MISC_MAX > NOISE_SIZE:
        raise SystemExit("MISC_MAX cannot exceed NOISE_SIZE")
    if any(p < 1 or p > 100 for p in PERCENTAGES):
        raise SystemExit("every value in PERCENTAGES must lie in 1..100")
    if EXPERIMENTS < 1:
        raise SystemExit("EXPERIMENTS must be at least 1")


def main() -> None:
    validate()

    out_dir = Path(OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    gt_chains = ground_truth_chains(CHAINS, MIN_LENGTH)

    with (out_dir / "ground_truth_sequences.csv").open("w", newline="") as fh:
        csv.writer(fh).writerows(gt_chains)

    total = 0
    for exp in range(EXPERIMENTS):
        for pct in PERCENTAGES:
            rng = random.Random(stable_seed(SEED, exp, pct))
            rows = build_dataset(gt_chains, pct, rng)
            with (out_dir / f"crs{pct}_({exp}).csv").open("w", newline="") as fh:
                csv.writer(fh).writerows(rows)
            total += 1

    gt_creds = sum(len(c) for c in gt_chains)
    print(f"ground truth : {CHAINS} chains, {gt_creds} credentials, "
          f"lengths {MIN_LENGTH}..{MIN_LENGTH + CHAINS - 1}")
    print(f"wallets      : {CHAINS * IDENTITIES_PER_CHAIN} per file, "
          f"{CHAINS_PER_IDENTITY} ground-truth chain(s) each, "
          f"noise pool {NOISE_SIZE}")
    print(f"written      : {total} dataset files + ground truth "
          f"-> {out_dir}  (seed {SEED})")


if __name__ == "__main__":
    main()
