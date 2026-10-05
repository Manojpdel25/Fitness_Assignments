"""Format readable console results."""

from .analysis import FIELDS


def show_number(value):
    if value is None:
        return "N/A"
    return f"{value:.3f}"


def describe_result(result):
    participant = result["participant_id"]
    if result["participant_name"] != participant:
        participant = f"{result['participant_name']} ({participant})"
    lines = [
        f"Session: {result['session_id']}",
        f"Participant: {participant}",
        f"Classification: {result['classification']}",
        f"Usable observations: {result['usable_observations']}",
        f"Rejected observations: {result['rejected_observations']}",
        f"Reason: {result['reason']}",
    ]
    for field in FIELDS:
        summary = result["summaries"][field]
        lines.append(f"  {field}: mean={show_number(summary['mean'])}, min={show_number(summary['min'])}, max={show_number(summary['max'])}")
    for field, difference in result["reference_differences"].items():
        lines.append(f"  {field} mean minus reference: {difference:+.3f}")
    return "\n".join(lines)


