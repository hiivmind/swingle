# Dispatch Setup Fast Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one-off and SDD dispatch setup deterministic and check-by-exception instead of a mandatory policy-document preamble.

**Architecture:** `validate-packs --root` remains the trust gate and `validate-packs --step0` remains the environment, route, readiness, and drift gate. The two skill documents move generic policy files behind named exceptions, while keeping the routed provider body, role contract, and launch-time liveness read at the exact point each is needed.

**Tech Stack:** Markdown skills; pytest behavioral-contract tests; existing `scripts/validate-packs` CLI.

## Global Constraints

- No persistent setup fingerprint or new configuration schema.
- Preserve trust, Step-0, provider-body, role-contract, clean-tree, evidence, containment, and controller-test/commit gates.
- Preserve the registry-resolution paragraph byte-for-byte because `tests/test_delegate_skill.py` treats it as a contract.
- Test behavior rather than exact incidental prose outside established contract fragments.

---

### Task 1: Lock the fast-path contract in tests

**Files:**
- Modify: `tests/test_delegate_skill.py`
- Test: `tests/test_delegate_skill.py`

**Interfaces:**
- Consumes: `skills/delegate/SKILL.md`, `skills/sdd/SKILL.md`
- Produces: `test_both_skills_make_step0_the_fast_gate` and `test_both_skills_keep_launch_time_requirements`

- [ ] **Step 1: Write failing behavioral tests**

Add assertions over both skill files:

```python
def test_both_skills_make_step0_the_fast_gate():
    for skill in (SKILL, SDD_SKILL):
        text = skill.read_text()
        assert "Do not pre-explore" in text
        assert "Do not independently re-run a provider `--version`" in text
        assert "read by exception" in text
        assert "`validate-packs --step0` is the mandatory" in text


def test_both_skills_keep_launch_time_requirements():
    for skill in (SKILL, SDD_SKILL):
        text = skill.read_text()
        assert "routed provider's manifest/body" in text
        assert "applicable role contract" in text
        assert "immediately before constructing the background wrapper" in text
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `uv run pytest tests/test_delegate_skill.py -q`

Expected: failure because neither skill yet contains the fast-path contract.

- [ ] **Step 3: Record the fast-path policy in both skills**

Replace their “Never dispatch from memory” / unconditional core-read wording with the approved decision. In each Setup flow:

```markdown
`validate-packs --step0` is the mandatory fast gate.
Do not pre-explore `<root>` ...
Do not independently re-run a provider `--version` after the gate.
Read core doctrine by exception ...
```

Keep the existing `--root`, `--step0`, and registry-resolution text intact.

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `uv run pytest tests/test_delegate_skill.py -q`

Expected: PASS.

### Task 2: Move Delegate setup reads to their point of need

**Files:**
- Modify: `skills/delegate/SKILL.md`
- Test: `tests/test_delegate_skill.py`

**Interfaces:**
- Consumes: fast-path test contract from Task 1
- Produces: direct-dispatch Setup flow with exception-only core-doc reads

- [ ] **Step 1: Add a failing test for the delegate-specific flow**

Assert that the delegate skill says `liveness.md` is read immediately before constructing the background wrapper and that provider log/local records are read only for drift or body-required preflight:

```python
def test_delegate_reads_provider_evidence_only_by_exception():
    text = SKILL.read_text()
    assert "only when `--step0` reports drift" in text
    assert "immediately before constructing the background wrapper" in text
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `uv run pytest tests/test_delegate_skill.py -q`

Expected: failure because Setup step 6 currently mandates the log/local-record sweep and reads liveness in the universal preamble.

- [ ] **Step 3: Update `skills/delegate/SKILL.md` minimally**

- Remove the unconditional first-dispatch core-doc mandate.
- Retain one routed-provider body/manifest read before first use of that provider and the role contract at prompt construction.
- Change provider logs and user record from mandatory startup evidence to drift/lane-preflight evidence.
- Put `liveness.md` immediately before Step 3’s background wrapper construction.
- State reuse within an installed plugin version for later jobs in the same session.

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `uv run pytest tests/test_delegate_skill.py -q`

Expected: PASS.

### Task 3: Apply the same policy to SDD Step 0

**Files:**
- Modify: `skills/sdd/SKILL.md`
- Test: `tests/test_delegate_skill.py`

**Interfaces:**
- Consumes: approved fast-path policy and the Step-0 outcome table already in the skill
- Produces: SDD Step 0 that does not proactively load core doctrine

- [ ] **Step 1: Add a failing SDD-specific test**

```python
def test_sdd_does_not_require_a_prophylactic_core_document_wall():
    text = SDD_SKILL.read_text()
    assert "Core doctrine is read by exception" in text
    assert "Read `<root>/core/roles.md`, `<root>/core/playbook.md`" not in text
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `uv run pytest tests/test_delegate_skill.py -q`

Expected: failure because current SDD Step 0 requires all four core documents before the trust gate.

- [ ] **Step 3: Update `skills/sdd/SKILL.md` minimally**

- Move the trust gate and Step-0 gate before any exception-based policy reads.
- Retain the existing shell-less fallback, step0 outcome table, and exact registry-resolution paragraph.
- Require routed provider body/manifest and role contract at first use; require `liveness.md` at launch time.
- Preserve SDD’s `superpowers:subagent-driven-development`, workspace, and progress-ledger setup.

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `uv run pytest tests/test_delegate_skill.py -q`

Expected: PASS.

### Task 4: Document delivery and verify the complete contract

**Files:**
- Modify: `docs/superpowers/specs/2026-08-09-dispatch-setup-fast-path-design.md`
- Modify: `docs/superpowers/plans/2026-08-09-dispatch-setup-fast-path.md`
- Modify: `~/git/hiivmind/swingle-central/04.planning/backlog/2026-08-01-validate-packs-surface-streamlining.md`
- Test: `tests/test_delegate_skill.py`, full test suite

**Interfaces:**
- Consumes: completed Task 1–3 skill behavior
- Produces: delivered design/backlog record and verified repository state

- [ ] **Step 1: Mark the design and plan delivery state accurately**

Only after green tests, update the design status with the branch/commit evidence and mark completed plan checkboxes.

- [ ] **Step 2: Update the central backlog with the new delivered round**

Document that the original `--step0` consolidation removed duplicate mechanical pipeline logic, while this round removes the remaining unconditional skill-read preamble. List the preserved hard gates and the fact that no persisted cross-session fingerprint was added.

- [ ] **Step 3: Run focused and full verification**

Run:

```bash
uv run pytest tests/test_delegate_skill.py -q
uv run pytest -q
python3 scripts/validate-packs --root .
```

Expected: all pass; the validator returns exit 0.

- [ ] **Step 4: Review the actual diff and commit**

Inspect the skill and test diff. Commit only the streamlining change with a message such as:

```bash
git commit -am "fix(dispatch): gate setup reads on step0 exceptions"
```
