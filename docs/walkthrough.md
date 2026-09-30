# Walkthrough and practice questions

## Explain the pipeline in one minute

“This project summarizes simulated study data using SAS. I read the input fields explicitly and check their permitted values, unique keys, and subject references before calculating anything. I define the safety population as subjects with a dosing flag of Y. I then produce demographics and the percentage of subjects with each event, counting a subject once per term. A separate Python implementation produces reference values for comparison. The project includes missing ages, repeated events, an exact duplicate, and nondosed subjects so the main reporting rules can be checked.”

Use that explanation only after reading, running, and understanding the code. An assisted project is useful practice, but it does not replace being able to explain or modify the SAS program independently.

## Key decisions

1. **Which denominator?** Use all dosed subjects in each arm, not the number of event records or only subjects with events. The included dataset has 28 dosed subjects in each arm.
2. **What is the difference between events and incidence?** Three headaches for one person are three event records but one subject with a headache. A person with both headache and nausea counts in each term but only once in “Any event.”
3. **Why distinguish duplicate types?** The same complete event repeated can be removed and logged. The same event key with two different severities is a conflict that needs correction, so reporting stops.
4. **What happens to missing age?** It stays missing. The age mean and sample standard deviation use nonmissing observations; `AGE_N` and `AGE_MISSING` make that visible.
5. **Why scaffold both arms and every term?** A zero-event arm or category should display zero, rather than disappear because an inner join found no matching event.
6. **Why a second implementation?** A separate calculation makes it easier to notice denominator or counting errors. Passing Python tests alone does not establish that SAS ran successfully.

## Practice before describing SAS as a skill

- Run the program and locate a subject with repeated event terms. Trace that subject through `events_unique`, `subject_terms`, and `ae_incidence`.
- Explain `DATA`, `SET`, `INFILE`, `INPUT`, `WHERE`/subsetting `IF`, `BY`, `CLASS`, `GROUP BY`, and `COUNT(DISTINCT ...)` using this example.
- Change one subject from dosed to nondosed in a copy of the inputs. Predict the denominator and which event counts change, then verify.
- Change a repeated event key's severity. Find the validation table and explain why the report stops.
- Add an age summary for a subgroup and explain what to do when fewer than two ages are present.
- Read the SAS log: distinguish an error, warning, informational note, and deliberately printed completion message.

## Boundaries of the example

These source fields were chosen for a small exercise. The project has no statistical analysis plan, date-based treatment-emergence derivation, treatment switching, coding dictionary, missing-data analysis, inferential statistics, SDTM mapping, or ADaM specification. Do not present it as clinical work experience or a regulatory deliverable.
