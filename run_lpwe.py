#!/usr/bin/env python3
"""
Runner: LPwE (trust-agnostic).

Sweeps the ground-truth percentages and experiment files for every
combination of similarity threshold and score threshold requested,
running lpwe.py once per configuration. Each run prints its metrics; by
default they are also appended to
Results_original/LPwE/similarity_<t>/LPWE_score_threshold_<s>.txt

"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT = "lpwe.py"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--similarity-thresholds", type=float, nargs="+",
                    default=[0.4], help="Jaccard similarity thresholds")
    ap.add_argument("--score-thresholds", type=float, nargs="+",
                    default=[0.7], help="label score thresholds")
    ap.add_argument("--experiments", type=int, default=5)
    ap.add_argument("--percentages", type=int, nargs="+",
                    default=list(range(10, 101, 10)))
    ap.add_argument("--data-dir", type=Path, default=Path("GT_and_CSV_files"))
    ap.add_argument("--results-dir", type=Path,
                    default=Path("Results_original/LPwE"))
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    total = (len(args.similarity_thresholds) * len(args.score_thresholds)
             * args.experiments * len(args.percentages))
    done = 0
    for sim in args.similarity_thresholds:
        for score in args.score_thresholds:
            print(f"\n=== LPwE  similarity={sim}  score={score} ===")
            for exp in range(args.experiments):
                for pct in args.percentages:
                    # lpwe.py order: percentage score exp similarity
                    cmd = [sys.executable, SCRIPT, str(pct), str(score),
                           str(exp), str(sim),
                           "--data-dir", str(args.data_dir),
                           "--results-dir", str(args.results_dir)]
                    if not args.no_write:
                        cmd.append("--write")
                    done += 1
                    print(f"[{done}/{total}] exp={exp} gt={pct}%  ",
                          end="", flush=True)
                    subprocess.run(cmd)
    print(f"\nfinished: {done} runs")


if __name__ == "__main__":
    main()
