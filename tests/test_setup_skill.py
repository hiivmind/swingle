# -*- coding: utf-8 -*-
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "swingle-setup" / "SKILL.md"
YAML = ROOT / "skills" / "swingle-setup" / "agents" / "openai.yaml"
FIXTURES = ROOT / "tests" / "fixtures" / "setup-skill"

# Probe label regex: spell the em-dash as an explicit \u2014 ('—')
PROBE_LABEL_RE = re.compile(r"^#+\s*P\d+\b|P\d+\s+—")

# Leading markdown furniture that can precede a command on a line: list bullets,
# ordered-list markers, blockquotes, and shell prompts.
_MARKER = re.compile(r"^(?:[-*+>]\s+|\d+[.)]\s+|[$#]\s+)")


def _pack_clis():
    """The validated cli name from every provider pack manifest."""
    clis = set()
    for pack in (ROOT / "providers").glob("*/pack.md"):
        m = re.search(r"^cli: (\S+)", pack.read_text(encoding="utf-8"), re.M)
        if m:
            clis.add(m.group(1))
    return clis


def _cli_invocation(line, clis):
    """A command-shaped use of a pack cli, or None."""
    stripped = line.strip()
    while True:
        m = _MARKER.match(stripped)
        if not m:
            break
        stripped = stripped[m.end() :]
    stripped = stripped.strip("`").strip()
    parts = stripped.split()
    if len(parts) < 2 or parts[0] not in clis:
        return None
    if not any(p.startswith("-") for p in parts[1:]):
        return None
    return stripped


def _check_boundary_guard(text: str, clis: set) -> list:
    """Boundary guard checking for P-label probe steps or CLI probe invocations."""
    violations = []
    for n, line in enumerate(text.splitlines(), 1):
        if PROBE_LABEL_RE.search(line):
            violations.append(f"Line {n}: probe label step found: {line.strip()!r}")
        inv = _cli_invocation(line, clis)
        if inv:
            violations.append(f"Line {n}: probe invocation found: {inv!r}")
    return violations


def test_skill_exists_with_frontmatter():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    front = text.split("---", 2)[1]
    assert re.search(r"^name: swingle-setup$", front, re.M)
    assert re.search(r"^description: .{40,}", front, re.M)
    assert re.search(r"explicit.*only", front, re.I) or re.search(
        r"explicit.*only", text, re.I
    )

    yaml_text = YAML.read_text(encoding="utf-8")
    assert "allow_implicit_invocation: false" in yaml_text


def test_boundary_guard_passes_on_setup_skill():
    clis = _pack_clis()
    text = SKILL.read_text(encoding="utf-8")
    violations = _check_boundary_guard(text, clis)
    assert not violations, f"Boundary guard violations found in SKILL.md: {violations}"
    assert "swingle-verify <id>" in text, (
        "bare recommendation string swingle-verify <id> must be present"
    )


def test_boundary_guard_fails_on_violating_fixtures():
    clis = _pack_clis()

    p_label_file = FIXTURES / "violating_p_label.md"
    assert p_label_file.exists(), f"Missing fixture file: {p_label_file}"
    p_label_text = p_label_file.read_text(encoding="utf-8")
    violations_p = _check_boundary_guard(p_label_text, clis)
    assert violations_p, f"Expected boundary guard to fail on {p_label_file.name}"
    assert any("probe label" in v for v in violations_p)

    probe_inv_file = FIXTURES / "violating_probe_invocation.md"
    assert probe_inv_file.exists(), f"Missing fixture file: {probe_inv_file}"
    probe_inv_text = probe_inv_file.read_text(encoding="utf-8")
    violations_inv = _check_boundary_guard(probe_inv_text, clis)
    assert violations_inv, f"Expected boundary guard to fail on {probe_inv_file.name}"
    assert any("probe invocation" in v for v in violations_inv)


def test_superpowers_operational_independence():
    text = SKILL.read_text(encoding="utf-8")
    assert "no superpowers dependency" in text.lower()
    assert text.count("scripts/sdd-workspace") == 1
    assert text.count(".superpowers/") == 1


def test_consent_invariants_present():
    text = SKILL.read_text(encoding="utf-8")
    assert "consent" in text.lower()
    assert "yes to all" in text.lower()
    assert "never" in text.lower()


def test_superpowers_probe_present():
    text = SKILL.read_text(encoding="utf-8")
    assert (
        "superpowers: <version>" in text and "superpowers: none" in text
    )  # exact probe reply grammar
    assert "superpowers: unknown-version" in text  # installed-but-undiscoverable case
    assert text.count("worktree-dispatch") >= 1  # names its consumer


def test_superpowers_probe_is_consented_and_recorded():
    text = SKILL.read_text(encoding="utf-8")
    assert '"probed"' in text and '"installed"' in text  # records the validated shape
