#!/usr/bin/env python3
"""
CAM -- Co-Acquisition Matrix (Section III-B, Eq. (1), Definition III.1).
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


# ------------------------------------------------------- count matrix ---

def acquisition_counts(rows: list[list[str]], creds: list[str]) -> np.ndarray:
    """M x M matrix of eventually-follows counts over the records.

    Elements are assumed unique per record (Sec. III-A); repeats collapse to
    their first occurrence, matching the original row.index semantics.
    """
    index = {c: k for k, c in enumerate(creds)}
    counts = np.zeros((len(creds), len(creds)), dtype=np.int64)
    for row in rows:
        first_pos: dict[str, int] = {}
        for pos, element in enumerate(row):
            first_pos.setdefault(element, pos)
        idx = np.fromiter((index[e] for e in first_pos), dtype=np.int64,
                          count=len(first_pos))
        pos = np.fromiter(first_pos.values(), dtype=np.int64,
                          count=len(first_pos))
        # counts[i, j] += 1 for every pair with pos_i < pos_j
        counts[np.ix_(idx, idx)] += (pos[:, None] < pos[None, :])
    return counts


# ----------------------------------------------------- link extraction ---

def chain_links(counts: np.ndarray, creds: list[str],
                min_support: float, risup: float,
                n_rows: int) -> list[list[str]]:
    """Ordered pairs [a, b] passing Eq. (1): support and risup thresholds."""
    support = counts + counts.T                       # co-occurrence counts
    ratio = np.divide(counts, support,
                      out=np.zeros(counts.shape, dtype=float),
                      where=support > 0)
    keep = (support > 0) & (support >= n_rows * min_support) & (ratio >= risup)
    np.fill_diagonal(keep, False)
    return [[creds[i], creds[j]] for i, j in zip(*np.nonzero(keep))]


# ----------------------------------------------------- chain assembly ---

def assemble_chains(links: list[list[str]]) -> list[list[str]]:
    """Join links into maximal chains under the disjointness condition.

    An extension is admissible only if (a) its first element equals the
    chain's last element AND (b) it introduces no element already present in
    the chain. Condition (b) is the paper's disjointness requirement; it
    makes every chain a simple path, so the depth-first search terminates
    after at most M extensions regardless of cycles in the link digraph.
    Chains with no admissible extension are the maximal ones (deduplicated).
    """
    by_first: dict[str, list[list[str]]] = {}
    for link in links:
        by_first.setdefault(link[0], []).append(link)

    results: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for link in links:
        stack = [link]
        while stack:
            chain = stack.pop()
            chain_set = set(chain)
            extensions = [nxt for nxt in by_first.get(chain[-1], [])
                          if not (set(nxt[1:]) & chain_set)]   # disjointness
            if extensions:
                stack.extend(chain + nxt[1:] for nxt in extensions)
            else:
                key = tuple(chain)
                if key not in seen:
                    seen.add(key)
                    results.append(chain)
    return results


def is_subsequence(sub: list[str], seq: list[str]) -> bool:
    it = iter(seq)
    return all(x in it for x in sub)


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
    ap.add_argument("min_support", nargs="?", type=float, default=0.03,
                    help="minimum co-occurrence support as a fraction of N")
    ap.add_argument("risup", nargs="?", type=float, default=1.0)
    ap.add_argument("experiment", nargs="?", type=int, default=0)
    ap.add_argument("percentage", nargs="?", type=int, default=100)
    ap.add_argument("--data-dir", type=Path, default=Path("GT_and_CSV_files"))
    ap.add_argument("--results-dir", type=Path,
                    default=Path("Results_original/CAM"))
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

    counts = acquisition_counts(rows, creds)
    links = chain_links(counts, creds, args.min_support, args.risup, len(rows))
    chains = remove_subchains(assemble_chains(links))

    duration = time.time() - start                

    if args.verbose:
        print(f"records: {len(rows)}  credentials: {len(creds)}  "
              f"links: {len(links)}  chains: {len(chains)}")
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
        out_dir = args.results_dir / f"min_support_{args.min_support}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"CAM_risup_{args.risup:.2f}.txt"
        with out.open("a") as fh:
            fh.write(f"\n{args.percentage}  {duration:.3f}  {coverage:.4f} "
                     f"{accuracy:.4f} {precision:.4f}  {recall:.4f}  {f1:.4f}  ")
            if args.percentage == 100:
                fh.write("\n")


if __name__ == "__main__":
    main()
