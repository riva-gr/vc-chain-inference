# Verifiable-Credential Chain Inference

Reference implementation of **GSP-X**, **CAM**, and **LPwE** for inferring hidden credential chains from populations of verifiable credentials. The repository also contains three trust-aware variants for each algorithm and the synthetic-data generator used in the experiments.

## Algorithms

| Algorithm | Full name / approach | Description | Paper section |
|---|---|---|:---:|
| **GSP-X** | Sequential-pattern-mining baseline | Mines frequent sequences and filters them using relative in-order support. | III-A |
| **CAM** | Co-Acquisition Matrix | Converts pairwise ordering statistics into credential chains under a disjointness condition. | III-B |
| **LPwE** | Label Propagation with Encirclement | Propagates credentials over a similarity graph and scores them using a harmonic-normalised encirclement measure. | III-C |

Each algorithm has three **trust-aware variants** that incorporate issuer trust by filtering at the credential, node, or link/prediction level, as described in Sections IV-A to IV-C.

This repository accompanies the paper *Building Trust on Arbitrary Properties of Microservices Through Verifiable Credential Chains*.

## Contents

- [Requirements](#requirements)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
- [Running the code](#running-the-code)
  - [Direct script runs](#direct-script-runs)
  - [Batch runs and parameter sweeps](#batch-runs-and-parameter-sweeps)
- [Datasets](#datasets)
- [Implementation notes](#implementation-notes)
- [Default results directories](#default-results-directories)
- [License](#license)

## Requirements

- Python **3.10 or newer**. The code uses `list[str]`-style type annotations.
- Install the dependencies from the repository root:

```bash
pip install -r requirements.txt
```

| Dependency | Required by | Purpose |
|---|---|---|
| `numpy` | CAM and LPwE | Numerical and graph-based operations. |
| `pymining` | GSP-X | Sequential-pattern mining. |

## Repository layout

```text
.
├── README.md
├── LICENSE
├── requirements.txt
│
├── gsp.py                                   # GSP-X base implementation
├── cam.py                                   # CAM base implementation
├── lpwe.py                                  # LPwE base implementation
│
├── gspx_remove_untrustworthy_credentials.py # GSP-X trust variants (Sec. IV-A)
├── gspx_remove_from_sequences.py
├── gspx_remove_untrustworthy_nodes.py
│
├── cam_remove_untrustworthy_credentials.py  # CAM trust variants (Sec. IV-B)
├── cam_remove_untrustworthy_nodes.py
├── cam_trustworthy_links.py
│
├── lpwe_remove_untrustworthy_nodes.py       # LPwE trust variants (Sec. IV-C)
├── lpwe_similarity_by_trustworthy_labels.py
├── lpwe_add_only_trustworthy_labels.py
│
├── run_gspx.py                              # Batch runners (sweeps)
├── run_gspx_variants.py
├── run_cam.py
├── run_cam_variants.py
├── run_lpwe.py
├── run_lpwe_variants.py
│
├── create_files.py                          # Dataset generator

```

> [!IMPORTANT]
> The trust-aware variants import their family base modules: `gsp.py`, `cam.py`, and `lpwe.py`. Keep all Python scripts in the same directory.

## Quick start

Install the dependencies, then run CAM on the 60%-ground-truth dataset using replicate `0`, `min_support=0.02`, and `risup=1.0`:

```bash
pip install -r requirements.txt
python3 cam.py 0.02 1.0 0 60
```

A successful run prints a single metrics line:

```text
time 0.24s  cov 1.0000  acc 1.0000  prec 1.0000  rec 1.0000  f1 1.0000
```

> [!NOTE]
> Every script prints its metrics to the terminal. Direct script runs append to a results file only when `--write` is supplied.

## Running the code

Run all commands from the directory containing the scripts. The repository supports two execution modes:

| Mode | Best suited for | Results-file behaviour |
|---|---|---|
| **Direct script** | One configuration, debugging, inspection, or spot checks | Prints only by default; add `--write` to append the result. |
| **Runner** | Percentage, replicate, and parameter sweeps | Writes by default; add `--no-write` to suppress file output. |

### Direct script runs

#### Positional argument order

Positional arguments are order-sensitive and differ by algorithm family.

| Family / scripts | Command form | Positional argument order |
|---|---|---|
| **GSP-X base**<br>`gsp.py` | `python3 gsp.py ...` | `<percentage> <risup> <experiment> [min_support]` |
| **CAM base and GSP-X/CAM variants**<br>`cam.py`, `gspx_*`, `cam_*` | `python3 <script> ...` | `<min_support> <risup> <experiment> <percentage>` |
| **LPwE family**<br>`lpwe.py`, `lpwe_*` | `python3 <script> ...` | `<percentage> <score_threshold> <experiment> <similarity_threshold>` |

#### Flags available on every script

| Flag | Default | Effect |
|---|---|---|
| `--verbose` | Off | Print discovered chains or additional diagnostics. |
| `--write` | Off | Append the metrics line to the script-specific results file. |
| `--data-dir PATH` | `GT_and_CSV_files` | Read datasets from an alternative directory. |
| `--results-dir PATH` | Script-specific | Write results under an alternative directory. |

#### Single-run examples

Run the three base algorithms:

```bash
python3 gsp.py 60 1.0 0 0.02
python3 cam.py 0.02 1.0 0 60
python3 lpwe.py 60 0.7 0 0.4
```

Run representative trust-aware variants:

```bash
python3 cam_trustworthy_links.py 0.01 1.0 0 60
python3 gspx_remove_from_sequences.py 0.03 1.0 0 60
python3 lpwe_add_only_trustworthy_labels.py 60 0.7 0 0.4
```

Print the discovered chains or diagnostics and append the result to disk:

```bash
python3 cam.py 0.02 1.0 0 80 --verbose --write
```

### Batch runs and parameter sweeps

Each runner iterates over percentages, experiment files, and any supplied parameter values. It prints an `[n/total]` progress line for every run.

Runners **write results by default**. Pass `--no-write` to print the metrics without modifying results files.

#### Available runners

| Family | Base runner | Variant runner | Parameter flags |
|---|---|---|---|
| **GSP-X** | `run_gspx.py` | `run_gspx_variants.py` | `--min-supports`, `--risups` |
| **CAM** | `run_cam.py` | `run_cam_variants.py` | `--min-supports`, `--risups` |
| **LPwE** | `run_lpwe.py` | `run_lpwe_variants.py` | `--similarity-thresholds`, `--score-thresholds` |

#### Common runner flags

| Flag | Availability | Purpose |
|---|---|---|
| `--experiments N` | All runners | Set the number of experiment files or replicates. |
| `--percentages P ...` | All runners | Select the ground-truth percentages to execute. |
| `--data-dir PATH` | All runners | Read datasets from an alternative directory. |
| `--results-dir PATH` | All runners | Write results under an alternative directory. |
| `--no-write` | All runners | Print results without writing files. |
| `--only SCRIPT ...` | Variant runners only | Run only the named trust-aware variants. |

Every parameter flag accepts multiple values, producing a full cross-product sweep.

#### Runner examples

Run one CAM configuration across all default percentages and five replicates:

```bash
python3 run_cam.py --min-supports 0.02 --risups 1.0
```

Run a parameter-sensitivity sweep at 80% ground truth:

```bash
python3 run_cam.py \
  --min-supports 0.01 0.02 0.03 0.04 0.05 0.06 0.07 0.08 \
  --risups 0.2 0.4 0.6 0.8 1.0 \
  --percentages 80
```

Run all three CAM trust-aware variants:

```bash
python3 run_cam_variants.py --min-supports 0.01 --risups 1.0
```

Run one LPwE trust-aware variant only:

```bash
python3 run_lpwe_variants.py \
  --only lpwe_add_only_trustworthy_labels.py
```

## Datasets

Dataset files follow the naming convention `crs<percentage>_(<experiment>).csv`, with one wallet per row. Ground-truth chains are stored in `ground_truth_sequences.csv`, with one chain per row.

| Property | Value |
|---|---|
| Ground-truth chains | 10 chains |
| Chain lengths | 2-11 credentials |
| Ground-truth credentials | 65 total |
| Wallets per dataset | 1,000 |
| Default miscellaneous/noise pool | 100 credentials |

The generator is deterministically seeded, so a given configuration produces byte-identical files on any machine.

## Implementation notes

The implementation follows the algorithms described in the paper. The following behaviours are important when reading, extending, or validating the code.

### Accuracy excludes true negatives

Accuracy is computed as:

```text
TP / (TP + FP + FN)
```

This is the Jaccard index over predicted and ground-truth elements, consistent with Section V-A. The unbounded set of credentials that are never predicted is not counted.

### Trust assignment

In the trust-aware variants:

- Ground-truth credentials receive trust sampled uniformly from `[0.50, 1.0]`.
- Miscellaneous credentials receive trust sampled from `[0.0, 0.49)`.
- Values are rounded to two decimal places.
- A fixed seed is applied over the sorted credential list.

### CAM chain assembly always terminates

A chain is extended only with credentials that it does not already contain, implementing the disjointness condition from Section III-B. Assembly therefore terminates on any link graph, including cyclic graphs.

### Coverage is informational

Results files include a coverage column representing the fraction of ground-truth elements recovered. This column is provided for information and is not one of the metrics reported in the paper.

## Default results directories

| Component | Default location | Override |
|---|---|---|
| Base GSP-X | `Results/` | Use `--results-dir PATH`. |
| Base CAM and LPwE | `Results_original/` | Use `--results-dir PATH`. |
| Trust-aware variants | `Results_modified/` | Use `--results-dir PATH`. |
| LPwE label-level variant | `Results/LPwE` | Use `--results-dir PATH` to place all variants together. |

## License

Released under the MIT License. See [LICENSE](LICENSE).
