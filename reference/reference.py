"""Independent Python reference for the SAS learning project (stdlib only).

These calculations do not run or validate SAS syntax. They provide expected
results against which a future SAS run can be compared.
"""
from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("Active", "Placebo")
TERMS = ("Dizziness", "Fatigue", "Headache", "Nausea")
SUBJECT_FIELDS = ("SUBJID", "ARM", "AGE", "SEX", "DOSED")
AE_FIELDS = ("SUBJID", "AESEQ", "AETERM", "SEVERITY")


def read_csv(path, fields):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(fields):
            raise ValueError(f"{path}: expected header {','.join(fields)}")
        rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ValueError(f"{path}: incorrect number of fields")
    return rows


def write_csv(path, rows):
    if not rows:
        raise ValueError("Cannot infer header from an empty result")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def valid_id(value):
    return len(value) == 4 and value[0] == "S" and value[1:].isascii() and value[1:].isdigit()


def number(value, label, low, high=None):
    try:
        value = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid {label}") from exc
    if not math.isfinite(value) or not value.is_integer() or value < low or (high is not None and value > high):
        raise ValueError(f"Invalid {label}")
    return int(value)


def analyze(subject_rows, event_rows):
    subjects = {}
    for raw in subject_rows:
        row = {key: value.strip() for key, value in raw.items()}
        sid = row["SUBJID"]
        if not valid_id(sid) or sid in subjects:
            raise ValueError("Invalid or duplicate subject ID")
        if row["ARM"] not in ARMS or row["SEX"] not in ("F", "M") or row["DOSED"] not in ("Y", "N"):
            raise ValueError("Invalid subject category")
        row["AGE"] = None if row["AGE"] == "" else number(row["AGE"], "age", 18, 90)
        subjects[sid] = row
    if not subjects:
        raise ValueError("No subjects")

    events = {}
    duplicates = 0
    for raw in event_rows:
        row = {key: value.strip() for key, value in raw.items()}
        sid = row["SUBJID"]
        if not valid_id(sid) or sid not in subjects:
            raise ValueError("Invalid or unknown AE subject ID")
        row["AESEQ"] = number(row["AESEQ"], "AE sequence", 1)
        if row["AETERM"] not in TERMS or row["SEVERITY"] not in ("Mild", "Moderate", "Severe"):
            raise ValueError("Invalid AE category")
        key = (sid, row["AESEQ"])
        if key in events:
            if events[key] != row:
                raise ValueError("Conflicting duplicate AE key")
            duplicates += 1
        events[key] = row

    safety = {sid: row for sid, row in subjects.items() if row["DOSED"] == "Y"}
    denominators = [{"ARM": arm, "N": sum(row["ARM"] == arm for row in safety.values())} for arm in ARMS]
    if any(row["N"] == 0 for row in denominators):
        raise ValueError("Every planned arm must contain at least one dosed subject")
    safety_events = [row for row in events.values() if row["SUBJID"] in safety]
    demographics = []
    incidence = []
    for denominator in denominators:
        arm, n = denominator["ARM"], denominator["N"]
        arm_subjects = {sid: row for sid, row in safety.items() if row["ARM"] == arm}
        ages = [row["AGE"] for row in arm_subjects.values() if row["AGE"] is not None]
        sexes = Counter(row["SEX"] for row in arm_subjects.values())
        demographics.append({"ARM": arm, "N": n, "AGE_N": len(ages), "AGE_MISSING": n - len(ages),
                             "AGE_MEAN": round(mean(ages), 4) if ages else "",
                             "AGE_SD": round(stdev(ages), 4) if len(ages) > 1 else "",
                             "AGE_MIN": min(ages) if ages else "", "AGE_MAX": max(ages) if ages else "",
                             "FEMALE_N": sexes["F"], "MALE_N": sexes["M"],
                             "FEMALE_PCT": round(100 * sexes["F"] / n, 4),
                             "MALE_PCT": round(100 * sexes["M"] / n, 4)})
        for term in ("Any event",) + TERMS:
            ids = {row["SUBJID"] for row in safety_events
                   if row["SUBJID"] in arm_subjects and (term == "Any event" or row["AETERM"] == term)}
            incidence.append({"ARM": arm, "CATEGORY": term, "SUBJECT_N": len(ids), "N": n,
                              "PCT": round(100 * len(ids) / n, 4)})
    qc = [{"METRIC": name, "VALUE": value} for name, value in (
        ("input_subjects", len(subject_rows)), ("input_ae_rows", len(event_rows)),
        ("exact_duplicate_ae_rows_removed", duplicates), ("unique_ae_rows", len(events)),
        ("safety_subjects", len(safety)), ("safety_ae_rows", len(safety_events)),
        ("nondosed_ae_rows_excluded", len(events) - len(safety_events)),
        ("safety_age_missing", sum(row["AGE"] is None for row in safety.values())),
    )]
    return {"denominators.csv": denominators, "demographics.csv": demographics,
            "ae_incidence.csv": incidence, "qc_summary.csv": qc}


def compare_directory(expected, actual_dir):
    """Compare a genuine SAS export by column, order and numeric tolerance."""
    failures = []
    for filename, rows in expected.items():
        path = Path(actual_dir) / filename
        try:
            actual = read_csv(path, tuple(rows[0]))
        except (OSError, ValueError) as exc:
            failures.append(str(exc))
            continue
        if len(rows) != len(actual):
            failures.append(f"{filename}: expected {len(rows)} rows, got {len(actual)}")
            continue
        for index, (want, got) in enumerate(zip(rows, actual), 2):
            for key, value in want.items():
                text = got[key].strip()
                if isinstance(value, (int, float)):
                    try:
                        equal = math.isfinite(float(text)) and math.isclose(float(text), value, abs_tol=0.00011, rel_tol=0)
                    except ValueError:
                        equal = False
                else:
                    equal = text in ("", ".") if value == "" else text == value
                if not equal:
                    failures.append(f"{filename}:{index} {key}: expected {value!r}, got {text!r}")
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare", type=Path, help="Directory containing actual SAS-exported CSV files")
    args = parser.parse_args()
    result = analyze(read_csv(ROOT / "data/subjects.csv", SUBJECT_FIELDS),
                     read_csv(ROOT / "data/adverse_events.csv", AE_FIELDS))
    if args.compare:
        failures = compare_directory(result, args.compare)
        if failures:
            raise SystemExit("\n".join(failures))
        print("PASS: supplied CSV files match Python reference values. This does not verify their provenance.")
    else:
        for filename, rows in result.items():
            write_csv(ROOT / "expected" / filename, rows)
        print("Wrote 4 Python reference CSVs under expected/. SAS was not run.")
        for row in result["qc_summary.csv"]:
            print(f"{row['METRIC']}: {row['VALUE']}")


if __name__ == "__main__":
    main()
