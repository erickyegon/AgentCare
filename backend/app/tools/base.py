"""Shared tool result type."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Uniform structured result returned by every tool.

    ``ok``      — whether the tool succeeded.
    ``message`` — human-readable summary (surfaced in the agent trace).
    ``data``    — structured payload (ids, records) used by downstream agents.
    """

    ok: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "message": self.message, "data": self.data}
