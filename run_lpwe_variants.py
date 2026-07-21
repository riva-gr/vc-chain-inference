#!/usr/bin/env python3
"""
Runner: LPwE trust-aware variants (Sec. IV-C).

Runs the three trust-aware variants of LPwE -- node-level filtering,
label-level filtering (similarity computed on trustworthy labels) and
prediction-level filtering (only trustworthy labels are accepted) -- over
the ground-truth percentages and experiment files, for every requested
combination of similarity and score thresholds. Each run prints its
metrics; by default they are also appended under the variant's results
directory.

NOTE: the label-level variant writes under Results/LPwE by default, the
other two under Results_modified/LPwE. Passing --results-dir overrides
this for every variant in the run.

"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = ["lpwe_remove_untrustworthy_nodes.py",
           "lpwe_similarity_by_trustworthy_labels.py",
           "lpwe_add_only_trustworthy_labels.py"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--similarity-thresholds", type=float, nargs="+",
                    default=[0.4])
    ap.add_argument("--score-thresholds", type=float, nargs="+", default=[0.7])
    ap.add_argument("--experiments", type=int, default=5)
    ap.add_argument("--percentages", type=int, nargs="+",
                    default=list(range(10, 101, 10)))
    ap.add_argument("--only", nargs="+", choices=SCRIPTS,
                    help="run only the listed variant scripts")
    ap.add_argument("--data-dir", type=Path, default=Path("GT_and_CSV_files"))
    ap.add_argument("--results-dir", type=Path, default=None,
                    help="override each variant's default results directory")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    scripts = args.only or SCRIPTS
    total = (len(scripts) * len(args.similarity_thresholds)
             * len(args.score_thresholds) * args.experiments
             * len(args.percentages))
    done = 0
    for script in scripts:
        for sim in args.similarity_thresholds:
            for score in args.score_thresholds:
                print(f"\n=== {script}  similarity={sim}  score={score} ===")
                for exp in range(args.experiments):
                    for pct in args.percentages:
                        # variants order: percentage score exp similarity
                        cmd = [sys.executable, script, str(pct), str(score),
                               str(exp), str(sim),
                               "--data-dir", str(args.data_dir)]
                        if args.results_dir is not None:
                            cmd += ["--results-dir", str(args.results_dir)]
                        if not args.no_write:
                            cmd.append("--write")
                        done += 1
                        print(f"[{done}/{total}] exp={exp} gt={pct}%  ",
                              end="", flush=True)
                        subprocess.run(cmd)
    print(f"\nfinished: {done} runs")


if __name__ == "__main__":
    main()
