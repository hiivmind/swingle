import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "delegate" / "SKILL.md"
YAML = ROOT / "skills" / "delegate" / "agents" / "openai.yaml"
READER = ROOT / "contracts" / "reader-contract.md"

def _model_ids():
    """Every model id declared in any provider's models.md Resolvable table."""
    ids = set()
    for models in (ROOT / "providers").glob("*/models.md"):
        for line in models.read_text().splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # Tier | Lane | Priority | Model id | Status | ...
            if len(cells) >= 5 and cells[2].isdigit():
                ids.add(cells[3].strip("`"))
    return ids

def _pack_clis():
    """The validated cli name from every provider pack manifest."""
    clis = set()
    for pack in (ROOT / "providers").glob("*/pack.md"):
        m = re.search(r"^cli: (\S+)", pack.read_text(), re.M)
        if m:
            clis.add(m.group(1))
    return clis

def test_skill_exists_with_frontmatter():
    text = SKILL.read_text()
    assert text.startswith("---\n")
    front = text.split("---", 2)[1]
    assert re.search(r"^name: delegate$", front, re.M)
    assert re.search(r"^description: .{40,}", front, re.M)

def test_purity_no_model_ids_in_any_skill():
    ids = _model_ids()
    assert ids, "expected provider model tables to parse"
    for skill in (ROOT / "skills").glob("*/SKILL.md"):
        text = skill.read_text()
        leaked = {m for m in ids if m in text}
        assert not leaked, f"{skill}: model ids leaked: {leaked}"

def test_purity_no_cli_invocations_anywhere():
    # Invocation strings live in provider packs only. No line ANYWHERE in the skill
    # (fenced or prose) may be command-shaped for a pack cli: first token equal to a
    # cli name, followed by whitespace and an argument. Prose mentions like
    # "(codex/opencode/agy)" or "via codex" do not match.
    clis = _pack_clis()
    assert clis, "expected pack manifests to declare cli names"
    for line in SKILL.read_text().splitlines():
        stripped = line.strip()
        parts = stripped.split(None, 1)
        if len(parts) == 2 and parts[0] in clis:
            raise AssertionError(f"command-shaped cli line leaked into skill: {stripped}")

def test_superpowers_operational_independence():
    # Normative rule: no operational dependency or invocation. The skill NAMES
    # superpowers and its workspace exactly once each — in the negative disclaimer.
    text = SKILL.read_text()
    assert "no superpowers dependency" in text.lower()
    assert text.count("scripts/sdd-workspace") == 1
    assert text.count(".superpowers/sdd") == 1

def test_root_resolution_stated():
    assert "grandparent" in SKILL.read_text()

def test_status_vocabulary_present():
    text = SKILL.read_text()
    for status in ("DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED"):
        assert status in text

def test_openai_yaml_disables_implicit_invocation():
    assert "allow_implicit_invocation: false" in YAML.read_text()

def test_reader_contract_protocol():
    text = READER.read_text()
    for token in ("STATUS:", "ANSWER:", "REPORT:", "NEEDS_CONTEXT", "Read-only",
                  "cannot write files"):
        assert token in text
