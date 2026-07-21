#!/usr/bin/env python3
"""
Runner: GSP-X trust-aware variants (Sec. IV-A).

Runs the three trust-aware variants of GSP-X -- credential-level,
chain-level (filtering inside the discovered frequent sequences) and
node-level filtering -- over the ground-truth percentages and experiment
files, for every requested combination of minimum support and relative
in-order support. Each run prints its metrics; by default they are also
appended under Results_modified/GSP-X/<variant>/

"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = ["gspx_remove_untrustworthy_credentials.py",
           "gspx_remove_from_sequences.py",
           "gspx_remove_untrustworthy_nodes.py"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-supports", type=float, nargs="+", default=[0.03])
    ap.add_argument("--risups", type=float, nargs="+", default=[1.0])
    ap.add_argument("--experiments", type=int, default=5)
    ap.add_argument("--percentages", type=int, nargs="+",
                    default=list(range(10, 101, 10)))
    ap.add_argument("--only", nargs="+", choices=SCRIPTS,
                    help="run only the listed variant scripts")
    ap.add_argument("--data-dir", type=Path, default=Path("GT_and_CSV_files"))
    ap.add_argument("--results-dir", type=Path,
                    default=Path("Results_modified/GSP-X"))
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    scripts = args.only or SCRIPTS
    total = (len(scripts) * len(args.min_supports) * len(args.risups)
             * args.experiments * len(args.percentages))
    done = 0
    for script in scripts:
        for ms in args.min_supports:
            for risup in args.risups:
                print(f"\n=== {script}  min_support={ms}  risup={risup} ===")
                for exp in range(args.experiments):
                    for pct in args.percentages:
                        # variants order: min_support risup experiment percentage
                        cmd = [sys.executable, script, str(ms), str(risup),
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
