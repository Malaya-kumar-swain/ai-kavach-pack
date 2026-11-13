"""Risk tier: score seven factors 1 to 3; the highest factor sets the tier.

Follows the ai-governance-playbook risk-tiering template: one high-risk factor makes the
whole system high risk.
"""

from __future__ import annotations

from dataclasses import dataclass

from .form import System, lang_names

TIER_NAMES = {1: "Low", 2: "Medium", 3: "High"}


@dataclass(frozen=True)
class Factor:
    name: str
    score: int
    reason: str


def factors(s: System) -> list[Factor]:
    out = []
    aud = {"internal-team": 1, "employees": 2, "customers": 3, "public": 3}[s.audience]
    out.append(Factor("Who sees the output", aud, s.audience.replace("-", " ").capitalize()))

    role = {"drafts": 1, "recommends": 2, "decides": 3, "acts": 3}[s.role]
    what = {"drafts": "drafts for a human to edit", "recommends": "recommends; a human decides",
            "decides": "decides on its own", "acts": "takes actions: " + (", ".join(s.actions) or "not listed")}[s.role]
    out.append(Factor("What the AI does", role, what.capitalize()))

    if not s.personal_data:
        out.append(Factor("Personal data", 1, "No personal data"))
    elif s.sensitive_kinds:
        out.append(Factor("Personal data", 3, "Sensitive data: " + ", ".join(s.sensitive_kinds)))
    else:
        out.append(Factor("Personal data", 2, "Ordinary personal data: " + (", ".join(s.data_kinds) or "not listed")))

    dom = 1 if s.domain == "productivity" else 2 if s.domain in ("operations", "hr", "sales") else 3
    out.append(Factor("Domain", dom, s.domain.capitalize()))

    rev = {"easy": 1, "manual": 2, "hard": 3}[s.reversibility]
    out.append(Factor("Reversibility", rev, f"Undoing a mistake is {s.reversibility}"))

    if s.vulnerable_users:
        out.append(Factor("Scale", 3, f"Vulnerable users included ({s.users:,} users)"))
    else:
        scale = 1 if s.users < 100 else 2 if s.users <= 100_000 else 3
        out.append(Factor("Scale", scale, f"About {s.users:,} users"))

    langs = list(dict.fromkeys(s.languages))
    untested = [l for l in langs if l not in s.quality_tested_languages]
    if len(langs) == 1 and not untested:
        lang = (1, f"One language ({lang_names(langs)}), tested")
    elif not untested:
        lang = (2, f"{len(langs)} languages, all tested")
    elif len(langs) >= 3 or len(untested) == len(langs):
        lang = (3, f"{len(langs)} language(s); not tested: {lang_names(untested)}")
    else:
        lang = (2, f"{len(langs)} languages; not tested: {lang_names(untested)}")
    out.append(Factor("Languages", *lang))
    return out


def tier(s: System) -> int:
    return max(f.score for f in factors(s))
