"""Save CSV and text reports."""

import csv
from pathlib import Path

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


def save_reports(output_folder, results, log):
    folder = Path(output_folder)
    folder.mkdir(parents=True, exist_ok=True)
    summary_path = folder / "analysis_summary.csv"
    report_path = folder / "analysis_report.txt"
    rejected_path = folder / "rejected_records.txt"
    columns = ["session_id", "participant_id", "participant_name", "usable_observations", "rejected_observations", "classification", "reason"]
    for field in FIELDS:
        for statistic in ("mean", "min", "max"):
            columns.append(f"{field}_{statistic}")
    reference_fields = ("heart_rate", "skin_response", "temperature", "activity_level")
    for field in reference_fields:
        columns.append(f"{field}_reference_difference")
    with open(summary_path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for result in results:
            row = {}
            for column in columns[:7]:
                row[column] = result[column]
            for field in FIELDS:
                for statistic, value in result["summaries"][field].items():
                    row[f"{field}_{statistic}"] = "" if value is None else round(value, 3)
            for field in reference_fields:
                value = result["reference_differences"].get(field)
                row[f"{field}_reference_difference"] = "" if value is None else round(value, 3)
            writer.writerow(row)
    with open(report_path, "w", encoding="utf-8", newline="") as stream:
        stream.write("SMART FITNESS SESSION ANALYZER\nSimulated data; not a medical assessment.\n\n")
        stream.write(f"Accepted profiles: {log.accepted_profiles}\nAccepted observations: {log.accepted_observations}\nRejected rows: {len(log.rejections)}\nFile errors: {len(log.file_errors)}\n\n")
        if not results:
            stream.write("No identifiable sessions could be processed.\n")
        for result in results:
            stream.write(describe_result(result) + "\n\n")
    with open(rejected_path, "w", encoding="utf-8", newline="") as stream:
        stream.write("REJECTED RECORDS\n")
        if not log.rejections:
            stream.write("No rejected rows.\n")
        for row in log.rejections:
            stream.write(f"source={row['source']} | row={row['row']} | field={row['field']} | reason={row['reason']}\n")
        stream.write("\nFILE ERRORS\n")
        if not log.file_errors:
            stream.write("No file errors.\n")
        for error in log.file_errors:
            stream.write(f"source={error['source']} | reason={error['reason']}\n")
    return [summary_path, report_path, rejected_path]
