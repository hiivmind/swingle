from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELEGATE = ROOT / "skills" / "delegate" / "SKILL.md"
SETUP = ROOT / "skills" / "swingle-setup" / "SKILL.md"
SDD = ROOT / "skills" / "sdd" / "SKILL.md"

RETIRED = (
    "verified-version",
    "models.yaml",
    "verification-protocol",
    "controllers/",
    "core/liveness",
    "require-verified-version",
    "native-subagents",
    "superpowers availability",
    "worktree dispatch",
)


def test_delegate_uses_live_cli_contract_and_ledger():
    text = DELEGATE.read_text()
    for required in (
        "executable", "--help", "live", "contract", "ledger",
        "python3 <root>/scripts/swingle", "Path(<this SKILL.md>).parents[2]",
        "Tier policy", "outcome",
        "disable", "providers_by_contract", "default_provider",
        "explicit user model", ".swingle/delegate/ledger.md", "--path",
        "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED",
    ):
        assert required in text
    for retired in RETIRED:
        assert retired not in text


def test_setup_manages_only_swingle_owned_state():
    text = SETUP.read_text()
    for required in (
        "scripts/swingle config", "scripts/swingle ledger", "executable presence",
        "Path(<this SKILL.md>).parents[2]", "does not inspect provider auth",
        "Explicit migration", "SWINGLE_MODELS", "user model directory",
    ):
        assert required in text
    for retired in RETIRED + ("provider version",):
        assert retired not in text


def test_sdd_is_only_a_delegate_wrapper():
    text = SDD.read_text()
    assert "subagent-driven-development" in text
    assert "swingle-delegate" in text
    assert "sole authority" in text
    assert "SDD run-ledger path" in text
    for retired in RETIRED + ("Step 0", "self-reaping", "models.yaml"):
        assert retired not in text


def test_delegate_names_every_contract():
    text = DELEGATE.read_text()
    for contract in sorted((ROOT / "contracts").glob("*-contract.md")):
        role = contract.stem.removesuffix("-contract")
        assert role in text, f"{contract.name} not named in delegate SKILL.md step 1"


def test_contracts_are_transport_neutral():
    for path in sorted((ROOT / "contracts").glob("*.md")):
        text = path.read_text()
        assert "provider pack" not in text.lower()
        assert "report-transport" not in text
        assert "sandboxed providers" not in text.lower()


def test_removed_skill_and_controller_surfaces_are_absent():
    assert not (ROOT / "skills" / "swingle-verify").exists()
    assert not (ROOT / "controllers").exists()
    assert not (ROOT / "core").exists()
