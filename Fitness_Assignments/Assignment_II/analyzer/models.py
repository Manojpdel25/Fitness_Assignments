"""Classes for participants and their fitness readings."""

from .validation import InvalidRecordError, check_id, read_number, read_timestamp, required


class ReferenceProfile:
    def __init__(self, heart_rate, skin_response, temperature, activity=None):
        self.heart_rate = heart_rate
        self.skin_response = skin_response
        self.temperature = temperature
        self.activity = activity

    @classmethod
    def from_record(cls, record):
        if "baseline_heart_rate" in record:
            heart_field = "baseline_heart_rate"
            skin_field = "baseline_skin_response"
            temperature_field = "baseline_temperature"
        else:
            heart_field = "resting_heart_rate"
            skin_field = "reference_skin_response"
            temperature_field = "reference_temperature"
        activity = None
        if "reference_activity_level" in record:
            activity = read_number(record, "reference_activity_level", 0, 1)
        return cls(
            read_number(record, heart_field, 30, 120),
            read_number(record, skin_field, 0),
            read_number(record, temperature_field, 20, 45),
            activity,
        )


class Participant:
    def __init__(self, participant_id, name, reference):
        self.participant_id = participant_id
        self.name = name
        self.reference = reference

    @classmethod
    def from_record(cls, record):
        participant_id = check_id(required(record, "participant_id"), "participant_id")
        name = participant_id
        if "name" in record:
            name = required(record, "name")
        return cls(participant_id, name, ReferenceProfile.from_record(record))


class Observation:
    def __init__(self, timestamp, heart_rate, skin_response, temperature, activity_level, signal_quality):
        self.timestamp = timestamp
        self.heart_rate = heart_rate
        self.skin_response = skin_response
        self.temperature = temperature
        self.activity_level = activity_level
        self.signal_quality = signal_quality

    @classmethod
    def from_record(cls, record):
        observation = cls(
            read_timestamp(record),
            read_number(record, "heart_rate", 30, 220),
            read_number(record, "skin_response", 0),
            read_number(record, "temperature", 20, 45),
            read_number(record, "activity_level", 0, 1),
            read_number(record, "signal_quality", 0, 1),
        )
        if observation.signal_quality < 0.50:
            raise InvalidRecordError("signal_quality", "below usable quality of 0.50")
        return observation


class Session:
    def __init__(self, session_id, participant):
        self.session_id = check_id(session_id, "session_id")
        self.participant = participant
        self._observations = []
        self.rejected_count = 0

    def add_observation(self, observation):
        for previous in self._observations:
            if previous.timestamp == observation.timestamp:
                raise InvalidRecordError("timestamp", "duplicate timestamp in this session")
        self._observations.append(observation)

    @property
    def observations(self):
        # Return a separate list so callers cannot change the stored list.
        return sorted(self._observations, key=lambda observation: observation.timestamp)

    def reject_observation(self):
        self.rejected_count += 1
