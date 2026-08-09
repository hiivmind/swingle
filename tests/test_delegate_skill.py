import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "delegate" / "SKILL.md"
YAML = ROOT / "skills" / "delegate" / "agents" / "openai.yaml"
READER = ROOT / "contracts" / "reader-contract.md"

def _model_ids():
    """Every model id declared in any provider's models.yaml."""
    ids = set()
    for models in (ROOT / "providers").glob("*/models.yaml"):
        for line in models.read_text().splitlines():
            m = re.match(r'\s*(?:- )?model:\s*"?([^"\s#]+)"?', line)
            if m:
                ids.add(m.group(1))
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
    assert re.search(r"^name: swingle-delegate$", front, re.M)
    assert re.search(r"^description: .{40,}", front, re.M)

def _skill_files():
    """Every skill-authored file whose content the purity boundary binds."""
    files = list((ROOT / "skills").glob("*/SKILL.md"))
    files += [p for p in (ROOT / "skills").glob("*/agents/*.yaml")]
    return files

def test_purity_no_model_ids_in_any_skill():
    ids = _model_ids()
    assert ids, "expected provider model tables to parse"
    for skill in _skill_files():
        text = skill.read_text()
        leaked = {m for m in ids if m in text}
        assert not leaked, f"{skill}: model ids leaked: {leaked}"

# Leading markdown furniture that can precede a command on a line: list bullets,
# ordered-list markers, blockquotes, and shell prompts.
_MARKER = re.compile(r"^(?:[-*+>]\s+|\d+[.)]\s+|[$#]\s+)")

def _cli_invocation(line, clis):
    """A command-shaped use of a pack cli, or None.

    Command-shaped means: a pack cli name in leading position (after stripping
    markdown/prompt furniture and code-span backticks) carrying at least one flag
    argument. Requiring a flag is what separates a real invocation
    ("agy --model X ...", "- codex exec --json") from prose that merely opens with
    the name ("codex is the default when active").
    """
    stripped = line.strip()
    while True:
        m = _MARKER.match(stripped)
        if not m:
            break
        stripped = stripped[m.end():]
    stripped = stripped.strip("`").strip()
    parts = stripped.split()
    if len(parts) < 2 or parts[0] not in clis:
        return None
    if not any(p.startswith("-") for p in parts[1:]):
        return None
    return stripped

def test_purity_no_cli_invocations_anywhere():
    # Invocation strings live in provider packs only. No line ANYWHERE in a skill
    # (fenced or prose) may be a command-shaped use of a pack cli. Prose mentions
    # like "(codex/opencode/agy)", "via codex", or "codex is active" do not match;
    # bullets and shell prompts ("- codex exec --json", "$ agy -p ...") do.
    clis = _pack_clis()
    assert clis, "expected pack manifests to declare cli names"
    for skill in _skill_files():
        for n, line in enumerate(skill.read_text().splitlines(), 1):
            leaked = _cli_invocation(line, clis)
            assert not leaked, f"{skill}:{n}: cli invocation leaked into skill: {leaked}"

def test_cli_invocation_detector_discriminates():
    # Guards the heuristic itself: the detector must fire on real invocations
    # (including ones dressed in markdown) and stay silent on prose.
    clis = {"codex", "agy", "opencode"}
    for bad in ("agy --model X -p \"t\"", "- codex exec --json", "$ agy -p 'x'",
                "1. opencode run --model m", "`codex exec --cd .`", "> agy --version"):
        assert _cli_invocation(bad, clis), f"should have flagged: {bad}"
    for ok in ("codex is active", "via codex", "(codex/opencode/agy)",
               "- codex, opencode, and agy are the packs", "the agy pack", "codex"):
        assert _cli_invocation(ok, clis) is None, f"false positive: {ok}"

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
    # The contract is hard-wrapped prose, so a phrase can straddle a line break —
    # normalize whitespace before asserting, or the test breaks on a rewrap alone.
    text = " ".join(READER.read_text().split())
    # "cannot write files" was the original phrasing of the inline switch, back when it
    # fired only on an enforced read-only lane. The switch now also fires on a pack
    # declaring report-transport: captured-output, so the assertion covers both triggers.
    for token in ("STATUS:", "ANSWER:", "REPORT:", "NEEDS_CONTEXT", "Read-only",
                  "return the report inline", "cannot write files", "captured output"):
        assert token in text, f"reader contract missing: {token!r}"

def test_validator_ignores_delegate_workspace():
    # Regression: the delegate workspace is git-ignored agent scratch whose reports are
    # full of illustrative links. Before this guard, running the delegate skill inside
    # this repo made the repo's own hard gate fail on those links.
    #
    # Run the real validator on the real tree twice — once as-is, once with a
    # link-broken report planted in the workspace — and require identical results.
    # Comparing against the tree's own baseline isolates the workspace's effect
    # without needing a complete fixture copy.
    import subprocess, tempfile, os
    cmd = ["python3", str(ROOT / "scripts" / "validate-packs"), "--root", str(ROOT)]
    before = subprocess.run(cmd, capture_output=True, text=True)
    ws = ROOT / ".swingle" / "delegate"
    ws.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="zz-regression-", suffix=".md", dir=ws)
    os.close(fd)
    planted = Path(name)
    try:
        planted.write_text(
            "See [roles](file:///nowhere/core/roles.md#L1-L2) and [x](./nope.md).\n")
        after = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        planted.unlink()
    assert after.returncode == before.returncode, (
        f"delegate workspace changed the validator verdict "
        f"({before.returncode} -> {after.returncode}):\n{after.stdout}{after.stderr}")
    assert planted.name not in after.stdout + after.stderr, (
        "validator scanned a file inside the delegate workspace")

def _manifest(pack):
    front = pack.read_text().split("---", 2)[1]
    out = {}
    for line in front.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out

def test_every_pack_declares_a_valid_report_transport():
    # report-transport tells the skill whether an agent can be trusted to write its own
    # report file. Optional in the schema (default report-file), but every shipped pack
    # states it explicitly so routing never depends on an implicit default.
    packs = list((ROOT / "providers").glob("*/pack.md"))
    assert packs, "expected provider packs"
    for pack in packs:
        transport = _manifest(pack).get("report-transport")
        assert transport in {"report-file", "captured-output"}, \
            f"{pack}: report-transport must be report-file|captured-output, got {transport!r}"

def test_skill_branches_output_capture_on_report_transport():
    # The skill must route on the manifest field, not hardcode a provider name.
    text = SKILL.read_text()
    assert "report-transport" in text, "SKILL.md must consult the report-transport field"
    assert "captured-output" in text and "report-file" in text, \
        "SKILL.md must name both transports so the branch is unambiguous"

def test_reader_contract_inline_switch_is_not_sandbox_only():
    # The inline-report switch fires on EITHER an enforced read-only lane or a pack that
    # routes reports through captured output — it must not read as sandbox-only.
    text = READER.read_text()
    assert "captured output" in text, \
        "reader contract must cover the captured-output transport, not just read-only lanes"


DESIGN = ROOT / "contracts" / "design-reviewer-contract.md"
SDD_SKILL = ROOT / "skills" / "sdd" / "SKILL.md"


def test_design_reviewer_contract_states_the_no_code_premise():
    # The whole point of a separate contract: a design review must not degrade into
    # checking whether the design has been implemented. If that framing is ever edited
    # out, the contract is indistinguishable from the task-reviewer contract.
    text = " ".join(DESIGN.read_text().split())
    assert "has NOT been implemented yet" in text
    for token in ("Architectural flaws", "Missed edge cases", "Bad assumptions"):
        assert token in text, f"design contract missing lens: {token!r}"
    assert "not check whether the design has been carried out" in text


def test_both_skills_route_unimplemented_artifacts_to_the_design_contract():
    for skill in (SKILL, SDD_SKILL):
        text = skill.read_text()
        assert "design-reviewer-contract.md" in text, \
            f"{skill}: no route to the design-reviewer contract"


def test_status_vocabulary_is_required_inline_in_prompts():
    # playbook E1a: contracts move by path, the four status tokens move in the prompt.
    required = "STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED"
    for f in (ROOT / "core" / "playbook.md", SKILL, SDD_SKILL):
        text = " ".join(f.read_text().split())
        assert "inline" in text.lower() and required in text, \
            f"{f}: complete inline status-vocabulary rule missing"


def test_explicit_model_rule_is_stated_in_roles():
    text = " ".join((ROOT / "core" / "roles.md").read_text().split())
    assert "always passed explicitly" in text
    assert "inherits whatever model the caller's own session is running" in text


def test_worktree_dispatch_lane_present():
    text = (ROOT / "skills" / "delegate" / "SKILL.md").read_text()
    assert text.count('"in a worktree"') == 1 and text.count('"in my tree"') == 1
    assert "superpowers:using-git-worktrees" in text
    assert "swingle/" in text                       # branch naming pattern
    assert "final commit SHA" in text               # report requirement


def test_worktree_lane_keeps_operational_independence():
    # The existing independence counts must survive unchanged.
    text = (ROOT / "skills" / "delegate" / "SKILL.md").read_text()
    assert text.count("scripts/sdd-workspace") == 1 and text.count(".superpowers/sdd") == 1


def test_both_skills_define_registry_body_resolution_and_shard_logs():
    expected = (
        "Take the installed version from the CLI's **raw version-output token**, accepting it\n"
        "only when it full-matches the closed dotted-numeric grammar; a suffixed token is\n"
        "unparseable — never resolve on a numeric prefix. Resolve the provider BODY from the\n"
        "registry `providers/<id>/versions/`: exact key match → that file; between keys →\n"
        "nearest at-or-below; above the manifest's `verified-version` → the current file\n"
        "(`versions/<verified-version>.md`, silence — a newer release is not a defect); below\n"
        "the oldest key, or unparseable → the current file plus the corresponding advisory; the\n"
        "current file missing → STOP and surface (broken pack). The manifest (frontmatter)\n"
        "always comes from `pack.md`; each registry file's first line declares its evidence\n"
        "class (`> Verified:` round truth vs `> Distilled…:` assembled history) — weigh it.\n"
        "Version comparison and edge rules are in `core/verification-protocol.md` Recording.\n"
        "Guidance still applies additively on top of whichever body resolves."
    )
    expected = "\n".join(f"   {line}" for line in expected.splitlines())
    for skill in (SKILL, SDD_SKILL):
        text = skill.read_text()
        assert expected in text, f"{skill}: registry resolution paragraph drifted"
        assert "providers/<id>/log/" in text, f"{skill}: monthly log shards not referenced"
        assert "providers/<id>/verification-log.md" not in text, \
            f"{skill}: obsolete provider log index read remains"


def test_sdd_worktree_lane_present():
    text = (ROOT / "skills" / "sdd" / "SKILL.md").read_text()
    assert "superpowers:using-git-worktrees" in text          # literal skill string
    assert "swingle/sdd-" in text
    assert text.count('"in a worktree"') == 1 and text.count('"in my tree"') == 1
    assert "continue on the existing branch" in text          # continuation form


def test_both_skills_make_step0_the_fast_gate():
    for skill in (SKILL, SDD_SKILL):
        text = " ".join(skill.read_text().split())
        assert "`validate-packs --step0` is the mandatory fast gate" in text
        assert "Do not pre-explore `<root>`" in text
        assert "Do not independently re-run a provider `--version`" in text
        assert "Core doctrine is read by exception" in text


def test_both_skills_keep_launch_time_requirements():
    for skill in (SKILL, SDD_SKILL):
        text = " ".join(skill.read_text().split())
        assert "routed provider's manifest/body" in text
        assert "applicable role contract" in text
        assert "immediately before constructing the background wrapper" in text


def test_delegate_reads_provider_evidence_only_by_exception():
    text = " ".join(SKILL.read_text().split())
    assert "only when `--step0` reports drift" in text
    assert "immediately before constructing the background wrapper" in text


def test_sdd_does_not_require_a_prophylactic_core_document_wall():
    text = " ".join(SDD_SKILL.read_text().split())
    assert "Core doctrine is read by exception" in text
    assert "Read `<root>/core/roles.md`, `<root>/core/playbook.md`" not in text
