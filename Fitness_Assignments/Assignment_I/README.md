# Assignment I - Fitness Session Analyzer

**Option:** A  
Student name: Manoj Poudel  


## About the program

The program checks simulated fitness readings, compares them with personal
references and explains each session's result. The unchanged instructor
generator provides five scenarios: resting, moderate activity, high activity,
recovery and poor quality. The program decides the result from the readings.

## How to run

Use Python 3.9 or newer. No extra packages are needed. Inside `Assignment_I`, run:

```bash
python main.py
python tests.py
```


## Design

| Class | Purpose |
| --- | --- |
| `ReferenceProfile` | Personal reference values. |
| `Participant` | A person and their profile. |
| `Observation` | One reading. |
| `Session` | A participant and their readings. |

Composition means one object contains another: a participant contains a profile,
and a session contains observations. I chose composition instead of inheritance
and overriding because these are "has a" relationships.

For encapsulation, `_observations` is controlled through `add_observation()`.
The `observations` property returns a separate sorted list. `from_record()` class
methods check dictionaries and create objects.

The `analyzer/` modules are `models.py` for classes, `validation.py` for checks,
`analysis.py` for calculations and `reports.py` for console output.
`sample_data.py` builds sessions; `main.py` runs them.
Functions include `summarize()`, `is_recovering()`, `classify()` and
`compare_reference()`. Data uses lists and dictionaries; results are dictionaries.

## Checks and classification

Missing values, bad numbers, NaN, infinity and duplicate timestamps are rejected.
Limits are 30-220 bpm for heart rate, 30-120 bpm for its reference, 20-45 C for
temperature, non-negative skin response, and 0-1 for activity and quality.
Boundaries are included. Quality below 0.50 is rejected. Timestamps must be
non-negative integers. These limits are project assumptions.

Rules are checked in this order:

1. Insufficient data: fewer than three usable readings.
2. Recovery: activity-phase means reach reference heart rate plus 30 bpm and
   0.40 activity. Ending means drop by at least 15 bpm and 0.20 activity;
   both signals also fall near the end.
3. Resting: mean heart rate is at most reference plus 15 bpm and activity at most 0.20.
4. High activity: mean heart rate is at least reference plus 60 bpm or activity at least 0.75.
5. Otherwise, moderate activity.

The ending is the final third, rounded down, with at least one reading.
Earlier readings form the activity phase. The final half, with at least three
readings, is split into two groups; both later averages must be lower for recovery.
Skin response and temperature are compared but do not decide the category.
No activity reference is provided by the generator.

## Results and limitations

The five sample sessions give the five required results. The console shows
counts, means, minimums, maximums, reference differences and reasons.

```text
Completed: 5 participants, 48 usable observations, 12 rejected observations, 5 sessions.
```

All ten tests passed. 

