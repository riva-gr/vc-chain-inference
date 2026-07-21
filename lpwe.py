#!/usr/bin/env python3
"""
LPwE — Label Propagation with Encirclement (Section III-C, Eqs. (2)-(4)).

"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np


# --------------------------------------------------------------- I/O ---

def load_rows(path: Path) -> list[list[str]]:
    """Read a CSV as a list of string rows; exit cleanly if missing."""
    try:
        with path.open(newline="") as fh:
            return [row for row in csv.reader(fh) if row]
    except FileNotFoundError:
        sys.exit(f"The file {path} does not exist!")


# ------------------------------------------------- graph construction ---

def membership_matrix(rows: list[list[str]], labels: list[str]) -> np.ndarray:
    """N x L boolean matrix: B[v, l] = True iff node v holds label l."""
    index = {lbl: j for j, lbl in enumerate(labels)}
    B = np.zeros((len(rows), len(labels)), dtype=bool)
    for v, row in enumerate(rows):
        for lbl in set(row):
            B[v, index[lbl]] = True
    return B


def jaccard_adjacency(B: np.ndarray, threshold: float) -> np.ndarray:
    """Symmetric boolean adjacency: edge iff round(Jaccard, 2) >= threshold."""
    Bi = B.astype(np.int32)
    inter = Bi @ Bi.T
    sizes = Bi.sum(axis=1)
    union = sizes[:, None] + sizes[None, :] - inter
    with np.errstate(divide="ignore", invalid="ignore"):
        sim = np.where(union > 0, inter / union, 0.0)
    sim = np.round(sim, 2)          # parity: original rounds before comparing
    A = sim >= threshold
    np.fill_diagonal(A, False)
    return A


# ----------------------------------------------------- LPwE algorithm ---

def propagate(A: np.ndarray, B0: np.ndarray) -> tuple[np.ndarray, int]:
    """Synchronous set-union label propagation.

    Returns (counts, n): counts[r, v, l] = number of neighbours of v
    holding label l at the start of round r+1 (Eq. (2)'s t_{r,l}),
    recorded for EVERY node in EVERY non-terminal round. Label sets grow
    monotonically, so the loop terminates within diam(G) rounds
    (Proposition III.1); the terminal no-update round is not recorded,
    matching the paper's definition of n.
    """
    Ai = A.astype(np.int32)
    B = B0.copy()
    per_round = []
    while True:
        C = Ai @ B                     
        newB = B | (C > 0)
        if np.array_equal(newB, B):     
            break
        per_round.append(C)
        B = newB
    n = len(per_round)
    counts = (np.stack(per_round) if n
              else np.zeros((0,) + B0.shape, dtype=np.int32))
    return counts, n


def final_scores(counts: np.ndarray, B0: np.ndarray,
                 degrees: np.ndarray, n: int) -> np.ndarray:
    """Eqs. (2)-(4): s_l = (sum_r t_{r,l} / (d * r)) / H_n, per node/label.

    Initially-held labels are forced to 0 (they are never re-inferred).
    """
    if n == 0:
        return np.zeros(B0.shape)
    inv_r = 1.0 / np.arange(1, n + 1)               
    raw = np.tensordot(inv_r, counts, axes=1)      
    H_n = inv_r.sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        s = raw / (degrees[:, None] * H_n)
    s = np.round(np.where(np.isfinite(s), s, 0.0), 2)    
    s[B0] = 0.0
    return s


# ------------------------------------------------------------ metrics ---

def corresponding_gt(labels: set[str],
                     gt_sequences: list[list[str]]) -> list[str]:
    """GT sequence sharing the most elements; first maximum wins (parity)."""
    best, best_count = [], 0
    for seq in gt_sequences:
        c = len(labels & set(seq))
        if c > best_count:
            best, best_count = seq, c
    return best


# --------------------------------------------------------------- main ---

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("percentage", nargs="?", type=int, default=40,
                    help="percentage of ground-truth elements per record")
    ap.add_argument("score_threshold", nargs="?", type=float, default=0.7)
    ap.add_argument("experiment", nargs="?", type=int, default=0)
    ap.add_argument("similarity_threshold", nargs="?", type=float, default=0.3)
    ap.add_argument("--data-dir", type=Path, default=Path("GT_and_CSV_files"))
    ap.add_argument("--results-dir", type=Path,
                    default=Path("Results_original/LPwE"))
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

    B_all = membership_matrix(rows, labels)
    A_all = jaccard_adjacency(B_all, args.similarity_threshold)

    keep = A_all.any(axis=1)                
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
        print(f"nodes kept: {B0.shape[0]}/{B_all.shape[0]}  "
              f"labels: {len(labels)}  rounds (n): {n_rounds}")
    print(f"time {duration:.3f}s  cov {coverage:.4f}  acc {accuracy:.4f}  "
          f"prec {precision:.4f}  rec {recall:.4f}  f1 {f1:.4f}")

    if args.write:
        out_dir = args.results_dir / f"similarity_{args.similarity_threshold}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"LPWE_score_threshold_{args.score_threshold:.2f}.txt"
        with out.open("a") as fh:
            fh.write(f"\n{args.percentage}  {duration:.3f} {coverage:.4f} "
                     f"{accuracy:.4f} {precision:.4f}  {recall:.4f}  {f1:.4f}  ")
            if args.percentage == 100:
                fh.write("\n")


if __name__ == "__main__":
    main()
