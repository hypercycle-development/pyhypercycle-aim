import json
from datetime import datetime, timezone
from pathlib import Path

# Write logs next to this file: aims/telemetry/aims_events.log
LOG_FILE = Path(__file__).resolve().parent / "aims_events.log"

def log_event(payload):
    # Make sure it's JSON-serializable
    event = dict(payload) if isinstance(payload, dict) else {"payload": str(payload)}
    event["ts"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Ensure folder exists (should already)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Append one JSON object per line
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    # Keep printing too (nice while developing)
    print("TELEMETRY:", event)
