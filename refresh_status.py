import json
from datetime import datetime, UTC
from pathlib import Path

STATUS_FILE = Path(__file__).resolve().parent / "refresh_status.json"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def read_refresh_status():
    if not STATUS_FILE.exists():
        return {
            "status": "unknown",
            "updated_at": None,
        }

    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        return {
            "status": "error",
            "updated_at": _now_iso(),
            "error": f"failed to read refresh status: {e}",
        }


def write_refresh_status(replace: bool = False, **data):
    payload = {} if replace else read_refresh_status()
    payload.update(data)
    payload["updated_at"] = _now_iso()

    STATUS_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
