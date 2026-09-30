"""Create deterministic fictional study records; no source patient data."""
from reference import ROOT, write_csv


def main():
    subjects, events = [], []
    terms = ("Headache", "Nausea", "Fatigue", "Dizziness")
    for index in range(1, 61):
        subject = {"SUBJID": f"S{index:03d}", "ARM": "Active" if index % 2 else "Placebo",
                   "AGE": "" if index in (17, 44) else 22 + (index * 7) % 50,
                   "SEX": "F" if index % 3 else "M", "DOSED": "N" if index in (11, 30, 41, 60) else "Y"}
        subjects.append(subject)
        # Some subjects have no events; repeat terms test distinct-subject counts.
        if index % 4:
            for sequence in range(1, 2 + index % 3):
                events.append({"SUBJID": subject["SUBJID"], "AESEQ": sequence,
                               "AETERM": terms[(index + (0 if index % 5 == 0 else sequence)) % 4],
                               "SEVERITY": ("Mild", "Moderate", "Severe")[(index + sequence) % 3]})
    # An intentional, exact source duplication is removed, then reported in QC.
    events.append(dict(events[0]))
    write_csv(ROOT / "data/subjects.csv", subjects)
    write_csv(ROOT / "data/adverse_events.csv", events)
    print(f"Generated {len(subjects)} fictional subjects and {len(events)} event rows.")


if __name__ == "__main__":
    main()
