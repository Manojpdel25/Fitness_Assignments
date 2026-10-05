

import argparse
import csv
from pathlib import Path

from analyzer.files import LoadLog, PROFILE_FIELDS, SESSION_FIELDS, add_session_row
from analyzer.models import Participant
from analyzer.validation import InvalidRecordError
from option_a_fitness.data_generator import available_scenarios, generate_fitness_data


def make_examples():
    profiles = []
    rows = []
    for index, scenario in enumerate(available_scenarios(), start=1):
        participant_id = f"P{index:03d}"
        session_id = f"FIT-2026-{index:03d}"
        profile, observations = generate_fitness_data(
            participant_id=participant_id,
            scenario=scenario,
            seed=41 + index,
            number_of_windows=12,
        )
        profiles.append(profile)
        for observation in observations:
            row = observation.copy()
            row["participant_id"] = participant_id
            row["session_id"] = session_id
            rows.append(row)

    # These extra invalid rows are our own test examples.
    changes = [
        {"participant_id": "P01"}, {"session_id": "FIT-26-001"},
        {"participant_id": "P999"}, {"heart_rate": "not-a-number"},
        {"heart_rate": -5}, {"temperature": 60}, {"skin_response": -1},
        {"activity_level": 1.5}, {"signal_quality": 0.1},
        {"heart_rate": ""}, {"heart_rate": "nan"}, {"timestamp": -1},
    ]
    invalid_rows = []
    for index, change in enumerate(changes):
        row = rows[0].copy()
        row["session_id"] = "FIT-2026-006"
        row["timestamp"] = 100 + index
        row.update(change)
        invalid_rows.append(row)
    return profiles, rows, invalid_rows


def build_demo():
    profiles, rows, _ = make_examples()
    participants = {}
    sessions = {}
    log = LoadLog()
    for row_number, record in enumerate(profiles, start=1):
        try:
            participant = Participant.from_record(record)
            participants[participant.participant_id] = participant
            log.accepted_profiles += 1
        except InvalidRecordError as error:
            log.reject("generated profiles", row_number, error)
    for row_number, record in enumerate(rows, start=1):
        add_session_row(record, participants, sessions, log, "generated observations", row_number, check_shape=False)
    return sessions, log


def write_example_csvs(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    profiles, rows, invalid_rows = make_examples()
    tables = [
        ("participants.csv", PROFILE_FIELDS, profiles),
        ("fitness_sessions.csv", SESSION_FIELDS, rows),
        ("fitness_sessions_invalid.csv", SESSION_FIELDS, invalid_rows),
    ]
    for filename, _, _ in tables:
        if (directory / filename).exists():
            raise FileExistsError(f"Will not overwrite {filename}; choose a new folder.")
    for filename, fields, records in tables:
        with open(directory / filename, "x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Write example CSV files in a new folder.")
    parser.add_argument("--directory", default="new_sample_data")
    options = parser.parse_args()
    try:
        write_example_csvs(options.directory)
    except (OSError, csv.Error) as error:
        parser.exit(1, f"Could not create example files: {error}\n")
    print(f"Created examples in {options.directory}.")
