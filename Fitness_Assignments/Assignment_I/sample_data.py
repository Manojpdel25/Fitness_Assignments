

from analyzer.models import Observation, Participant, Session
from analyzer.validation import InvalidRecordError
from option_a_fitness.data_generator import available_scenarios, generate_fitness_data


def build_sessions():
    sessions = []
    for index, scenario in enumerate(available_scenarios(), start=1):
        profile, readings = generate_fitness_data(
            participant_id=f"P{index:03d}",
            scenario=scenario,
            seed=41 + index,
            number_of_windows=12,
        )
        participant = Participant.from_record(profile)
        session = Session(f"FIT-2026-{index:03d}", participant)
        for record in readings:
            try:
                session.add_observation(Observation.from_record(record))
            except InvalidRecordError:
                session.reject_observation()
        sessions.append(session)
    return sessions
