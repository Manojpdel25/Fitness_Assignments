# Assignment II - Fitness CSV Analyzer

**Option:** A  
Student name: Manoj Poudel  


## About the program

This continues Assignment I. It reads participant and session CSVs, checks rows,
analyzes sessions and saves reports. The three official CSVs in `data/` are
copied unchanged from `Assignment_II_Pack.zip`.

## How to run

Use Python 3.9 or newer. No extra packages are needed. Inside `Assignment_II`, run:

```bash
python main.py
python tests.py
```

Use `python3` if needed. 
```bash
git clone https://github.com/USERNAME/REPOSITORY.git
cd REPOSITORY
python main.py
```

The default run reads all three official files. To choose paths:

```bash
python main.py --profiles data/participants.csv --sessions data/fitness_sessions.csv data/fitness_sessions_invalid.csv --output output
```

## Design

`ReferenceProfile` stores references, `Participant` stores a person and profile,
`Observation` stores a reading, and `Session` groups readings. `LoadLog` records
counts and errors. Composition connects these objects. `_observations` is
controlled through a method and property. `from_record()` class methods create
validated objects. Composition fits these relationships better than a parent
class with overriding. The custom exceptions use inheritance.

The `analyzer/` package has five modules: `models.py`, `validation.py`, `files.py`,
`analysis.py` and `reports.py`. They handle classes, checks, CSV loading,
calculations and output. Lists and dictionaries hold data and results.
`pathlib` handles paths. Only the Python standard library is used.

## Validation

The loader uses `csv`, UTF-8 and `with open(..., newline="")`. Values become
numbers. Regex full matches check IDs such as `P001` and `FIT-2026-001`.
Missing fields, wrong row lengths, unknown people and duplicate readings are
rejected. Limits are 30-220 bpm for heart rate, 30-120 bpm for its reference,
20-45 C for temperature, non-negative skin response, and 0-1 for activity/quality.
Boundaries are included. Quality below 0.50, NaN and infinity are rejected.
Timestamps must be non-negative integers.

`InvalidRecordError` and `InvalidIdentifierError` are raised and handled.
Targeted handlers cover missing files, permissions, conversion, missing keys,
CSV errors and writing errors. Rejections record filename, row, field and the
first problem found. The next row or file is attempted when safe.

## Analysis and reports

The same Assignment I rules apply: fewer than three usable readings means
insufficient data; recovery is checked next; resting means heart rate at most
reference plus 15 bpm and activity at most 0.20; high activity means heart rate
at least reference plus 60 bpm or activity at least 0.75. Otherwise, moderate.

Recovery compares activity-phase means with the final third, rounded down with
at least one reading. Activity-phase means must reach reference plus 30 bpm and
0.40 activity; ending means must drop by at least 15 bpm and 0.20 activity.
The final half, with at least three readings, is split into two groups, and both
later averages must be lower. Skin response and temperature are also summarized
and compared with references.

The output folder is created automatically. Repeated runs replace:

- `analysis_summary.csv`: one row per session with counts and statistics.
- `analysis_report.txt`: results and reasons.
- `rejected_records.txt`: rejected rows and file errors.

Inputs are only read. File/output errors return 1; a completed run returns 0.

## Results and limitations

Official sessions 001-004 give resting, moderate, high activity and recovery.
Session 005 and sessions 101-103 have insufficient data.

```text
Completed: 3 accepted profiles, 25 accepted observations, 15 rejected rows, 8 sessions.
```

All 18 tests passed, including valid/invalid, missing-file and boundary cases.



