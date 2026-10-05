"""Check the values before using them in the analysis."""

import math
import re


class InvalidRecordError(ValueError):
    def __init__(self, field, reason):
        self.field = field
        self.reason = reason
        super().__init__(f"{field}: {reason}")


class InvalidIdentifierError(InvalidRecordError):
    """Raised when a participant or session ID has the wrong format."""


def required(record, field):
    try:
        value = record[field]
    except KeyError as error:
        raise InvalidRecordError(field, "field is missing") from error
    if value is None or str(value).strip() == "":
        raise InvalidRecordError(field, "value is missing")
    return str(value).strip()


def check_id(value, field):
    if field == "participant_id":
        pattern = r"P[0-9]{3}"
        expected = "P followed by three digits"
    else:
        pattern = r"FIT-[0-9]{4}-[0-9]{3}"
        expected = "FIT-YYYY-NNN"
    if re.fullmatch(pattern, value) is None:
        raise InvalidIdentifierError(field, f"expected {expected}; got {value!r}")
    return value


def read_number(record, field, minimum, maximum=None):
    value = required(record, field)
    try:
        result = float(value)
    except ValueError as error:
        raise InvalidRecordError(field, f"not a number: {value!r}") from error
    if not math.isfinite(result):
        raise InvalidRecordError(field, "NaN and infinity are not allowed")
    if result < minimum:
        raise InvalidRecordError(field, f"must be at least {minimum}")
    if maximum is not None and result > maximum:
        raise InvalidRecordError(field, f"must be at most {maximum}")
    return result


def read_timestamp(record):
    value = required(record, "timestamp")
    try:
        result = int(value)
    except ValueError as error:
        raise InvalidRecordError("timestamp", "must be a whole number") from error
    if result < 0:
        raise InvalidRecordError("timestamp", "cannot be negative")
    return result


def check_row(record):
    if None in record:
        raise InvalidRecordError("row", "more values than the CSV header")
    for value in record.values():
        if value is None:
            raise InvalidRecordError("row", "fewer values than the CSV header")
