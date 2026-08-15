"""Step-0 outcome-table lockstep guard.

The dispatch skills' Markdown outcome tables are normative; lib/swingle/step0.py is
their executable rendering (repo CLAUDE.md). This test fails if the two drift:
- every typed line step0 emits must have its prefix declared in OUTCOME_PREFIXES, so a
  new outcome class forces a constant update;
- every adjudicated class (STOP/ASK/CHANNEL/warning) must appear verbatim in BOTH skills.
"""

import re
from pathlib import Path

from swingle import step0

ROOT = Path(__file__).resolve().parents[1]
SKILLS = [
    ROOT / "skills" / "sdd" / "SKILL.md",
    ROOT / "skills" / "delegate" / "SKILL.md",
]
ADJUDICATED = {"STOP:", "ASK:", "CHANNEL:", "warning:"}
STEP0_SRC = (ROOT / "lib" / "swingle" / "step0.py").read_text()


def _emitted_prefixes():
    prefixes = set()
    for text in re.findall(r'(?:print|find)\(f?"([^"{]*)', STEP0_SRC):
        text = text.strip()
        if not text:
            continue
        prefixes.add(text[: text.index(":") + 1] if ":" in text else text)
    return prefixes


def test_outcome_prefixes_match_emitted_lines():
    """OUTCOME_PREFIXES is exactly the set of prefixes step0 actually emits."""
    assert _emitted_prefixes() == step0.OUTCOME_PREFIXES


def test_adjudicated_classes_declared_and_documented():
    for prefix in ADJUDICATED:
        assert prefix in step0.OUTCOME_PREFIXES, prefix
        for skill in SKILLS:
            assert prefix in skill.read_text(), f"{prefix} missing from {skill.name}"
