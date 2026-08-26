from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELEGATE = ROOT / "skills" / "delegate" / "SKILL.md"
SETUP = ROOT / "skills" / "swingle-setup" / "SKILL.md"
SDD = ROOT / "skills" / "sdd" / "SKILL.md"
ISOLATION = ROOT / "references" / "isolation.md"

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


def test_delegate_uses_next_action_controller_flow():
    text = DELEGATE.read_text()
    for required in (
        "$PLUGIN_ROOT",
        "$REPO_ROOT",
        "dispatch context",
        "next_action",
        "ledger begin-direct",
        "ledger finish-direct",
        "ledger finalize-run",
        "grounding record",
        "grounding refresh",
        "setup_repair",
        "ground_without_cache",
        "grounding_source",
        "exact authored briefing",
        "artifact directory",
        "selected provider pack path",
        "Dispatch-guidance fingerprint",
        "read and adapt Dispatch guidance",
        "temporary parser",
        "repository_verification",
        "VERIFIED",
        "run-completed",
        "wait or join concurrent jobs",
        "jobs=N done=N done_with_concerns=N needs_context=N blocked=N",
        "BLOCKED > NEEDS_CONTEXT > DONE_WITH_CONCERNS > DONE",
    ):
        assert required in text
    for command in (
        "python3 $PLUGIN_ROOT/scripts/swingle dispatch context",
        "python3 $PLUGIN_ROOT/scripts/swingle ledger begin-direct",
        "python3 $PLUGIN_ROOT/scripts/swingle ledger finish-direct",
        "python3 $PLUGIN_ROOT/scripts/swingle ledger finalize-run",
        "python3 $PLUGIN_ROOT/scripts/swingle grounding record",
        "python3 $PLUGIN_ROOT/scripts/swingle grounding refresh",
    ):
        assert command in text
    for removed in (
        "ledger init",
        "ledger append",
        "ledger record run-completed",
        ".swingle/delegate/ledger.md",
        "config show --project",
        "acquire grounding",
        "claim token",
        "busy wait",
        "refresh lease",
        "dispatch render",
        "result extract",
        "selector program",
        "prompt paraphrase",
    ):
        assert removed not in text


def test_setup_manages_only_swingle_owned_state():
    text = SETUP.read_text()
    for required in (
        "scripts/swingle config", "scripts/swingle ledger", "executable presence",
        "Path(<this SKILL.md>).parents[2]", "does not inspect provider auth",
        "Explicit migration", "SWINGLE_MODELS", "user model directory",
        "references/isolation.md",
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


def test_setup_defines_targeted_repairs_and_cache_git_behavior():
    text = SETUP.read_text()
    for required in (
        "repair=config-error",
        "repair=provider-routing",
        "repair=grounding-policy",
        "repair=liveness-policy",
        "repair=provider-grounding",
        "REPAIRED",
        "DECLINED",
        "BLOCKED",
        "grounding refresh",
        ".swingle/grounding/.gitignore",
        ".swingle/delegate/ledger/",
        ".swingle/delegate/artifacts/.gitignore",
        "raw artifacts never committed",
    ):
        assert required in text
    for forbidden in ("lease", "polling", "setup-complete", "watchdog"):
        assert forbidden not in text.lower()


def test_sdd_defines_shared_run_ledger_and_outcome_contract():
    text = SDD.read_text()
    for required in (
        "ledger start",
        "--kind sdd",
        "controller-session-id",
        "run-id",
        "dispatch context",
        "ledger allocate",
        "ledger finalize-run",
        "run-completed",
        "provider_outcome",
        "repository_verification",
        "VERIFIED",
        "jobs=N done=N done_with_concerns=N needs_context=N blocked=N",
        "BLOCKED > NEEDS_CONTEXT > DONE_WITH_CONCERNS > DONE",
    ):
        assert required in text
    assert "ledger record run-completed" not in text
    for forbidden in ("lease", "polling", "setup-complete", "watchdog"):
        assert forbidden not in text.lower()


def test_grounding_isolation_keeps_controller_state_local():
    text = ISOLATION.read_text()
    for local in (
        "dispatch context",
        "grounding record",
        "grounding invalidate",
        "ledger writes",
        "config reads and writes",
        "temporary parser and artifact management",
        "task-specific repository verification",
    ):
        assert local in text
    for isolated in (
        "live provider help",
        "model listing",
        "provider-note recovery analysis",
        "safe behavioral probes",
        "failure-repair hunts",
    ):
        assert isolated in text
    assert "warm dispatch never creates a grounding worker" in text


def test_living_documentation_describes_v2_state_and_commands():
    concepts = (ROOT / "references" / "concepts.md").read_text()
    config = (ROOT / "references" / "config.md").read_text()
    tiering = (ROOT / "references" / "model-tiering.md").read_text()
    entry_docs = "\n".join((ROOT / name).read_text() for name in ("README.md", "CLAUDE.md"))
    for name in ("README.md", "CLAUDE.md"):
        text = (ROOT / name).read_text()
        assert "read-only dispatch context, grounding" not in text
        assert (
            "read-only dispatch context plus typed grounding and ledger state/inspection "
            "commands"
        ) in text

    for required in (
        "Tier → Provider → Project grounding → Model + Effort",
        "LLM-composed command",
        "Provider outcome",
        "Repository verification",
        "observed mechanics",
        "advisory inventory",
        "live invocation wins",
        "Python never renders commands",
        '"grounding_cache"',
        '"ttl_seconds": 604800',
        '"liveness"',
        "unknown providers",
        "invalid optional branches",
        "invalid explicit liveness policy stops before dispatch",
        "cached inventory",
        "invalidate",
        "accepted explicit model",
        "dispatch context --project <project-root> --role <role> --tier <tier>",
        "grounding show --project <project-root> --provider <provider-id>",
        "ledger show --dir <ledger-directory> --format text",
        "ledger validate --dir <ledger-directory>",
        ".swingle/delegate/ledger/",
        ".swingle/delegate/artifacts/",
        "provider_outcome",
        "repository_verification",
        "--legacy-path",
        "references/liveness.md",
        "exact authored briefing",
        "dynamic result interpretation",
    ):
        assert required in "\n".join((concepts, config, tiering, entry_docs))

    for retired in (
        "ledger init",
        "ledger append",
        "ledger record run-completed",
        ".swingle/delegate/ledger.md",
        "dispatch render",
        "result extract",
        "selector program",
        "runnable recipe",
    ):
        assert retired not in entry_docs
