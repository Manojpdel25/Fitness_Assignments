

from analyzer.analysis import analyze_session
from analyzer.reports import describe_result
from sample_data import build_sessions


def main():
    sessions = build_sessions()
    usable = 0
    rejected = 0
    for session in sessions:
        result = analyze_session(session)
        print(describe_result(result))
        print()
        usable += result["usable_observations"]
        rejected += result["rejected_observations"]
    print(f"Completed: {len(sessions)} participants, {usable} usable observations, {rejected} rejected observations, {len(sessions)} sessions.")


if __name__ == "__main__":
    main()
