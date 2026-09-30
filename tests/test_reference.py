"""Meaningful edge-case checks of the independent reference calculations."""
import copy
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reference"))
from reference import analyze, compare_directory, read_csv, write_csv, SUBJECT_FIELDS


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.subjects = [
            dict(SUBJID="S001", ARM="Active", AGE="40", SEX="F", DOSED="Y"),
            dict(SUBJID="S002", ARM="Active", AGE="", SEX="M", DOSED="Y"),
            dict(SUBJID="S003", ARM="Placebo", AGE="60", SEX="F", DOSED="Y"),
            dict(SUBJID="S004", ARM="Placebo", AGE="50", SEX="M", DOSED="Y"),
            dict(SUBJID="S005", ARM="Active", AGE="30", SEX="F", DOSED="N"),
        ]
        self.events = [
            dict(SUBJID="S001", AESEQ="1", AETERM="Headache", SEVERITY="Mild"),
            dict(SUBJID="S001", AESEQ="2", AETERM="Headache", SEVERITY="Moderate"),
            dict(SUBJID="S001", AESEQ="3", AETERM="Nausea", SEVERITY="Mild"),
            dict(SUBJID="S005", AESEQ="1", AETERM="Headache", SEVERITY="Mild"),
        ]

    def result(self):
        return analyze(self.subjects, self.events)

    def test_safety_denominators_exclude_nondosed(self):
        self.assertEqual(self.result()["denominators.csv"], [{"ARM": "Active", "N": 2}, {"ARM": "Placebo", "N": 2}])
        qc = {row["METRIC"]: row["VALUE"] for row in self.result()["qc_summary.csv"]}
        self.assertEqual(qc["nondosed_ae_rows_excluded"], 1)

    def test_subject_incidence_is_not_event_count(self):
        rows = {row["CATEGORY"]: row for row in self.result()["ae_incidence.csv"] if row["ARM"] == "Active"}
        self.assertEqual(rows["Headache"]["SUBJECT_N"], 1)
        self.assertEqual(rows["Headache"]["PCT"], 50)
        self.assertEqual(rows["Any event"]["SUBJECT_N"], 1)
        self.assertEqual(sum(row["SUBJECT_N"] for key, row in rows.items() if key != "Any event"), 2)

    def test_zero_event_arm_stays_in_report(self):
        rows = [row for row in self.result()["ae_incidence.csv"] if row["ARM"] == "Placebo"]
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(row["SUBJECT_N"] == 0 and row["PCT"] == 0 for row in rows))

    def test_no_events_is_valid(self):
        self.events = []
        self.assertTrue(all(row["SUBJECT_N"] == 0 for row in self.result()["ae_incidence.csv"]))

    def test_exact_duplicate_removed(self):
        before = self.result()
        self.events.append(copy.deepcopy(self.events[0]))
        after = self.result()
        self.assertEqual(before["ae_incidence.csv"], after["ae_incidence.csv"])
        qc = {row["METRIC"]: row["VALUE"] for row in after["qc_summary.csv"]}
        self.assertEqual(qc["exact_duplicate_ae_rows_removed"], 1)

    def test_conflicting_duplicate_rejected(self):
        bad = dict(self.events[0], SEVERITY="Severe")
        self.events.append(bad)
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            self.result()

    def test_missing_age_not_imputed(self):
        row = self.result()["demographics.csv"][0]
        self.assertEqual((row["N"], row["AGE_N"], row["AGE_MISSING"], row["AGE_MEAN"], row["AGE_SD"]), (2, 1, 1, 40, ""))

    def test_all_ages_missing_supported(self):
        self.subjects[0]["AGE"] = ""
        row = self.result()["demographics.csv"][0]
        self.assertEqual((row["AGE_N"], row["AGE_MISSING"], row["AGE_MEAN"], row["AGE_MIN"]), (0, 2, "", ""))

    def test_sample_standard_deviation(self):
        row = self.result()["demographics.csv"][1]
        self.assertAlmostEqual(row["AGE_SD"], 7.0711, places=4)

    def test_duplicate_subject_rejected(self):
        self.subjects.append(copy.deepcopy(self.subjects[0]))
        with self.assertRaisesRegex(ValueError, "duplicate subject"):
            self.result()

    def test_invalid_and_missing_ids_rejected(self):
        for value in ("", "S1", "S001XYZ", "A001"):
            with self.subTest(value=value):
                subjects = copy.deepcopy(self.subjects)
                subjects[0]["SUBJID"] = value
                with self.assertRaises(ValueError):
                    analyze(subjects, self.events)

    def test_unknown_event_subject_rejected(self):
        self.events[0]["SUBJID"] = "S999"
        with self.assertRaisesRegex(ValueError, "unknown"):
            self.result()

    def test_invalid_age_rejected(self):
        for value in ("bad", "NaN", "inf", "17", "91", "30.5"):
            with self.subTest(value=value):
                subjects = copy.deepcopy(self.subjects)
                subjects[0]["AGE"] = value
                with self.assertRaisesRegex(ValueError, "age"):
                    analyze(subjects, self.events)

    def test_invalid_event_sequence_rejected(self):
        for value in ("", "0", "1.5", "NaN"):
            with self.subTest(value=value):
                events = copy.deepcopy(self.events)
                events[0]["AESEQ"] = value
                with self.assertRaisesRegex(ValueError, "sequence"):
                    analyze(self.subjects, events)

    def test_invalid_categories_rejected(self):
        for field, value in (("ARM", "Unknown"), ("SEX", ""), ("DOSED", "yes")):
            with self.subTest(field=field):
                subjects = copy.deepcopy(self.subjects)
                subjects[0][field] = value
                with self.assertRaisesRegex(ValueError, "category"):
                    analyze(subjects, self.events)

    def test_arm_with_no_dosed_subjects_rejected(self):
        for subject in self.subjects:
            if subject["ARM"] == "Placebo":
                subject["DOSED"] = "N"
        with self.assertRaisesRegex(ValueError, "at least one dosed"):
            self.result()

    def test_csv_schema_and_short_row_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            for content in ("wrong,header\na,b\n", "SUBJID,ARM,AGE,SEX,DOSED\nS001,Active,40,F\n"):
                path.write_text(content)
                with self.assertRaises(ValueError):
                    read_csv(path, SUBJECT_FIELDS)

    def test_export_comparison_detects_changed_count(self):
        result = self.result()
        with tempfile.TemporaryDirectory() as tmp:
            for name, rows in result.items():
                write_csv(Path(tmp) / name, rows)
            self.assertEqual(compare_directory(result, tmp), [])
            changed = copy.deepcopy(result["ae_incidence.csv"])
            changed[0]["SUBJECT_N"] += 1
            write_csv(Path(tmp) / "ae_incidence.csv", changed)
            self.assertTrue(any("SUBJECT_N" in failure for failure in compare_directory(result, tmp)))


if __name__ == "__main__":
    unittest.main()
