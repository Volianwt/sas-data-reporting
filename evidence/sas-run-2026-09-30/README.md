# Verified SAS run — September 30, 2026

## Run provenance

- Environment: SAS Studio on SAS OnDemand for Academics; the HTML report identifies SAS Software Version 9.4.
- Program and inputs: source commit `983ecb1547ee2a96e23583f6929cbe04bc6e6f2d`.
- Execution: the public bootstrap was run in an authenticated SAS Studio session. After completion, the seven files below were downloaded from the SAS server's `outputs/` folder.
- The CSV files, HTML report, and completion marker are preserved byte for byte from the downloads.
- Only account identifiers in `sas_run.log` were redacted: the server home path became `<SAS_HOME>` and the owner name became `<SAS_USER>`. Procedure diagnostics, counts, timings, and report values are unchanged.
- All participant and event records are synthetic.

## Results

| Check | Result |
|---|---|
| Program completion | `RUN_COMPLETED.txt` produced; log ends with `NOTE: DEMO COMPLETED.` |
| Captured SAS program log | 0 ERROR diagnostics; 0 WARNING diagnostics |
| Four SAS-exported CSVs vs independent Python reference | PASS |
| Python reference edge-case tests | 18 passed |
| Participants | 60 input; 56 included; 28 included per group |
| Event records | 91 input; 1 exact duplicate removed; 90 unique; 83 included in reporting |
| Missing ages among included participants | 2; excluded from age statistics, retained in participant counts |

The comparison checks column order, row counts, text values, and numeric values within an absolute tolerance of 0.00011. The Python tests cover the independent reference implementation, not the SAS interpreter.

## Recheck the saved results

From the repository root:

```bash
python3 reference/reference.py --compare evidence/sas-run-2026-09-30
python3 -m unittest discover -s tests -v
```

Recorded comparison output:

```text
PASS: supplied CSV files match Python reference values. This does not verify their provenance.
```

Provenance comes from the observed SAS Studio execution and downloads described above; numerical agreement alone cannot establish which program created a file.

## Files

- [Demographics and event report](study_summary.html): download and open in a browser to view the rendered SAS tables.
- [SAS execution log](sas_run.log), with account paths redacted.
- [Completion marker](RUN_COMPLETED.txt).
- [Denominators](denominators.csv), [demographics](demographics.csv), [event incidence](ae_incidence.csv), and [quality checks](qc_summary.csv).
- [SHA-256 manifest](SHA256SUMS): hashes of these preserved evidence files, after log redaction.

The GitHub Actions workflow runs Python checks only. Rerun SAS and save new evidence if the SAS source or input data change.
