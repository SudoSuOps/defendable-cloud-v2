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
    flight_sheet_id: Optional[str] = None
    lane: Optional[Lane] = None
    title: Optional[str] = Field(default=None, max_length=300)
    inputs: Dict[str, Any] = Field(default_factory=dict)


class EvidenceIn(BaseModel):
    kind: EvidenceKind = "note"
    label: str = Field(min_length=1, max_length=300)
    content: Optional[str] = None


class ApprovalIn(BaseModel):
    decision: Literal["approved", "rejected", "escalated"]
    note: Optional[str] = None


class CookRequestIn(BaseModel):
    dataset_id: str
    base_model: str = "swarm/curator-9b"


class RunnerClaimIn(BaseModel):
    runner: str = "rig"


class RunnerStatusIn(BaseModel):
    status: Literal["running", "claimed"] = "running"
    metrics: Dict[str, Any] = Field(default_factory=dict)


class RunnerCompleteIn(BaseModel):
    eval_after: float
    adapter_ref: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


class RunnerFailIn(BaseModel):
    error: str
