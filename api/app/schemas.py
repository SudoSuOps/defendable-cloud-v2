from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

Lane = Literal["agent", "dataset", "compute", "other"]
EvidenceKind = Literal["file", "note", "url", "observation", "tool_output", "model_output", "log"]
CapabilityTier = Literal["edge", "small", "mid", "frontier"]


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
    agent_profile_id: Optional[str] = None
    lane: Optional[Lane] = None
    title: Optional[str] = Field(default=None, max_length=300)
    inputs: Dict[str, Any] = Field(default_factory=dict)


class AgentProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    harness: Optional[str] = Field(default=None, max_length=80)
    harness_version: Optional[str] = Field(default=None, max_length=40)
    model: Optional[str] = Field(default=None, max_length=120)
    model_provider: Optional[str] = Field(default=None, max_length=80)
    served_by: Optional[str] = Field(default=None, max_length=40)
    runtime_host: Optional[str] = Field(default=None, max_length=120)
    runtime_os: Optional[str] = Field(default=None, max_length=80)
    runtime_hardware: Optional[str] = Field(default=None, max_length=160)
    tools: list[str] = Field(default_factory=list)
    context_window: Optional[int] = None
    capability_tier: Optional[CapabilityTier] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


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
