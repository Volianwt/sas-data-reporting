# SAS Clinical Reporting Demo

A small, reproducible learning project that turns fictional subject and adverse-event records into demographic summaries, subject-level event incidence, and a data-quality report.

The reporting question is simple: **among subjects who received a dose, how many experienced each event?** Repeated events for the same subject must not inflate incidence, and subjects with no events must remain in the denominator.

## What the project demonstrates

- SAS DATA steps with explicit input types and validation; sorting and duplicate checks.
- `PROC SQL` joins, safety-population denominators, and distinct-subject event counts.
- `PROC MEANS`, `PROC FREQ`, and `PROC REPORT` for summaries and an HTML report.
- Macro variables and a small export macro for reproducible paths and outputs.
- An independent Python reference and 18 edge-case tests using only the standard library.

**Scope:** all data are generated from a deterministic formula. These are clinical-style practice tables, not real study data, CDISC datasets, a submission package, or a validated production system. Event dates are not modeled, so the project does not derive treatment-emergent adverse events.

## Data and reporting rules

| Input | Columns | Rules |
|---|---|---|
| `data/subjects.csv` | `SUBJID, ARM, AGE, SEX, DOSED` | One unique ID per subject; Active/Placebo; age 18–90 or missing; sex F/M; dosed Y/N |
| `data/adverse_events.csv` | `SUBJID, AESEQ, AETERM, SEVERITY` | Existing subject ID; positive integer sequence; one of four event terms; Mild/Moderate/Severe |

The sample has 60 fictional subjects, 30 assigned to each arm. The safety population contains the 56 dosed subjects, 28 per arm. Two safety subjects have missing age; age statistics use the available ages without imputation. Four subjects were not dosed. Their events are excluded from safety summaries.

There are 91 source event rows: one intentional exact duplicate is removed, leaving 90 unique events. Seven events belong to nondosed subjects, leaving 83 events in the safety population. A conflicting duplicate `(SUBJID, AESEQ)` fails validation. Within a term, each safety subject counts once; the “Any event” row counts each subject once across all terms. An arm with no events still receives zero-valued rows for every planned event category. Percentages use the full dosed arm denominator. Input CSVs use UTF-8 and LF line endings for SAS Studio on Linux.

## Run in SAS Studio / SAS 9.4

1. Create a project folder containing `data/` and `outputs/` in your SAS server home directory.
2. Upload `run.sas` and both input CSV files, keeping the CSVs in `data/`.
3. Set `project_root` near the beginning of `run.sas` to that server folder. A local computer path does not point to SAS Studio's server files.
4. Run the complete program. Check `outputs/sas_run.log` for errors and confirm `RUN_COMPLETED.txt` exists.
5. Open `outputs/study_summary.html` and download the four CSV files for comparison below.

Alternatively, paste [`bootstrap_sas_studio.sas`](bootstrap_sas_studio.sas) into SAS Studio. It creates the folders, downloads the public inputs and program, and runs it. This optional setup requires network access; the main `run.sas` works with uploaded files.

SAS's official [local-data upload guide](https://support.sas.com/content/dam/SAS/support/en/products-solutions/ondemand/UploadingLocalDataDec2023.pdf) explains the server folder and upload workflow. [SAS OnDemand for Academics](https://support.sas.com/en/software/ondemand-for-academics-support.html) provides access for independent learners.

## Outputs and independent comparison

| File | Purpose |
|---|---|
| `denominators.csv` | Dosed subject counts by arm |
| `demographics.csv` | Age statistics, missing ages, and sex counts/percentages |
| `ae_incidence.csv` | Subjects with any event and each event term, by arm |
| `qc_summary.csv` | Input, duplicate, exclusion, and missing-value counts |
| `study_summary.html` | Human-readable demographic, event, and QC tables |
| `sas_run.log` | Actual SAS execution log |

Committed files under `expected/` are **Python reference outputs**, not SAS results. To regenerate them and run the edge-case tests locally:

```bash
python3 reference/reference.py
python3 -m unittest discover -s tests -v
```

After downloading actual SAS CSV files into `outputs/`:

```bash
python3 reference/reference.py --compare outputs
```

The comparison checks column order, row counts, values, and an absolute numeric tolerance of 0.00011 for rounded exports. It does not inspect the SAS log or prove which tool generated a file. The tests exercise the Python reference, including repeated terms, exact/conflicting duplicates, missing age, unknown IDs, invalid categories, zero-event arms, and invalid or empty denominators. They do not execute the SAS language.

**Verified run — September 30, 2026:** the program ran in SAS Studio on SAS OnDemand for Academics (SAS 9.4). All four downloaded SAS CSV files matched the independent Python reference. The captured program log contains no `ERROR:` or `WARNING:` diagnostics, and the completion marker was produced. The Python reference's 18 tests also pass. See the [run evidence and verification record](evidence/sas-run-2026-09-30/README.md), [SAS HTML report](evidence/sas-run-2026-09-30/study_summary.html), and [SAS log with account paths redacted](evidence/sas-run-2026-09-30/sas_run.log).

GitHub Actions runs the Python reference checks; it does not run SAS. The saved SAS evidence documents this specific run, rather than certifying future changes or production use.

To recreate the exact synthetic inputs, run `python3 reference/generate_data.py`. See [`docs/walkthrough.md`](docs/walkthrough.md) for a short explanation of the reporting decisions and useful exercises.
