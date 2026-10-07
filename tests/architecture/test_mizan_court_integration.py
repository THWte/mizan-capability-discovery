import json
from pathlib import Path

SCHEMA=Path("contracts/court-session-artifact-v1/schema.json")
DOC=Path("docs/architecture/MIZAN_COURT_INTEGRATION_CONTRACT_V1.md")

def test_three_delegation_modes_are_contractual():
    s=json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert s["properties"]["delegation_mode"]["enum"]==[
        "MIZAN_HANDLES","TOGETHER","OWNER_HANDLES"
    ]

def test_every_step_requires_artifact_identity_and_epistemic_class():
    s=json.loads(SCHEMA.read_text(encoding="utf-8"))
    req=set(s["required"])
    assert {"artifact_id","session_id","step_index","delegation_mode","epistemic_class","sha256"} <= req

def test_simulation_is_not_an_accepted_fact_state():
    s=json.loads(SCHEMA.read_text(encoding="utf-8"))
    states=set(s["properties"]["epistemic_class"]["enum"])
    assert "ACCEPTED_FACT" not in states
    assert "SIMULATION_OUTPUT" in states

def test_contract_is_cumulative_and_public_repo_safe():
    text=DOC.read_text(encoding="utf-8")
    assert "Cumulative construction without deletion" in text
    assert "Real case files" in text
    assert "MUST NOT be committed" in text
