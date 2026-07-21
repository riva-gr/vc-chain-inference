#!/usr/bin/env python3
"""
Runner: CAM (trust-agnostic).

Sweeps the ground-truth percentages and experiment files for every
combination of minimum support and relative in-order support (risup)
requested, running cam.py once per configuration. Each run prints its
metrics; by default the metrics are also appended to
Results_original/CAM/min_support_<s>/CAM_risup_<r>.txt

"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT = "cam.py"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-supports", type=float, nargs="+", default=[0.02],
                    help="minimum support values to sweep")
    ap.add_argument("--risups", type=float, nargs="+", default=[1.0],
                    help="relative in-order support thresholds to sweep")
    ap.add_argument("--experiments", type=int, default=5,
                    help="number of experiment files, i.e. crs<pct>_(0..n-1)")
    ap.add_argument("--percentages", type=int, nargs="+",
                    default=list(range(10, 101, 10)))
    ap.add_argument("--data-dir", type=Path, default=Path("GT_and_CSV_files"))
    ap.add_argument("--results-dir", type=Path,
                    default=Path("Results_original/CAM"))
    ap.add_argument("--no-write", action="store_true",
                    help="print only; do not append to the results files")
    args = ap.parse_args()

    total = (len(args.min_supports) * len(args.risups)
             * args.experiments * len(args.percentages))
    done = 0
    for ms in args.min_supports:
        for risup in args.risups:
            print(f"\n=== CAM  min_support={ms}  risup={risup} ===")
            for exp in range(args.experiments):
                for pct in args.percentages:
                    cmd = [sys.executable, SCRIPT, str(ms), str(risup),
                           str(exp), str(pct),
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
