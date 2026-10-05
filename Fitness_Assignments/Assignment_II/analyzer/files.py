"""Read profiles and sessions from CSV files."""

import csv
from pathlib import Path

from .models import Observation, Participant, Session
from .validation import InvalidIdentifierError, InvalidRecordError, check_id, check_row, required

PROFILE_FIELDS = ("participant_id", "baseline_heart_rate", "baseline_skin_response", "baseline_temperature")
OLDER_PROFILE_FIELDS = ("participant_id", "resting_heart_rate", "reference_skin_response", "reference_temperature")
SESSION_FIELDS = ("participant_id", "session_id", "timestamp", "heart_rate", "skin_response", "temperature", "activity_level", "signal_quality")


class LoadLog:
    def __init__(self):
        self.accepted_profiles = 0
        self.accepted_observations = 0
        self.rejections = []
        self.file_errors = []

    def reject(self, source, row, error):
        self.rejections.append({"source": str(source), "row": row, "field": error.field, "reason": error.reason})

    def file_error(self, source, reason):
        self.file_errors.append({"source": str(source), "reason": reason})


def read_rows(path, required_fields, log):
    path = Path(path)
    records = []
    try:
        with open(path, encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            headers = reader.fieldnames
            if not headers:
                log.file_error(path, "missing CSV header")
                return records
            if len(headers) != len(set(headers)):
                log.file_error(path, "duplicate column names")
                return records
            if required_fields == PROFILE_FIELDS and "resting_heart_rate" in headers and "baseline_heart_rate" not in headers:
                required_fields = OLDER_PROFILE_FIELDS
            for field in required_fields:
                if field not in headers:
                    log.file_error(path, f"required column is missing: {field}")
                    return records
            for row in reader:
                records.append((reader.line_num, row))
    except FileNotFoundError:
        log.file_error(path, "file not found")
    except PermissionError:
        log.file_error(path, "permission denied")
    except UnicodeError as error:
        log.file_error(path, f"cannot read UTF-8 text: {error}")
    except csv.Error as error:
        log.file_error(path, f"CSV error near line {reader.line_num}: {error}")
    except OSError as error:
        log.file_error(path, f"cannot read file: {error}")
    return records


def load_profiles(path, log):
    participants = {}
    for row_number, record in read_rows(path, PROFILE_FIELDS, log):
        try:
            check_row(record)
            participant = Participant.from_record(record)
            if participant.participant_id in participants:
                raise InvalidRecordError("participant_id", "duplicate participant profile")
            participants[participant.participant_id] = participant
            log.accepted_profiles += 1
        except InvalidIdentifierError as error:
            log.reject(path, row_number, error)
        except InvalidRecordError as error:
            log.reject(path, row_number, error)
    return participants


def add_session_row(record, participants, sessions, log, source, row_number, check_shape=True):
    session = None
    try:
        participant_id = check_id(required(record, "participant_id"), "participant_id")
        session_id = check_id(required(record, "session_id"), "session_id")
        try:
            participant = participants[participant_id]
        except KeyError as error:
            raise InvalidRecordError("participant_id", f"unknown participant: {participant_id}") from error
        if session_id not in sessions:
            sessions[session_id] = Session(session_id, participant)
        session = sessions[session_id]
        if session.participant.participant_id != participant_id:
            session = None
            raise InvalidRecordError("participant_id", "session already belongs to another participant")
        if check_shape:
            check_row(record)
        session.add_observation(Observation.from_record(record))
        log.accepted_observations += 1
    except InvalidIdentifierError as error:
        log.reject(source, row_number, error)
    except InvalidRecordError as error:
        log.reject(source, row_number, error)
        if session is not None:
            session.reject_observation()


def load_sessions(paths, participants, log):
    sessions = {}
    for path in paths:
        for row_number, record in read_rows(path, SESSION_FIELDS, log):
            add_session_row(record, participants, sessions, log, path, row_number)
    return sessions
