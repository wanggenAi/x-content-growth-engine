"""Read secrets from environment or ignored private file; never log them."""
from __future__ import annotations
import os
from pathlib import Path

PRIVATE_DIR = Path("data/telegram")

def _private_env() -> dict[str, str]:
    path = PRIVATE_DIR / "credentials.env"
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values

def credentials(*, require_session: bool) -> tuple[int, str, str]:
    values = _private_env()
    def get(k: str) -> str:
        return os.environ.get(k) or values.get(k, "")
    try:
        api_id = int(get("TG_API_ID"))
    except ValueError as exc:
        raise RuntimeError("缺少 TG_API_ID；请参阅 telegram_research/README.md") from exc
    api_hash = get("TG_API_HASH")
    token = get("TG_STRING_SESSION")
    if not token and (PRIVATE_DIR / "session.txt").is_file():
        token = (PRIVATE_DIR / "session.txt").read_text(encoding="utf-8").strip()
    if not api_hash or (require_session and not token):
        raise RuntimeError("缺少 TG_API_HASH 或 TG_STRING_SESSION；先运行授权步骤")
    return api_id, api_hash, token
