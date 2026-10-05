"""Run these checks with: python tests.py"""

import contextlib
import csv
import io
import tempfile
import unittest
from pathlib import Path

from analyzer.analysis import analyze_session
from analyzer.files import LoadLog, PROFILE_FIELDS, SESSION_FIELDS, load_profiles, load_sessions
from analyzer.models import Observation, Participant, Session
from analyzer.reports import save_reports
from analyzer.validation import InvalidIdentifierError, InvalidRecordError, check_id, read_number
from main import run
from option_a_fitness.data_generator import available_scenarios, generate_fitness_data
from sample_data import build_demo, write_example_csvs


class FitnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.profile, self.readings = generate_fitness_data(scenario="moderate_activity", seed=42)
        self.person = Participant.from_record(self.profile)

    def make_session(self, measurements):
        session = Session("FIT-2026-100", self.person)
        for timestamp, (heart_rate, activity) in enumerate(measurements):
            record = self.readings[0].copy()
            record.update({"timestamp": timestamp, "heart_rate": heart_rate, "activity_level": activity})
            session.add_observation(Observation.from_record(record))
        return session

    def write_csv(self, filename, fields, rows):
        path = self.folder / filename
        with open(path, "w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_identifiers(self):
        self.assertEqual(check_id("P001", "participant_id"), "P001")
        self.assertEqual(check_id("FIT-2026-001", "session_id"), "FIT-2026-001")
        for value, field in [("P01", "participant_id"), ("P001extra", "participant_id"), ("P１２３", "participant_id"), ("FIT-26-001", "session_id"), ("prefixFIT-2026-001", "session_id")]:
            with self.subTest(value=value), self.assertRaises(InvalidIdentifierError):
                check_id(value, field)

    def test_missing_values_and_bad_numbers(self):
        for value in (None, "", "text", "nan", "inf", "-inf", -1, 221):
            with self.subTest(value=value), self.assertRaises(InvalidRecordError):
                read_number({"heart_rate": value}, "heart_rate", 30, 220)
        with self.assertRaises(InvalidRecordError):
            read_number({}, "heart_rate", 30, 220)

    def test_measurement_boundaries(self):
        record = {"timestamp": 0, "heart_rate": 30, "skin_response": 0, "temperature": 20, "activity_level": 0, "signal_quality": 0.50}
        Observation.from_record(record)
        Observation.from_record({**record, "heart_rate": 220, "temperature": 45, "activity_level": 1, "signal_quality": 1, "skin_response": 75})
        for field, value in [("heart_rate", 29.9), ("temperature", 45.1), ("skin_response", -1), ("activity_level", 1.1), ("signal_quality", 0.49), ("signal_quality", 1.1)]:
            with self.subTest(field=field), self.assertRaises(InvalidRecordError):
                Observation.from_record({**record, field: value})

    def test_timestamp_must_be_a_nonnegative_integer(self):
        self.assertEqual(Observation.from_record({**self.readings[0], "timestamp": 2000000000}).timestamp, 2000000000)
        for value in (-1, 1.5, "1.0", None, True):
            with self.subTest(value=value), self.assertRaises(InvalidRecordError):
                Observation.from_record({**self.readings[0], "timestamp": value})

    def test_minimum_usable_readings(self):
        for count in (0, 1, 2):
            result = analyze_session(self.make_session([(self.person.reference.heart_rate, 0.1)] * count))
            self.assertEqual(result["classification"], "insufficient data")
        result = analyze_session(self.make_session([(self.person.reference.heart_rate, 0.1)] * 3))
        self.assertEqual(result["classification"], "resting")

    def test_classification_boundaries(self):
        reference = self.person.reference.heart_rate
        cases = [
            ((reference + 15, 0.20), "resting"),
            ((reference + 15.1, 0.20), "moderate activity"),
            ((reference, 0.21), "moderate activity"),
            ((reference + 60, 0.40), "high activity"),
            ((reference + 59.9, 0.40), "moderate activity"),
            ((reference + 20, 0.75), "high activity"),
        ]
        for pair, expected in cases:
            with self.subTest(pair=pair):
                self.assertEqual(analyze_session(self.make_session([pair] * 3))["classification"], expected)

    def test_all_instructor_scenarios(self):
        expected = {"resting": "resting", "moderate_activity": "moderate activity", "high_activity": "high activity", "recovery": "recovering", "poor_quality": "insufficient data"}
        for scenario in available_scenarios():
            profile, readings = generate_fitness_data(scenario=scenario, seed=42, number_of_windows=10)
            session = Session("FIT-2026-001", Participant.from_record(profile))
            for record in readings:
                try:
                    session.add_observation(Observation.from_record(record))
                except InvalidRecordError:
                    session.reject_observation()
            with self.subTest(scenario=scenario):
                self.assertEqual(analyze_session(session)["classification"], expected[scenario])

    def test_recovery_needs_activity_and_an_ending_decline(self):
        self.assertEqual(analyze_session(self.make_session([(160, 0.8), (120, 0.5), (90, 0.1)]))["classification"], "recovering")
        self.assertNotEqual(analyze_session(self.make_session([(160, 0.8), (120, 0.8), (90, 0.8)]))["classification"], "recovering")
        rising_end = [(170, 0.8), (160, 0.7), (150, 0.6), (80, 0.2), (95, 0.1), (105, 0.0)]
        self.assertNotEqual(analyze_session(self.make_session(rising_end))["classification"], "recovering")

    def test_summaries_and_personal_references(self):
        session = self.make_session([(90, 0.4), (100, 0.4), (110, 0.4)])
        result = analyze_session(session)
        self.assertEqual(result["summaries"]["heart_rate"], {"mean": 100, "min": 90, "max": 110})
        self.assertEqual(result["reference_differences"]["heart_rate"], 100 - self.person.reference.heart_rate)
        self.assertNotIn("activity_level", result["reference_differences"])

    def test_sorted_readings_duplicates_and_protected_list(self):
        session = Session("FIT-2026-100", self.person)
        for timestamp in (2, 0, 1):
            session.add_observation(Observation.from_record({**self.readings[0], "timestamp": timestamp}))
        self.assertEqual([reading.timestamp for reading in session.observations], [0, 1, 2])
        session.observations.clear()
        self.assertEqual(len(session.observations), 3)
        with self.assertRaises(InvalidRecordError):
            session.add_observation(Observation.from_record(self.readings[0]))

    def test_csv_run_with_valid_and_invalid_files(self):
        write_example_csvs(self.folder)
        log = LoadLog()
        people = load_profiles(self.folder / "participants.csv", log)
        sessions = load_sessions([self.folder / "fitness_sessions.csv", self.folder / "fitness_sessions_invalid.csv"], people, log)
        self.assertEqual((len(people), len(sessions), log.accepted_observations, len(log.rejections)), (5, 6, 48, 24))
        self.assertEqual(log.file_errors, [])
        for rejected in log.rejections:
            self.assertEqual(set(rejected), {"source", "row", "field", "reason"})
            self.assertGreaterEqual(rejected["row"], 2)

    def test_official_assignment_two_files(self):
        data = Path(__file__).resolve().parent / "data"
        paths = [data / "participants.csv", data / "fitness_sessions.csv", data / "fitness_sessions_invalid.csv"]
        original = [path.read_bytes() for path in paths]
        log = LoadLog()
        people = load_profiles(paths[0], log)
        sessions = load_sessions(paths[1:], people, log)
        self.assertEqual((log.accepted_profiles, log.accepted_observations, len(log.rejections), len(sessions)), (3, 25, 15, 8))
        self.assertEqual(log.file_errors, [])
        expected = {
            "FIT-2026-001": "resting",
            "FIT-2026-002": "moderate activity",
            "FIT-2026-003": "high activity",
            "FIT-2026-004": "recovering",
            "FIT-2026-005": "insufficient data",
            "FIT-2026-101": "insufficient data",
            "FIT-2026-102": "insufficient data",
            "FIT-2026-103": "insufficient data",
        }
        for session_id, classification in expected.items():
            with self.subTest(session_id=session_id):
                self.assertEqual(analyze_session(sessions[session_id])["classification"], classification)
        self.assertEqual(original, [path.read_bytes() for path in paths])

    def test_missing_file_does_not_stop_the_next_file(self):
        write_example_csvs(self.folder)
        log = LoadLog()
        people = load_profiles(self.folder / "participants.csv", log)
        sessions = load_sessions([self.folder / "missing.csv", self.folder / "fitness_sessions.csv"], people, log)
        self.assertEqual(len(log.file_errors), 1)
        self.assertEqual(len(sessions), 5)
        self.assertEqual(log.accepted_observations, 48)
        self.assertEqual(load_profiles(self.folder / "missing_profile.csv", log), {})

    def test_wrong_row_lengths_and_csv_errors(self):
        person = {self.person.participant_id: self.person}
        path = self.folder / "rows.csv"
        row = {**self.readings[0], "participant_id": "P001", "session_id": "FIT-2026-001"}
        values = [row[field] for field in SESSION_FIELDS]
        with open(path, "w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(SESSION_FIELDS)
            writer.writerow(values + ["extra"])
            writer.writerow(values[:-1])
            writer.writerow(values)
        log = LoadLog()
        load_sessions([path], person, log)
        self.assertEqual(log.accepted_observations, 1)
        self.assertEqual(len(log.rejections), 2)
        path.write_text(",".join(SESSION_FIELDS) + '\n"unfinished\n', encoding="utf-8")
        load_sessions([path], person, log)
        self.assertIn("CSV error", log.file_errors[0]["reason"])

    def test_bad_headers_profiles_and_unknown_people(self):
        for text in ("", "participant_id,name\nP001,Name\n", "participant_id,participant_id\nP001,P001\n"):
            path = self.folder / "header.csv"
            path.write_text(text, encoding="utf-8")
            log = LoadLog()
            self.assertEqual(load_profiles(path, log), {})
            self.assertEqual(len(log.file_errors), 1)
        invalid = {**self.profile, "participant_id": "P002", "baseline_heart_rate": -1}
        path = self.write_csv("profiles.csv", PROFILE_FIELDS, [self.profile, self.profile, invalid])
        log = LoadLog()
        people = load_profiles(path, log)
        self.assertEqual(len(people), 1)
        self.assertEqual(len(log.rejections), 2)
        unknown = {**self.readings[0], "participant_id": "P999", "session_id": "FIT-2026-001"}
        path = self.write_csv("unknown.csv", SESSION_FIELDS, [unknown])
        self.assertEqual(load_sessions([path], people, log), {})
        self.assertIn("unknown participant", log.rejections[-1]["reason"])

    def test_reports_are_repeatable_and_include_insufficient_data(self):
        sessions, log = build_demo()
        results = []
        for session in sessions.values():
            results.append(analyze_session(session))
        paths = save_reports(self.folder / "reports", results, log)
        first = [path.read_bytes() for path in paths]
        save_reports(self.folder / "reports", results, log)
        self.assertEqual(first, [path.read_bytes() for path in paths])
        with open(paths[0], encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[-1]["heart_rate_mean"], "")
        self.assertIn("insufficient data", paths[1].read_text(encoding="utf-8"))
        self.assertIn("field=", paths[2].read_text(encoding="utf-8"))

    def test_command_line_status_and_input_files_are_unchanged(self):
        write_example_csvs(self.folder)
        inputs = sorted(self.folder.glob("*.csv"))
        original = [path.read_bytes() for path in inputs]
        arguments = ["--profiles", str(self.folder / "participants.csv"), "--sessions", str(self.folder / "fitness_sessions.csv"), str(self.folder / "fitness_sessions_invalid.csv"), "--output", str(self.folder / "reports")]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(run(arguments), 0)
            self.assertEqual(run(["--profiles", str(self.folder / "missing.csv"), "--sessions", str(self.folder / "fitness_sessions.csv"), "--output", str(self.folder / "errors")]), 1)
        self.assertEqual(original, [path.read_bytes() for path in inputs])

    def test_generated_examples_are_repeatable_and_not_overwritten(self):
        first = self.folder / "first"
        second = self.folder / "second"
        write_example_csvs(first)
        write_example_csvs(second)
        for path in first.glob("*.csv"):
            self.assertEqual(path.read_bytes(), (second / path.name).read_bytes())
        with self.assertRaises(FileExistsError):
            write_example_csvs(first)


if __name__ == "__main__":
    unittest.main(verbosity=2)
