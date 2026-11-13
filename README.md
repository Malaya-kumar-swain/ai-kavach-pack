# AI-Kavach-Pack

**Describe an AI system once. Get its governance pack in one command.**

You fill in one short form about an AI system: who uses it, what it does, what data it touches, which model runs it and which controls exist. AI-Kavach-Pack gives you back the documents a risk committee, a DPO and a board ask for, plus a gap check that can block a release in CI.

[![PyPI](https://img.shields.io/pypi/v/ai-kavach-pack)](https://pypi.org/project/ai-kavach-pack/) ![python](https://img.shields.io/badge/python-3.11%2B-blue) ![license](https://img.shields.io/badge/license-Apache--2.0-green) ![deps](https://img.shields.io/badge/core%20dependencies-0-brightgreen)

*Kavach* (कवच) means "armour" in Hindi.

## Why

Most teams in India do AI governance in spreadsheets and slide decks, rewritten for every system and out of date by the next release. The paid platforms are built for large enterprises and mostly for EU and US rules. Open-source tools exist for single documents, such as model cards, but not for the whole pack an Indian review needs: risk tier, DPDP duties, vendor questions on data location and training, and agent limits.

AI-Kavach-Pack turns the [AI Governance Playbook](https://github.com/Malaya-kumar-swain/ai-governance-playbook) into a working tool, so the review starts from facts about the system instead of a blank template.

## 30-second demo

```bash
pip install ai-kavach-pack
kavach-pack demo
```

This builds packs for three fictional systems:

| Example system | Tier | Blockers | Why it is in that tier |
|---|---|---|---|
| Meeting Summary Drafts | Low | 0 | Internal team, drafts only, no personal data |
| Loan Document Reader | High | 4 | Financial and ID data in a credit decision |
| Bank Support Assistant | High | 10 | Customer-facing agent that blocks cards, in three languages |

## Use it

```bash
kavach-pack new system.toml          # a blank form with every option explained
kavach-pack build system.toml        # writes governance-pack/<system>/
kavach-pack check system.toml        # tier and gaps; exits 1 if there are blockers
```

`check` takes several forms at once, so a CI job can block a release when any AI system has unresolved blockers:

```bash
kavach-pack check ai-systems/*.toml
```

## What is in the pack

| File | What it holds |
|---|---|
| `00-summary.md` | One page for the approver: tier, main reasons, blockers, decision needed |
| `01-risk-tier.md` | Seven factors scored 1 to 3; the highest sets the tier |
| `02-system-card.md` | Purpose, users, model, data, languages, limits and controls |
| `03-dpdp-checklist.md` | DPDP duties for this system, with section numbers, and every place personal data can hide (embeddings, caches, logs, agent memory, fine-tunes) |
| `04-vendor-questions.md` | Questions for the model provider, with what you already know filled in |
| `05-pre-launch-checklist.md` | Only the lines that apply at this tier, ticked where the form says they are done |
| `06-incident-plan.md` | Severity 1 events specific to this system, first-hour and 72-hour steps |
| `07-approvals.md` | Who approves at this tier, with sign-off rows |
| `gaps.json` | Every gap as data, for CI and dashboards |

## How the tier is set

| Factor | Low (1) | Medium (2) | High (3) |
|---|---|---|---|
| Who sees the output | Internal team | Employees | Customers or the public |
| What the AI does | Drafts | Recommends; a human decides | Decides or takes actions |
| Personal data | None | Ordinary | Financial, ID, health, biometric or children's data |
| Domain | Productivity | Operations, HR, sales | Finance, health, legal, safety, credit, eligibility |
| Reversibility | Easy | Manual effort | Hard |
| Scale | Under 100 users | Up to 100,000 | Over 100,000, or vulnerable users |
| Languages | One, tested | Several | Several not tested, or none tested |

The highest factor wins: one high-risk factor makes the whole system high risk.

## What the gap check looks for

Examples: no lawful basis or notice for personal data, erasure not tested across every store, unmasked logs, a vendor that may train on your data, unknown data location, quality or injection not tested in every supported language, no red-team for high-tier systems, agents without limits, human approval or a kill switch, and no incident owner, monitoring or rollback plan.

A **blocker** must be fixed, or formally accepted by the approver, before go-live. A **warning** should be fixed or explained. The same gap can be a warning at Low tier and a blocker at High tier.

## The form

```toml
[system]
name = "Bank Support Assistant"
owner = "Head of Customer Service"
purpose = "Answers customer questions and can block a card or raise a dispute"
audience = "customers"
users = 2000000

[data]
personal_data = true
data_kinds = ["contact", "financial", "government-id"]
stores = ["vector-store", "cache", "logs", "agent-memory"]

[behaviour]
role = "acts"
domain = "finance"
actions = ["block card", "raise dispute"]
human_approval = "above-limit"
action_limit_inr = 25000

[languages]
languages = ["en", "hi", "or"]
quality_tested_languages = ["en", "hi"]
```

Run `kavach-pack new` for the full form, with every allowed value. JSON works too.

## Limits

- **Not legal advice.** DPDP section numbers refer to the Digital Personal Data Protection Act, 2023. Confirm current obligations, the DPDP Rules timeline and sector rules (RBI, SEBI, IRDAI and others) with your legal team.
- The pack is only as good as the form. Ticked lines still need evidence.
- Sector-specific rule sets, such as RBI or SEBI guidance, are not built in yet. They are on the roadmap and will be added only after checking the official documents.

## Related

- [AI Governance Playbook](https://github.com/Malaya-kumar-swain/ai-governance-playbook): the templates this tool is built on
- [Kavach-Eval](https://github.com/Malaya-kumar-swain/kavach-eval): injection and data-leak tests in Indian languages
- [Agent-Pariksha](https://github.com/Malaya-kumar-swain/agent-pariksha): reliability tests for AI agents that take actions
- [Vismriti](https://github.com/Malaya-kumar-swain/vismriti): DPDP consent and erasure for RAG and agents
- [Nakli-Data](https://github.com/Malaya-kumar-swain/nakli-data): safe fake Indian personal data for testing

## License

Apache-2.0
