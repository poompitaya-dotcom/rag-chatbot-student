"""Per-turn tracing: one JSON line per answered question in logs/turns.jsonl.

Each line is a *trace*: everything needed to explain an answer later -
what was asked, what was retrieved and how similar it was, which prompt,
knowledge base and models produced it, whether the policy refused, and
how long each stage took.

logs/ is in .gitignore: logs contain what real users typed, so they never
go into version control.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "turns.jsonl"


def log_turn(result, channel="cli"):
    """Append the trace of one rag_answer() result. Returns its trace id."""
    hits = result["hits"]
    record = {
        "trace_id": uuid.uuid4().hex[:12],
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "channel": channel,
        "question": result["question"],
        "answer": result["answer"],
        "refused": result["refused"],
        "top_similarity": round(hits[0]["similarity"], 3) if hits else None,
        "retrieved": [{"id": h["id"], "similarity": round(h["similarity"], 3)} for h in hits],
        "prompt_version": result["prompt_version"],
        "kb_version": result["kb_version"],
        "models": result["models"],
        "timings_ms": result["timings_ms"],
    }
    LOG_PATH.parent.mkdir(exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record["trace_id"]


def read_turns(path=LOG_PATH):
    """Return all logged traces, oldest first."""
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
