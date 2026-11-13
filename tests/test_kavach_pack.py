import json
from importlib import resources
from pathlib import Path

import pytest

from kavach_pack import FormError, blockers, build, check, factors, from_dict, load, tier
from kavach_pack.__main__ import main

EXAMPLES = Path(str(resources.files("kavach_pack").joinpath("examples")))


def minimal(**sections):
    raw = {"system": {"name": "Test system", "owner": "Owner", "purpose": "Testing", "audience": "internal-team",
                      "users": 10},
           "languages": {"languages": ["en"], "quality_tested_languages": ["en"]},
           "controls": {"incident_owner": "On-call", "injection_tested": True, "monitoring": True}}
    for name, values in sections.items():
        raw.setdefault(name, {}).update(values)
    return from_dict(raw)


def test_low_tier_internal_drafting_tool_has_no_blockers():
    s = minimal()
    assert tier(s) == 1
    assert blockers(check(s)) == []


def test_one_high_factor_makes_the_whole_system_high():
    assert tier(minimal(behaviour={"domain": "credit"})) == 3
    assert tier(minimal(system={"audience": "customers"})) == 3
    assert tier(minimal(data={"personal_data": True, "data_kinds": ["government-id"],
                              "lawful_basis": "consent"})) == 3
    assert tier(minimal(system={"vulnerable_users": True})) == 3
    assert tier(minimal(behaviour={"role": "recommends"})) == 2


def test_language_factor():
    one = minimal()
    assert [f for f in factors(one) if f.name == "Languages"][0].score == 1
    three_untested = minimal(languages={"languages": ["en", "hi", "or"], "quality_tested_languages": ["en"]})
    lang = [f for f in factors(three_untested) if f.name == "Languages"][0]
    assert lang.score == 3 and "Hindi, Odia" in lang.reason


def test_agent_without_controls_is_blocked_at_any_tier():
    s = minimal(behaviour={"role": "acts", "actions": ["send email"], "human_approval": "none"})
    ids = {g.id for g in blockers(check(s))}
    assert {"AGENT-APPROVAL", "AGENT-LIMIT", "AGENT-KILL"} <= ids


def test_personal_data_without_basis_is_a_blocker_and_children_flagged():
    s = minimal(data={"personal_data": True, "data_kinds": ["children"]})
    ids = {g.id: g for g in check(s)}
    assert ids["DPDP-BASIS"].severity == "blocker"
    assert ids["DPDP-CHILDREN"].severity == "blocker"
    assert "s.9" in ids["DPDP-CHILDREN"].message


def test_vendor_training_unknown_is_flagged_only_with_personal_data():
    assert "VENDOR-TRAINING" not in {g.id for g in check(minimal())}
    s = minimal(data={"personal_data": True, "data_kinds": ["contact"], "lawful_basis": "consent"})
    assert "VENDOR-TRAINING" in {g.id for g in check(s)}


def test_high_tier_needs_injection_tests_in_every_language():
    s = minimal(system={"audience": "customers"}, languages={"languages": ["en", "hi"], "quality_tested_languages": ["en", "hi"]},
                controls={"injection_tested_languages": ["en"], "guardrails": True, "red_team": True,
                          "fallback_to_human": True, "rollback_plan": True})
    gap = {g.id: g for g in check(s)}["SEC-INJECTION-LANG"]
    assert gap.severity == "blocker" and "Hindi" in gap.message


def test_warnings_never_block():
    s = minimal(system={"audience": "employees", "users": 500})
    assert tier(s) == 2
    assert all(g.severity == "warning" for g in check(s) if g.id == "OPS-BUDGET")


def test_form_errors_are_clear():
    with pytest.raises(FormError, match="name is required"):
        from_dict({"system": {"owner": "x", "purpose": "y"}})
    with pytest.raises(FormError, match="audience"):
        from_dict({"system": {"name": "a", "owner": "b", "purpose": "c", "audience": "everyone"}})
    with pytest.raises(FormError, match="unknown field"):
        from_dict({"system": {"name": "a", "owner": "b", "purpose": "c", "colour": "blue"}})
    with pytest.raises(FormError, match="unknown section"):
        from_dict({"system": {"name": "a", "owner": "b", "purpose": "c"}, "extra": {}})
    with pytest.raises(FormError, match="personal_data"):
        from_dict({"system": {"name": "a", "owner": "b", "purpose": "c"}, "data": {"data_kinds": ["contact"]}})


def test_examples_load_and_build(tmp_path):
    results = {}
    for form in sorted(EXAMPLES.glob("*.toml")):
        s = load(form)
        folder = build(s, tmp_path)
        files = sorted(p.name for p in folder.iterdir())
        assert files == ["00-summary.md", "01-risk-tier.md", "02-system-card.md", "03-dpdp-checklist.md",
                         "04-vendor-questions.md", "05-pre-launch-checklist.md", "06-incident-plan.md",
                         "07-approvals.md", "gaps.json"]
        data = json.loads((folder / "gaps.json").read_text())
        results[s.name] = (data["tier"], data["blockers"])
        for md in folder.glob("*.md"):
            assert "not legal advice" in md.read_text()
    assert results["Meeting Summary Drafts"] == ("Low", 0)
    assert results["Bank Support Assistant"][0] == "High" and results["Bank Support Assistant"][1] > 0


def test_json_form_works(tmp_path):
    form = tmp_path / "s.json"
    form.write_text(json.dumps({"system": {"name": "J", "owner": "o", "purpose": "p"}}))
    assert load(form).name == "J"


def test_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["new", "system.toml"]) == 0
    assert main(["new", "system.toml"]) == 2  # never overwrites
    assert main(["build", "system.toml", "--out", "pack"]) == 0
    assert (tmp_path / "pack" / "name-of-the-ai-system" / "00-summary.md").exists()
    assert main(["check", str(EXAMPLES / "meeting-summary.toml")]) == 0
    assert main(["check", str(EXAMPLES / "bank-support-assistant.toml")]) == 1
    assert main(["demo"]) == 0
    bad = tmp_path / "bad.toml"
    bad.write_text("[system]\nname = 'x'\n")
    assert main(["check", str(bad)]) == 2
    assert "Form problem" in capsys.readouterr().err
