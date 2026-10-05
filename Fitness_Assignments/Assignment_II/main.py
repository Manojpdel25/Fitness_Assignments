

import argparse
import csv
import sys

from analyzer.analysis import analyze_session
from analyzer.files import LoadLog, load_profiles, load_sessions
from analyzer.reports import describe_result, save_reports


def run(arguments=None):
    parser = argparse.ArgumentParser(description="Analyze simulated fitness sessions.")
    parser.add_argument("--profiles", default="data/participants.csv")
    parser.add_argument("--sessions", nargs="+", default=["data/fitness_sessions.csv", "data/fitness_sessions_invalid.csv"])
    parser.add_argument("--output", default="output")
    parser.add_argument("--demo", action="store_true", help="Use the instructor's generator directly")
    options = parser.parse_args(arguments)

    if options.demo:
        from sample_data import build_demo
        sessions, log = build_demo()
    else:
        log = LoadLog()
        participants = load_profiles(options.profiles, log)
        sessions = load_sessions(options.sessions, participants, log)

    results = []
    for session_id in sorted(sessions):
        results.append(analyze_session(sessions[session_id]))
    try:
        reports = save_reports(options.output, results, log)
    except PermissionError as error:
        print(f"Permission denied while writing reports: {error}", file=sys.stderr)
        return 1
    except (OSError, csv.Error) as error:
        print(f"Could not save the reports: {error}", file=sys.stderr)
        return 1

    for result in results:
        print(describe_result(result))
        print()
    print(f"Completed: {log.accepted_profiles} accepted profiles, {log.accepted_observations} accepted observations, {len(log.rejections)} rejected rows, {len(results)} sessions.")
    for error in log.file_errors:
        print(f"Input error: {error['source']}: {error['reason']}", file=sys.stderr)
    for path in reports:
        print(f"Created: {path}")
    if log.file_errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
