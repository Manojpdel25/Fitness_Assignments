"""Calculate summaries and use simple rules to describe a session."""

from statistics import mean

FIELDS = ("heart_rate", "skin_response", "temperature", "activity_level", "signal_quality")


def summarize(values):
    if len(values) == 0:
        return {"mean": None, "min": None, "max": None}
    return {"mean": mean(values), "min": min(values), "max": max(values)}


def average_reading(observations, field):
    values = []
    for observation in observations:
        values.append(getattr(observation, field))
    return mean(values)


def is_recovering(observations, reference):
    if len(observations) < 3:
        return False
    section_size = max(1, len(observations) // 3)
    # The activity phase can include a warm-up before the heart rate rises.
    activity_phase = observations[:-section_size]
    ending = observations[-section_size:]
    active_hr = average_reading(activity_phase, "heart_rate")
    end_hr = average_reading(ending, "heart_rate")
    active_movement = average_reading(activity_phase, "activity_level")
    end_activity = average_reading(ending, "activity_level")

    # Also compare the two halves of the final segment. This allows small
    # fluctuations while checking that the readings fall near the end.
    recent = observations[-max(3, len(observations) // 2):]
    middle = len(recent) // 2
    recent_start = recent[:middle]
    recent_end = recent[middle:]
    heart_rate_falling = average_reading(recent_end, "heart_rate") < average_reading(recent_start, "heart_rate")
    activity_falling = average_reading(recent_end, "activity_level") < average_reading(recent_start, "activity_level")

    return (
        active_hr >= reference.heart_rate + 30
        and active_movement >= 0.40
        and active_hr - end_hr >= 15
        and active_movement - end_activity >= 0.20
        and heart_rate_falling
        and activity_falling
    )


def classify(observations, summaries, reference):
    if len(observations) < 3:
        return "insufficient data", "At least three usable observations are needed."
    if is_recovering(observations, reference):
        return "recovering", "Heart rate and activity are elevated during the activity phase, are lower at the end and fall in the final segment."
    heart_rate_difference = summaries["heart_rate"]["mean"] - reference.heart_rate
    activity = summaries["activity_level"]["mean"]
    if heart_rate_difference <= 15 and activity <= 0.20:
        return "resting", "Mean heart rate is at most 15 bpm above reference and activity is at most 0.20."
    if heart_rate_difference >= 60 or activity >= 0.75:
        return "high activity", "Mean heart rate is at least 60 bpm above reference or activity is at least 0.75."
    return "moderate activity", "There is enough usable data and the resting, high-activity and recovery rules do not apply."


def compare_reference(summaries, reference):
    baseline = {
        "heart_rate": reference.heart_rate,
        "skin_response": reference.skin_response,
        "temperature": reference.temperature,
        "activity_level": reference.activity,
    }
    differences = {}
    for field, value in baseline.items():
        average = summaries[field]["mean"]
        if value is not None and average is not None:
            differences[field] = average - value
    return differences


def analyze_session(session):
    observations = session.observations
    summaries = {}
    for field in FIELDS:
        values = []
        for observation in observations:
            values.append(getattr(observation, field))
        summaries[field] = summarize(values)
    classification, reason = classify(observations, summaries, session.participant.reference)
    return {
        "session_id": session.session_id,
        "participant_id": session.participant.participant_id,
        "participant_name": session.participant.name,
        "usable_observations": len(observations),
        "rejected_observations": session.rejected_count,
        "classification": classification,
        "reason": reason,
        "summaries": summaries,
        "reference_differences": compare_reference(summaries, session.participant.reference),
    }
