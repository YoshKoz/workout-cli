import json
import time
from pathlib import Path

import pytest

import workout


@pytest.fixture(autouse=True)
def clean_history(tmp_path, monkeypatch):
    """Redirect history file to a temp path for each test."""
    fake_path = tmp_path / ".workout_history.json"
    monkeypatch.setattr(workout, "HISTORY_PATH", fake_path)
    yield fake_path


def test_load_history_missing_file():
    result = workout.load_history()
    assert result == []


def test_load_history_returns_last_10(clean_history):
    sessions = [{"date": f"2026-05-{i:02d}", "exercises": [], "skipped": [], "duration_minutes": 10} for i in range(1, 16)]
    clean_history.write_text(json.dumps({"sessions": sessions}))
    result = workout.load_history()
    assert len(result) == 10
    assert result[0]["date"] == "2026-05-06"  # oldest of last 10


def test_save_session_creates_file(clean_history):
    start = time.time() - 600  # 10 minutes ago
    workout.save_session(["pushups", "squats"], ["burpees"], start)
    data = json.loads(clean_history.read_text())
    assert len(data["sessions"]) == 1
    session = data["sessions"][0]
    assert session["exercises"] == ["pushups", "squats"]
    assert session["skipped"] == ["burpees"]
    assert session["duration_minutes"] == pytest.approx(10, abs=1)


def test_save_session_appends(clean_history):
    existing = {"sessions": [{"date": "2026-05-01", "exercises": ["plank"], "skipped": [], "duration_minutes": 5}]}
    clean_history.write_text(json.dumps(existing))
    start = time.time() - 300
    workout.save_session(["squats"], [], start)
    data = json.loads(clean_history.read_text())
    assert len(data["sessions"]) == 2


def test_build_prompt_no_history():
    prompt = workout.build_prompt([])
    assert "no previous sessions" in prompt.lower() or "first time" in prompt.lower() or "fresh start" in prompt.lower()


def test_build_prompt_includes_recent_exercises():
    history = [
        {"date": "2026-05-20", "exercises": ["pushups", "squats"], "skipped": [], "duration_minutes": 10},
        {"date": "2026-05-21", "exercises": ["plank", "lunges"], "skipped": ["burpees"], "duration_minutes": 8},
    ]
    prompt = workout.build_prompt(history)
    assert "pushups" in prompt
    assert "squats" in prompt
    assert "plank" in prompt
    assert "lunges" in prompt
