# workout-cli

A terminal workout coach: Claude picks the exercises, you do them, it remembers.

## What it does

Run `workout` and Claude streams a short, no-fluff session — 3 to 5 exercises,
10-15 minutes total — picked to vary muscle groups you haven't hit in your
recent sessions. You reply `done` or `skip` after each one; `quit` ends the
session early. When it wraps up, the session (exercises completed, exercises
skipped, duration) is logged to `~/.workout_history.json`, and the next
session's prompt is built from your last 10 logged sessions so the coach
doesn't repeat itself.

## Features

- Streams Claude's responses live to the terminal (`client.messages.stream`)
- Builds its prompt from your actual history — no history file yet, no problem,
  it just starts fresh
- Tracks completed vs. skipped exercises per session, with duration
- `workout --history` / `workout history` / `workout -H` to review past sessions
- Handles `Ctrl-C` / EOF mid-session by logging whatever was completed instead
  of losing the session

## Install

```bash
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
```

Requires Python 3.10+ and an Anthropic API key.

## Usage

```bash
workout            # start a session
workout --history   # show your last 10 sessions
```

Example session:

```
--- Workout starting ---

**Exercise: Push-ups**
Keep your core tight, elbows at 45°.
3 sets of 10.

> done

**Exercise: Bodyweight squats**
...
> quit

Session logged: 1 done, 0 skipped.
```

## How it works

`workout.py` is a single module: `build_prompt()` turns recent history into a
system prompt instructing Claude to run the session turn-by-turn and end with
a `SESSION_COMPLETE` marker followed by a JSON summary line, which
`_extract_summary()` parses back out. `save_session()` appends the result to
`~/.workout_history.json`. No server, no database — the whole app is one file
plus the JSON log.

## Tests

```bash
pip install pytest
pytest
```

Tests cover history loading/truncation, session persistence, prompt
construction, and summary parsing (`tests/test_workout.py`).
