import anthropic
import json
import os
import sys
import time
from pathlib import Path

HISTORY_PATH = Path.home() / ".workout_history.json"


def load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    data = json.loads(HISTORY_PATH.read_text())
    sessions = data.get("sessions", [])
    return sessions[-10:]


def save_session(exercises: list[str], skipped: list[str], start_time: float) -> None:
    if HISTORY_PATH.exists():
        data = json.loads(HISTORY_PATH.read_text())
    else:
        data = {"sessions": []}
    duration = round((time.time() - start_time) / 60)
    data["sessions"].append({
        "date": time.strftime("%Y-%m-%d"),
        "exercises": exercises,
        "skipped": skipped,
        "duration_minutes": duration,
    })
    HISTORY_PATH.write_text(json.dumps(data, indent=2))


def build_prompt(history: list[dict]) -> str:
    if not history:
        history_text = "No previous sessions — this is their first workout."
    else:
        lines = []
        for s in history:
            done = ", ".join(s["exercises"]) if s["exercises"] else "none"
            skipped = ", ".join(s["skipped"]) if s["skipped"] else "none"
            lines.append(f"- {s['date']}: completed [{done}], skipped [{skipped}] ({s['duration_minutes']} min)")
        history_text = "\n".join(lines)

    return f"""You are a workout coach running a live step-by-step exercise session in the terminal.

Recent workout history:
{history_text}

Your job:
1. Pick 3-5 exercises the user hasn't done much recently. Vary the muscle groups. Keep it 10-15 minutes total.
2. Walk through ONE exercise at a time. Present each one clearly:

   **Exercise: [Name]**
   [One sentence on form]
   [Reps or duration — keep it achievable, user is often tired]

3. After presenting each exercise, STOP and wait. The user will reply:
   - "done" → move to the next exercise
   - "skip" → acknowledge briefly and move to next exercise
   - "quit" → end the session immediately

4. When all exercises are done (or user quits), output exactly this line and nothing else after it:
   SESSION_COMPLETE

5. After SESSION_COMPLETE, output ONLY this JSON on the next line (no extra text):
   {{"completed": ["exercise1", "exercise2"], "skipped": ["exercise3"]}}

Rules:
- Be brief. User has ADD. No pep talks, no long intros.
- Start immediately with the first exercise. No warmup speech.
- Keep energy positive but terse."""


def _stream_response(client, system_prompt: str, messages: list[dict], max_tokens: int) -> str:
    response_text = ""
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            response_text += text
    print()  # newline after streamed response
    return response_text


def _extract_summary(response_text: str) -> tuple[list[str], list[str]]:
    """Scan all lines after SESSION_COMPLETE for the first JSON object line."""
    lines = response_text.split("\n")
    past_complete = False
    for line in lines:
        if "SESSION_COMPLETE" in line:
            past_complete = True
            continue
        if past_complete and line.strip().startswith("{"):
            try:
                summary = json.loads(line.strip())
                completed = summary.get("completed") or []
                skipped = summary.get("skipped") or []
                return completed, skipped
            except json.JSONDecodeError:
                pass
    return [], []


def run_session() -> None:
    history = load_history()
    system_prompt = build_prompt(history)
    client = anthropic.Anthropic()

    messages: list[dict] = [{"role": "user", "content": "Start my workout."}]
    start_time = time.time()
    completed: list[str] = []
    skipped: list[str] = []

    print("\n--- Workout starting ---\n")

    try:
        while True:
            response_text = _stream_response(client, system_prompt, messages, max_tokens=1024)
            messages.append({"role": "assistant", "content": response_text})

            # Check if session ended
            if "SESSION_COMPLETE" in response_text:
                completed, skipped = _extract_summary(response_text)
                if not completed and not skipped and "SESSION_COMPLETE" in response_text:
                    print("\n(Note: could not parse exercise summary — session logged without exercise names.)")
                break

            user_input = input("\n> ").strip()
            if user_input.lower() == "quit":
                # Ask Claude to wrap up and extract summary
                messages.append({"role": "user", "content": user_input})
                response_text = _stream_response(client, system_prompt, messages, max_tokens=512)
                completed, skipped = _extract_summary(response_text)
                if not completed and not skipped and "SESSION_COMPLETE" in response_text:
                    print("\n(Note: could not parse exercise summary — session logged without exercise names.)")
                break

            messages.append({"role": "user", "content": user_input})

    except (KeyboardInterrupt, EOFError):
        print("\n\nInterrupted — saving progress.")

    save_session(completed, skipped, start_time)
    print(f"\nSession logged: {len(completed)} done, {len(skipped)} skipped.")


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)
    run_session()


if __name__ == "__main__":
    main()
