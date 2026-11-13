"""Gap check: what is missing before this system can go live at its tier.

A *blocker* must be fixed (or formally accepted by the approver) before go-live.
A *warning* should be fixed or explained.
DPDP references are to sections of the Digital Personal Data Protection Act, 2023.
This is guidance for a review, not legal advice.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .form import System, lang_names
from .tiering import tier

L, M, H = 1, 2, 3
NEVER = 4  # use as blocker_from for gaps that are only ever warnings


@dataclass(frozen=True)
class Gap:
    id: str
    severity: str  # "blocker" or "warning"
    area: str
    message: str
    fix: str

    def to_dict(self) -> dict:
        return asdict(self)


def _gap(found: list, t: int, gid: str, blocker_from: int, area: str, message: str, fix: str, warn_from: int = 1):
    """Add a gap that is a blocker at tier ``blocker_from`` and above, a warning from ``warn_from``."""
    if t >= blocker_from:
        found.append(Gap(gid, "blocker", area, message, fix))
    elif t >= warn_from:
        found.append(Gap(gid, "warning", area, message, fix))


def check(s: System) -> list[Gap]:
    t = tier(s)
    g: list[Gap] = []
    # Ownership
    if not s.incident_owner.strip():
        _gap(g, t, "OPS-OWNER", L, "Operations", "No incident owner is named.",
             "Name the person who is called when this system causes harm.")

    # Data protection
    if s.personal_data:
        if s.lawful_basis == "none-recorded":
            _gap(g, t, "DPDP-BASIS", L, "DPDP", "No lawful basis is recorded for using personal data (DPDP s.4, s.6, s.7).",
                 "Record whether you rely on consent or a legitimate use, for this specific purpose.")
        if not s.notice_covers_ai:
            _gap(g, t, "DPDP-NOTICE", M, "DPDP", "The notice to people does not cover this AI use (DPDP s.5).",
                 "Update the notice in plain language, in the languages your users read.")
        if s.retention_days is None:
            _gap(g, t, "DPDP-RETENTION", M, "DPDP", "No retention period is set for personal data (DPDP s.8(7)).",
                 "Set how long data, logs and embeddings are kept, and delete them after.")
        if s.stores and not s.erasure_tested:
            _gap(g, t, "DPDP-ERASURE", M, "DPDP",
                 f"Erasure has not been tested across: {', '.join(s.stores)} (DPDP s.12).",
                 "Test that one person's data can be found and deleted in every store, and keep the evidence.")
        if "logs" in s.stores and not s.logs_masked:
            _gap(g, t, "DPDP-LOGS", H, "DPDP", "Prompt and output logs keep personal data unmasked.",
                 "Mask identifiers before logging, or keep logs only as long as needed.", warn_from=M)
        if "children" in s.data_kinds:
            _gap(g, t, "DPDP-CHILDREN", L, "DPDP",
                 "Children's data is used (DPDP s.9: verifiable parental consent; no tracking, behavioural monitoring "
                 "or targeted advertising directed at children).",
                 "Confirm parental consent and switch off tracking and targeting for children.")
        if s.vendor_trains_on_data in ("yes", "unknown"):
            _gap(g, t, "VENDOR-TRAINING", L, "Vendor",
                 f"The model vendor may train on your data (answer: {s.vendor_trains_on_data}).",
                 "Get a written no-training commitment, or stop sending personal data to this vendor.")
        if "unknown" in (s.inference_location, s.storage_location):
            _gap(g, t, "DATA-LOCATION", H, "Data location", "You do not know where inference or storage happens.",
                 "Ask the vendor in writing where prompts are processed and stored.", warn_from=M)
        if "outside-india" in (s.inference_location, s.storage_location) and s.sensitive_kinds:
            _gap(g, t, "DATA-TRANSFER", NEVER, "Data location",
                 "Sensitive data leaves India (DPDP s.16, plus any sector rules such as RBI, SEBI or IRDAI directions).",
                 "Confirm with legal that this transfer is allowed for your sector and data.")

    # Quality across languages
    untested = [l for l in s.languages if l not in s.quality_tested_languages]
    if untested:
        _gap(g, t, "QUALITY-LANG", M, "Quality", f"Quality is not tested in: {lang_names(untested)}.",
             "Build a test set in every supported language and measure accuracy in each.")

    # Security
    if not s.guardrails and s.audience in ("customers", "public"):
        _gap(g, t, "SEC-GUARDRAILS", M, "Security", "No input or output guardrails for a customer-facing system.",
             "Write the domain limits in plain words and enforce them, with a test showing they work.")
    if not s.injection_tested:
        _gap(g, t, "SEC-INJECTION", M, "Security", "Prompt-injection testing has not been done.",
             "Test injection, including instructions hidden in retrieved documents.", warn_from=L)
    elif t >= H:
        missing = [l for l in s.languages if l not in s.injection_tested_languages]
        if missing:
            _gap(g, t, "SEC-INJECTION-LANG", H, "Security", f"Injection is not tested in: {lang_names(missing)}.",
                 "Run injection and data-leak tests in each supported language and script (for example with Kavach-Eval).")
    if not s.red_team:
        _gap(g, t, "SEC-REDTEAM", H, "Security", "No red-team exercise has been done.",
             "Run a red-team exercise and fix or formally accept the findings.", warn_from=H)

    # Agents that take actions
    if s.role == "acts":
        if s.human_approval == "none":
            _gap(g, t, "AGENT-APPROVAL", L, "Agent actions", "The agent takes actions with no human approval at any level.",
                 "Require human approval above a limit (maker-checker), at least for money and messages.")
        if s.action_limit_inr is None:
            _gap(g, t, "AGENT-LIMIT", L, "Agent actions", "No written limit on the agent's actions.",
                 "Set a per-action and daily limit, in rupees where money moves.")
        if not s.kill_switch:
            _gap(g, t, "AGENT-KILL", L, "Agent actions", "No tested kill switch for the agent.",
                 "Add a kill switch and test that it stops all actions.")

    # Operations
    if not s.monitoring:
        _gap(g, t, "OPS-MONITOR", M, "Operations", "No monitoring of usage, quality, cost and errors.",
             "Set up a dashboard and alerts before go-live.")
    if not s.fallback_to_human and s.audience in ("customers", "public"):
        _gap(g, t, "OPS-HANDOVER", H, "Operations", "No hand-over to a person when the system cannot help.",
             "Add a clear route to a human, and say plainly when the AI cannot help.", warn_from=M)
    if not s.rollback_plan:
        _gap(g, t, "OPS-ROLLBACK", H, "Operations", "No tested rollback plan.", "Write and test a rollback plan.",
             warn_from=M)
    if s.monthly_budget_inr is None:
        _gap(g, t, "OPS-BUDGET", NEVER, "Operations", "No monthly cost budget is agreed.",
             "Agree a monthly budget and a cost alert.", warn_from=M)
    return g


def blockers(gaps: list[Gap]) -> list[Gap]:
    return [x for x in gaps if x.severity == "blocker"]
