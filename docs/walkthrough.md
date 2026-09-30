# Calculation and validation notes

## Population and denominators

The `DOSED` field determines inclusion: records with `DOSED='Y'` are included in the grouped summaries. The supplied inputs contain 28 included participants per group. Percentages use that full group count, including participants with no event records.

## Event records and participant counts

Several records for the same participant and category contribute one participant to that category's count. A participant appearing in two categories counts once in each category and once in the overall “Any event” row. The program creates `subject_terms` with `PROC SORT NODUPKEY` and uses `COUNT(DISTINCT SUBJID)` for the overall count.

## Duplicate handling

An exact duplicate is removed and counted in the quality report. Two different records sharing `(SUBJID, AESEQ)` are a conflict, so the program stops rather than choosing one silently. Duplicate participant IDs and event records referring to unknown participant IDs also stop processing.

## Missing values

Missing ages remain missing. `PROC MEANS` calculates the mean and sample standard deviation from nonmissing values. `AGE_N` and `AGE_MISSING` report the available and missing counts separately. Missing identifiers or required category fields fail validation.

## Zero-count categories

The program creates both groups and every planned event category before joining observed counts. A group or category with no matching events receives a zero count instead of disappearing from the output.

## Independent comparison

The Python reference implements the same reporting rules separately. Its tests cover missing data, duplicates, invalid values, zero-event groups, and incorrect export values. CSV comparisons check schema, row order, counts, and numeric precision. The captured SAS run is recorded separately from the Python tests.

## Output traceability

`qc_summary.csv` records source rows, removed duplicates, excluded events, and missing ages. `sas_run.log` records procedure diagnostics and completion. The saved evidence includes a checksum manifest for the downloaded outputs.
