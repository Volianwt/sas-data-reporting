# SAS Data Analysis and Reporting

A reproducible workflow for importing structured records, checking data quality, and generating summary tables with SAS. An independent Python implementation checks the exported results.

## Workflow

1. Read two CSV files with explicit field types and schema checks.
2. Check unique identifiers, category values, numeric ranges, and links between tables.
3. Remove exact duplicate events and flag conflicting records.
4. Filter the reporting population, calculate grouped summaries, and count distinct participants by event category.
5. Export four CSV tables and an HTML report; compare the CSV values with the Python reference.

The implementation uses SAS DATA steps, `PROC SORT`, `PROC SQL`, `PROC MEANS`, `PROC FREQ`, `PROC REPORT`, and macro variables. Python reference checks cover 18 edge cases.

## Data

All records are synthetic and generated deterministically. The sample contains 60 participants in two groups and 91 event rows. The input files retain their original field names:

| Input | Columns | Checks |
|---|---|---|
| `data/subjects.csv` | `SUBJID, ARM, AGE, SEX, DOSED` | Unique participant ID; valid group and flags; age 18–90 or missing |
| `data/adverse_events.csv` | `SUBJID, AESEQ, AETERM, SEVERITY` | Existing participant ID; positive sequence; valid event and severity categories |

`ARM` identifies the group. `DOSED='Y'` defines which participants are included in the summaries: 56 in total, 28 per group. Two included participants have missing age; age statistics use available values without imputation.

One exact duplicate is removed from the 91 event rows. Seven of the remaining 90 events belong to excluded participants, leaving 83 included events. Conflicting records sharing `(SUBJID, AESEQ)` stop processing. Counts use distinct participants, so repeated events do not inflate a category's percentage. All included participants remain in the denominator, including those with no events. Every planned category is displayed even when its count is zero.

## Run with SAS Studio / SAS 9.4

Paste [`bootstrap_sas_studio.sas`](bootstrap_sas_studio.sas) into SAS Studio and run it. The setup creates a project folder, downloads the public source and input files, and runs the reporting program.

For an offline setup:

1. Create a server folder containing `data/` and `outputs/`.
2. Upload `run.sas` and the two input CSVs, keeping the CSVs under `data/`.
3. Set `project_root` in `run.sas` to that server folder.
4. Run the full program. Check `outputs/sas_run.log` and confirm `RUN_COMPLETED.txt` exists.
5. Open the HTML report and download the CSV outputs.

Input CSVs use UTF-8 and LF line endings. SAS Studio uses server-side paths. See the official [SAS upload guide](https://support.sas.com/content/dam/SAS/support/en/products-solutions/ondemand/UploadingLocalDataDec2023.pdf) for file handling.

## Outputs

| File | Contents |
|---|---|
| `denominators.csv` | Included participants by group |
| `demographics.csv` | Age statistics, missing ages, and category counts/percentages |
| `ae_incidence.csv` | Distinct participant counts and percentages by event category |
| `qc_summary.csv` | Input, duplicate, exclusion, and missing-value counts |
| `study_summary.html` | Summary tables and quality checks |
| `sas_run.log` | SAS execution log |

The filenames and field names are retained for consistency with the saved run. [`docs/walkthrough.md`](docs/walkthrough.md) explains the calculation rules and validation decisions.

## Verification

The program ran in SAS Studio on SAS OnDemand for Academics (SAS 9.4) on September 30, 2026. All four exported CSVs matched the independent reference, and the captured program log contains no ERROR or WARNING diagnostics.

- [Saved run and verification record](evidence/sas-run-2026-09-30/README.md)
- [HTML report](evidence/sas-run-2026-09-30/study_summary.html)
- [SAS log with account paths redacted](evidence/sas-run-2026-09-30/sas_run.log)

Files under `expected/` are Python reference outputs. To regenerate them and run the reference tests:

```bash
python3 reference/reference.py
python3 -m unittest discover -s tests -v
```

To compare a new SAS export or the saved run:

```bash
python3 reference/reference.py --compare outputs
python3 reference/reference.py --compare evidence/sas-run-2026-09-30
```

The comparison checks column order, row counts, text values, and numeric values within an absolute tolerance of 0.00011. The 18 tests cover the Python reference, including duplicates, missing values, invalid categories, unmatched identifiers, and groups with no events. GitHub Actions runs those Python checks; the saved SAS log and outputs document the SAS execution at the source revision identified in the verification record.

To recreate the inputs, run `python3 reference/generate_data.py`.
