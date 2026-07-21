#!/usr/bin/env python3
"""
Runner: GSP-X (trust-agnostic).

Sweeps the ground-truth percentages and experiment files for every
combination of relative in-order support (risup) and minimum support
requested, running gsp.py once per configuration. Each run prints its
metrics; by default they are also appended to
Results/GSP/gsp_threshold_<r>.txt

NOTE ON THE ARGUMENT ORDER: gsp.py takes
    percentage risup experiment [min_support]
which differs from the trust-aware GSP-X variants; this runner handles
the difference internally.

NOTE ON THE RESULTS FILE: the file name carries only the risup value, so
sweeping several minimum-support values with the same --results-dir
appends them to the same file. To keep sweeps separate, pass a distinct
--results-dir per minimum support.

"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT = "gsp.py"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-supports", type=float, nargs="+", default=[0.02])
    ap.add_argument("--risups", type=float, nargs="+", default=[1.0],
                    help="relative in-order support thresholds to sweep")
    ap.add_argument("--experiments", type=int, default=5)
    ap.add_argument("--percentages", type=int, nargs="+",
                    default=list(range(10, 101, 10)))
    ap.add_argument("--data-dir", type=Path, default=Path("GT_and_CSV_files"))
    ap.add_argument("--results-dir", type=Path, default=Path("Results/GSP"))
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    total = (len(args.min_supports) * len(args.risups)
             * args.experiments * len(args.percentages))
    done = 0
    for ms in args.min_supports:
        for risup in args.risups:
            print(f"\n=== GSP-X  min_support={ms}  risup={risup} ===")
            for exp in range(args.experiments):
                for pct in args.percentages:
                    # gsp.py order: percentage risup experiment min_support
                    cmd = [sys.executable, SCRIPT, str(pct), str(risup),
                           str(exp), str(ms),
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
