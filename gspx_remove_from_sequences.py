#!/usr/bin/env python3
"""
GSP-X trust-aware variant: CHAIN-LEVEL filtering (Sec. IV-A).
Requires gsp.py in the same directory (and the pymining package).
"""

from __future__ import annotations

import argparse
import random
import time
from pathlib import Path

from gsp import (build_chains, corresponding_gt, load_rows,
                 mine_frequent_sequences, remove_subchains)

LABEL_TRUST_THRESHOLD = 0.5
NOISE_TRUST_HIGH = 0.49
TRUST_SEED = 4
VARIANT_DIR = "GSP-X_remove_from_sequences"


def assign_trust(creds: list[str], gt_creds: set[str],
                 noise_high: float = NOISE_TRUST_HIGH,
                 seed: int = TRUST_SEED) -> dict[str, float]:
    """Seed-4 trust values over the sorted credential list (parity)."""
    random.seed(seed)
    return {c: round(random.uniform(0.50, 1.0), 2) if c in gt_creds
            else round(random.uniform(0.0, noise_high), 2) for c in creds}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("min_support", nargs="?", type=float, default=0.03)
    ap.add_argument("risup", nargs="?", type=float, default=0.5)
    ap.add_argument("experiment", nargs="?", type=int, default=0)
    ap.add_argument("percentage", nargs="?", type=int, default=100)
    ap.add_argument("--data-dir", type=Path, default=Path("GT_and_CSV_files"))
    ap.add_argument("--results-dir", type=Path,
                    default=Path("Results_modified/GSP-X"))
    ap.add_argument("--write", action="store_true",
                    help="also append the metrics to the results file")
    ap.add_argument("--verbose", action="store_true",
                    help="also print the discovered chains/diagnostics")
    args = ap.parse_args()

    csv_path = args.data_dir / f"crs{args.percentage}_({args.experiment}).csv"
    gt_path = args.data_dir / "ground_truth_sequences.csv"

    start = time.time()

    rows = load_rows(csv_path)
    gt_sequences = load_rows(gt_path)
    creds = sorted({c for row in rows for c in row})
    gt_creds = {c for seq in gt_sequences for c in seq}

    trust = assign_trust(creds, gt_creds)

    # Full-dataset mining (chain-level: trust intervenes only afterwards).
    frequent = mine_frequent_sequences(rows, args.min_support * len(rows))

    # Strip untrustworthy credentials from each frequent sequence
    # (no length re-check -- parity).
    frequent = [[c for c in seq if trust[c] >= LABEL_TRUST_THRESHOLD]
                for seq in frequent]

    chains = remove_subchains(build_chains(frequent, rows, args.risup))

    duration = time.time() - start

    if args.verbose:
        print(f"records: {len(rows)}  frequent (after stripping): "
              f"{len(frequent)}  chains: {len(chains)}")
        for chain in chains:
            print(chain)

    sum_acc = sum_prec = sum_rec = 0.0
    sum_inter = sum_corr = 0
    for chain in chains:
        corr = corresponding_gt(chain, gt_sequences)
        chain_set, gt_set = set(chain), set(corr)
        tp = len(chain_set & gt_set)
        sum_inter += tp
        sum_corr += len(corr)
        sum_acc += tp / len(chain_set | gt_set) if (chain_set | gt_set) else 0
        sum_prec += tp / len(chain_set) if chain_set else 0
        sum_rec += tp / len(gt_set) if gt_set else 0

    n_chains = len(chains)
    coverage = sum_inter / sum_corr if sum_corr else 0
    accuracy = sum_acc / n_chains if n_chains else 0
    precision = sum_prec / n_chains if n_chains else 0
    recall = sum_rec / n_chains if n_chains else 0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0)

    print(f"time {duration:.3f}s  cov {coverage:.4f}  acc {accuracy:.4f}  "
          f"prec {precision:.4f}  rec {recall:.4f}  f1 {f1:.4f}")

    if args.write:
        out_dir = (args.results_dir / VARIANT_DIR
                   / f"min_support_{args.min_support}")
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"gspx_risup_{args.risup:.2f}.txt"
        with out.open("a") as fh:
            fh.write(f"\n{args.percentage}  {duration:.3f}  {coverage:.4f} "
                     f"{accuracy:.4f} {precision:.4f}  {recall:.4f}  {f1:.4f}  ")
            if args.percentage == 100:
                fh.write("\n")


if __name__ == "__main__":
    main()
