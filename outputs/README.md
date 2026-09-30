SAS writes `sas_run.log`, `study_summary.html`, and four CSV files here.
Generated results are ignored by Git. This folder must exist before `run.sas`
starts. Committed Python reference results live separately in `expected/`.
The verified SAS run from September 30, 2026 is preserved in
`evidence/sas-run-2026-09-30/`, including the downloaded CSV files, HTML report,
completion marker, and log with SAS account paths redacted.
