"""Local API-key generation for provider integrations."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path


class APIKeyStore:
    def __init__(self, path: str | Path = ".constellation/api_keys.json") -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def create(self, label: str) -> str:
        token = f"cst_{secrets.token_urlsafe(24)}"
        records = self._read()
        records.append(
            {
                "label": label,
                "hash": hashlib.sha256(token.encode()).hexdigest(),
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )
        self.path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return token

    def _read(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))
