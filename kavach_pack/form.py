"""The system form: one TOML (or JSON) file that describes an AI system."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

AUDIENCES = ("internal-team", "employees", "customers", "public")
ROLES = ("drafts", "recommends", "decides", "acts")
DOMAINS = ("productivity", "operations", "hr", "sales", "finance", "health", "legal", "safety", "credit", "eligibility")
REVERSIBILITY = ("easy", "manual", "hard")
APPROVAL = ("none", "above-limit", "all")
LOCATIONS = ("india", "outside-india", "unknown")
YES_NO_UNKNOWN = ("yes", "no", "unknown")
BASES = ("consent", "legitimate-use", "none-recorded")
DATA_KINDS = ("contact", "financial", "government-id", "health", "biometric", "children", "location", "other")
SENSITIVE_KINDS = ("financial", "government-id", "health", "biometric", "children")
STORES = ("vector-store", "cache", "logs", "agent-memory", "fine-tune")
STATUSES = ("idea", "pilot", "live")
LANG_NAMES = {"en": "English", "hi": "Hindi", "hinglish": "Hinglish", "or": "Odia", "ta": "Tamil", "te": "Telugu",
              "bn": "Bengali", "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam", "pa": "Punjabi",
              "as": "Assamese", "ur": "Urdu"}


def lang_names(codes) -> str:
    """Language codes as readable names, e.g. ["en", "or"] -> "English, Odia"."""
    return ", ".join(LANG_NAMES.get(c, c) for c in codes)


class FormError(ValueError):
    """The form has a missing or invalid field. The message says which one and how to fix it."""


@dataclass
class System:
    # [system]
    name: str
    owner: str
    purpose: str
    status: str = "idea"
    audience: str = "employees"
    users: int = 0
    vulnerable_users: bool = False
    # [model]
    provider: str = ""
    model: str = ""
    inference_location: str = "unknown"
    storage_location: str = "unknown"
    vendor_trains_on_data: str = "unknown"
    vendor_retention_days: int | None = None
    # [data]
    personal_data: bool = False
    data_kinds: list[str] = field(default_factory=list)
    lawful_basis: str = "none-recorded"
    notice_covers_ai: bool = False
    retention_days: int | None = None
    stores: list[str] = field(default_factory=list)
    erasure_tested: bool = False
    logs_masked: bool = False
    # [behaviour]
    role: str = "drafts"
    domain: str = "productivity"
    actions: list[str] = field(default_factory=list)
    reversibility: str = "easy"
    human_approval: str = "all"
    action_limit_inr: int | None = None
    # [languages]
    languages: list[str] = field(default_factory=lambda: ["en"])
    quality_tested_languages: list[str] = field(default_factory=list)
    # [controls]
    guardrails: bool = False
    injection_tested: bool = False
    injection_tested_languages: list[str] = field(default_factory=list)
    red_team: bool = False
    kill_switch: bool = False
    monitoring: bool = False
    fallback_to_human: bool = False
    rollback_plan: bool = False
    incident_owner: str = ""
    monthly_budget_inr: int | None = None

    @property
    def slug(self) -> str:
        return "".join(c if c.isalnum() else "-" for c in self.name.lower()).strip("-") or "ai-system"

    @property
    def sensitive_kinds(self) -> list[str]:
        return [k for k in self.data_kinds if k in SENSITIVE_KINDS]


_SECTIONS = {
    "system": ("name", "owner", "purpose", "status", "audience", "users", "vulnerable_users"),
    "model": ("provider", "model", "inference_location", "storage_location", "vendor_trains_on_data", "vendor_retention_days"),
    "data": ("personal_data", "data_kinds", "lawful_basis", "notice_covers_ai", "retention_days", "stores",
             "erasure_tested", "logs_masked"),
    "behaviour": ("role", "domain", "actions", "reversibility", "human_approval", "action_limit_inr"),
    "languages": ("languages", "quality_tested_languages"),
    "controls": ("guardrails", "injection_tested", "injection_tested_languages", "red_team", "kill_switch", "monitoring",
                 "fallback_to_human", "rollback_plan", "incident_owner", "monthly_budget_inr"),
}
_CHOICES = {"status": STATUSES, "audience": AUDIENCES, "role": ROLES, "domain": DOMAINS, "reversibility": REVERSIBILITY,
            "human_approval": APPROVAL, "inference_location": LOCATIONS, "storage_location": LOCATIONS,
            "vendor_trains_on_data": YES_NO_UNKNOWN, "lawful_basis": BASES}
_LIST_CHOICES = {"data_kinds": DATA_KINDS, "stores": STORES}
_REQUIRED = ("name", "owner", "purpose")


def from_dict(raw: dict) -> System:
    flat: dict = {}
    for section, fields_ in _SECTIONS.items():
        block = raw.get(section, {})
        if not isinstance(block, dict):
            raise FormError(f"[{section}] must be a section of fields")
        unknown = set(block) - set(fields_)
        if unknown:
            raise FormError(f"[{section}] has unknown field(s): {', '.join(sorted(unknown))}. Allowed: {', '.join(fields_)}")
        flat.update(block)
    unknown_sections = set(raw) - set(_SECTIONS)
    if unknown_sections:
        raise FormError(f"unknown section(s): {', '.join(sorted(unknown_sections))}. Allowed: {', '.join(_SECTIONS)}")
    for key in _REQUIRED:
        if not str(flat.get(key, "")).strip():
            raise FormError(f"[system] {key} is required")
    for key, allowed in _CHOICES.items():
        if key in flat and flat[key] not in allowed:
            raise FormError(f"{key} = {flat[key]!r} is not allowed. Choose one of: {', '.join(allowed)}")
    for key, allowed in _LIST_CHOICES.items():
        bad = [v for v in flat.get(key, []) if v not in allowed]
        if bad:
            raise FormError(f"{key} has unknown value(s) {bad}. Choose from: {', '.join(allowed)}")
    if flat.get("data_kinds") and not flat.get("personal_data", False):
        raise FormError("data_kinds is filled in but personal_data is false. Set personal_data = true")
    return System(**flat)


def load(path: str | Path) -> System:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    try:
        raw = json.loads(text) if path.suffix == ".json" else tomllib.loads(text)
    except (tomllib.TOMLDecodeError, json.JSONDecodeError) as e:
        raise FormError(f"{path.name} could not be read: {e}") from e
    return from_dict(raw)
