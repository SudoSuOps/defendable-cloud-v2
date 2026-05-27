from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

Lane = Literal["agent", "dataset", "compute", "other"]
EvidenceKind = Literal["file", "note", "url", "observation", "tool_output", "model_output", "log"]


class HealthOut(BaseModel):
    ok: bool
    service: str
    version: str
    db: bool
    storage: bool
    email_configured: bool
    bucket: str


class MagicRequestIn(BaseModel):
    email: str


class MagicVerifyIn(BaseModel):
    token: str


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class RunIn(BaseModel):
    project_id: str
    lane: Lane = "agent"
    title: str = Field(min_length=1, max_length=300)
    inputs: Dict[str, Any] = Field(default_factory=dict)


class EvidenceIn(BaseModel):
    kind: EvidenceKind = "note"
    label: str = Field(min_length=1, max_length=300)
    content: Optional[str] = None


class ApprovalIn(BaseModel):
    decision: Literal["approved", "rejected", "escalated"]
    note: Optional[str] = None
