

import unittest

from analyzer.analysis import analyze_session
from analyzer.models import Observation, Participant, Session
from analyzer.validation import InvalidIdentifierError, InvalidRecordError, check_id, read_number
from option_a_fitness.data_generator import available_scenarios, generate_fitness_data


class FitnessTests(unittest.TestCase):
    def setUp(self):
        self.profile, self.readings = generate_fitness_data(scenario="moderate_activity", seed=42)
        self.person = Participant.from_record(self.profile)

    def make_session(self, measurements):
        session = Session("FIT-2026-100", self.person)
        for timestamp, (heart_rate, activity) in enumerate(measurements):
            record = self.readings[0].copy()
            record.update({"timestamp": timestamp, "heart_rate": heart_rate, "activity_level": activity})
            session.add_observation(Observation.from_record(record))
        return session

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
