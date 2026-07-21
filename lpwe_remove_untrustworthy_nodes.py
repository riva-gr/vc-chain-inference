#!/usr/bin/env python3
"""
LPwE trust-aware variant: NODE-LEVEL filtering (Sec. IV-C).
Requires lpwe.py in the same directory.
"""

from __future__ import annotations

import argparse
import random
import time
from pathlib import Path

import numpy as np

from lpwe import (corresponding_gt, final_scores, jaccard_adjacency,
                  load_rows, membership_matrix, propagate)

NODE_TRUST_THRESHOLD = 0.5
NOISE_TRUST_HIGH = 0.49          
TRUST_SEED = 4
VARIANT_DIR = "LPwE_remove_untrustworthy_nodes"


def assign_trust(labels: list[str], gt_labels: set[str],
                 noise_high: float = NOISE_TRUST_HIGH,
                 seed: int = TRUST_SEED) -> dict[str, float]:
    """Seed-4 trust values over the sorted label list (parity)."""
    random.seed(seed)
    return {l: round(random.uniform(0.50, 1.0), 2) if l in gt_labels
            else round(random.uniform(0.0, noise_high), 2) for l in labels}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("percentage", nargs="?", type=int, default=40)
    ap.add_argument("score_threshold", nargs="?", type=float, default=0.7)
    ap.add_argument("experiment", nargs="?", type=int, default=0)
    ap.add_argument("similarity_threshold", nargs="?", type=float, default=0.3)
    ap.add_argument("--data-dir", type=Path, default=Path("GT_and_CSV_files"))
    ap.add_argument("--results-dir", type=Path,
                    default=Path("Results_modified/LPwE"))
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
    labels = sorted({lbl for row in rows for lbl in row})
    label_arr = np.array(labels)
    gt_labels = {lbl for seq in gt_sequences for lbl in seq}

    trust = assign_trust(labels, gt_labels)

    # Node-level filtering: average label trust per record.
    node_trust = np.array([sum(trust[l] for l in row) / len(row) if row else 0
                           for row in rows])
    trusted = node_trust >= NODE_TRUST_THRESHOLD

    # Similarity on FULL label sets (parity); edges only among trusted nodes.
    B_all = membership_matrix(rows, labels)
    A_all = jaccard_adjacency(B_all, args.similarity_threshold)
    A_all &= trusted[:, None] & trusted[None, :]

    keep = A_all.any(axis=1)                 # isolated (and untrusted) removed
    A = A_all[np.ix_(keep, keep)]
    B0 = B_all[keep]
    degrees = A.sum(axis=1)

    counts, n_rounds = propagate(A, B0)
    scores = final_scores(counts, B0, degrees, n_rounds)

    duration = time.time() - start

    added = scores > args.score_threshold     

    sum_gt = sum_inter = TP = FP = 0
    for v in range(B0.shape[0]):
        initial = set(label_arr[B0[v]])
        added_v = set(label_arr[added[v]])
        final = initial | added_v
        gt_list = corresponding_gt(initial, gt_sequences)
        gt_set = set(gt_list)
        sum_gt += len(gt_list)
        sum_inter += len(final & gt_set)
        TP += len(added_v & gt_set)
        FP += len(added_v - gt_set)
    FN = sum_gt - sum_inter

    coverage = sum_inter / sum_gt if sum_gt else 0
    accuracy = TP / (TP + FP + FN) if (TP + FP + FN) else 0
    precision = TP / (TP + FP) if (TP + FP) else 0
    recall = TP / (TP + FN) if (TP + FN) else 0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0)

    if args.verbose:
        print(f"nodes kept: {B0.shape[0]}/{len(rows)} "
              f"(trusted: {int(trusted.sum())})  rounds (n): {n_rounds}")
    print(f"time {duration:.3f}s  cov {coverage:.4f}  acc {accuracy:.4f}  "
          f"prec {precision:.4f}  rec {recall:.4f}  f1 {f1:.4f}")

    if args.write:
        out_dir = (args.results_dir / VARIANT_DIR
                   / f"similarity_{args.similarity_threshold}")
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"LPWE_score_threshold_{args.score_threshold:.2f}.txt"
        with out.open("a") as fh:
            fh.write(f"\n{args.percentage}  {duration:.3f} {coverage:.4f} "
                     f"{accuracy:.4f} {precision:.4f}  {recall:.4f}  {f1:.4f}  ")
            if args.percentage == 100:
                fh.write("\n")


if __name__ == "__main__":
    main()
