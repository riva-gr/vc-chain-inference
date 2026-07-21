#!/usr/bin/env python3
"""
GSP-X -- GSP Extended (Section III-A, Eq. (1)).
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

try:
    from pymining import seqmining
except ImportError:                                    
    sys.exit("GSP-X requires the 'pymining' package: pip install pymining")


# --------------------------------------------------------------- I/O ---

def load_rows(path: Path) -> list[list[str]]:
    """Read a CSV as a list of string rows; exit cleanly if missing."""
    try:
        with path.open(newline="") as fh:
            return [row for row in csv.reader(fh) if row]
    except FileNotFoundError:
        sys.exit(f"The file {path} does not exist!")


# -------------------------------------------------------------- mining ---

def mine_frequent_sequences(rows: list[list[str]],
                            min_count: float) -> list[list[str]]:
    """Complete frequent-sequence enumeration; keep length >= 2 (parity)."""
    results = seqmining.freq_seq_enum(rows, min_count)
    return [list(seq) for seq, _support in results if len(seq) >= 2]


# ------------------------------------------------------- chain creation ---

def is_subsequence(sub: list[str], seq: list[str]) -> bool:
    it = iter(seq)
    return all(x in it for x in sub)


def is_subset(sub: list[str], seq: list[str]) -> bool:
    return set(sub).issubset(seq)


def build_chains(frequent: list[list[str]], rows: list[list[str]],
                 threshold: float) -> list[list[str]]:
    """Eq. (1): keep sequences whose risup >= threshold (deduplicated).

    A sequence whose element set never co-occurs in any record (zero
    unordered support) is skipped, matching the original's
    ZeroDivisionError guard.
    """
    row_sets = [set(row) for row in rows]
    chains: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for fs in frequent:
        ordered = unordered = 0
        fs_set = set(fs)
        for row, row_set in zip(rows, row_sets):
            if is_subsequence(fs, row):
                ordered += 1
            if fs_set.issubset(row_set):
                unordered += 1
        if unordered and ordered / unordered >= threshold:
            key = tuple(fs)
            if key not in seen:
                seen.add(key)
                chains.append(fs)
    return chains


def remove_subchains(chains: list[list[str]]) -> list[list[str]]:
    """Drop chains that are ordered subsequences of a longer chain."""
    chains.sort(key=len)
    drop: set[tuple[str, ...]] = set()
    for i in range(len(chains)):
        for j in range(i + 1, len(chains)):
            if is_subsequence(chains[i], chains[j]):
                drop.add(tuple(chains[i]))
                break
    return [c for c in chains if tuple(c) not in drop]


# ------------------------------------------------------------ metrics ---

def corresponding_gt(chain: list[str],
                     gt_sequences: list[list[str]]) -> list[str]:
    """GT sequence sharing the most elements; first maximum wins (parity)."""
    best, best_count = [], 0
    for seq in gt_sequences:
        c = len(set(chain) & set(seq))
        if c > best_count:
            best, best_count = seq, c
    return best


# --------------------------------------------------------------- main ---

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("percentage", nargs="?", type=int, default=100,
                    help="percentage of ground-truth elements per record")
    ap.add_argument("threshold", nargs="?", type=float, default=0.5,
                    help="relative in-order support (risup) threshold")
    ap.add_argument("experiment", nargs="?", type=int, default=0)
    ap.add_argument("min_support", nargs="?", type=float, default=0.03,
                    help="minimum support as a fraction of N (orig: 0.03)")
    ap.add_argument("--data-dir", type=Path, default=Path("GT_and_CSV_files"))
    ap.add_argument("--results-dir", type=Path, default=Path("Results/GSP"))
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

    frequent = mine_frequent_sequences(rows, args.min_support * len(rows))
    chains = remove_subchains(build_chains(frequent, rows, args.threshold))

    duration = time.time() - start                

    if args.verbose:
        print(f"records: {len(rows)}  frequent sequences: {len(frequent)}  "
              f"chains: {len(chains)}")
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
        args.results_dir.mkdir(parents=True, exist_ok=True)
        out_dir = args.results_dir / f"min_support_{args.min_support}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"gsp_threshold_{args.threshold:.2f}.txt"
        with out.open("a") as fh:
            fh.write(f"\n{args.percentage}  {duration:.3f} {coverage:.4f} "
                     f"{accuracy:.4f} {precision:.4f}  {recall:.4f}  {f1:.4f}  ")
            if args.percentage == 100:
                fh.write("\n")


if __name__ == "__main__":
    main()
