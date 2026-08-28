from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELEGATE = ROOT / "skills" / "delegate" / "SKILL.md"
SETUP = ROOT / "skills" / "swingle-setup" / "SKILL.md"
SDD = ROOT / "skills" / "sdd" / "SKILL.md"
ISOLATION = ROOT / "references" / "isolation.md"

ANNOUNCEMENT_BLOCK = (
    "delegate: role=<role> contract=<contract> tier=<tier> provider=<provider> "
    "model=<model> effort=<effort> attempt=<attempt> run=<run-id> job=<job-id>\n"
    "artifacts: <artifact-dir> — inspect: cd <quoted-repo-root> && python3 "
    "<quoted-plugin-root>/scripts/swingle workspace show --run <run-id> --job <job-id>"
)


def _section(text: str, start_heading: str, end_heading: str) -> str:
    start = text.index(start_heading)
    end = text.index(end_heading, start + len(start_heading))
    return text[start:end]


def _single_text_block(section: str) -> str:
    opener = "```text\n"
    closer = "\n```"
    _, found_opener, remainder = section.partition(opener)
    assert found_opener
    block, found_closer, suffix = remainder.partition(closer)
    assert found_closer
    assert opener not in suffix
    return block


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


def test_delegate_defines_contract_selection_announcement_fields_and_encoding():
    text = DELEGATE.read_text()
    section = _section(
        text,
        "## Contract selection announcement",
        "## Consent and isolation",
    )

    for required in (
        "^[A-Za-z0-9._/@+-]+$",
        "json.dumps(value, ensure_ascii=True)",
        "shlex.quote",
        "full lowercase UUIDs",
        "artifact_dir",
        "returned verbatim",
        "-contract.md",
        "provider-default",
        "attempt=1",
        "$REPO_ROOT",
        "$PLUGIN_ROOT",
        "accepted role and tier",
        "provider, model, and effort resolved",
        "CR or LF",
        "reject the dispatch before rendering",
        "no pause, confirmation, consent, or prompt",
        "one block per `dispatched` event",
        "never emit one summary per run",
        "`gpt-5.2` → `model=gpt-5.2`",
        '`foo effort=high` → `model="foo effort=high"`',
        "`/tmp/Swingle repo` → `'/tmp/Swingle repo'`",
        "`$REPO_ROOT=/tmp/repo\\nbreak` → reject",
        "`$PLUGIN_ROOT=/tmp/plugin\\rbreak` → reject",
    ):
        assert required in section

    assert section.index("artifact_dir") < section.index("returned verbatim")
    assert "JSON quoting" in section
    assert "shell operands" in section


def test_delegate_announces_warm_attempt_after_begin_and_before_launch():
    text = DELEGATE.read_text()
    section = _section(
        text,
        "### Warm cache path",
        "## Positive-TTL miss and TTL-zero paths",
    )
    announcement_section = _section(
        section,
        "#### Announce warm attempt 1",
        "Launch only after",
    )
    block = _single_text_block(announcement_section)
    announcement_fence = f"```text\n{block}\n```"
    announcement_at = section.index(announcement_fence)

    assert block == ANNOUNCEMENT_BLOCK
    assert announcement_fence not in section[
        announcement_at + len(announcement_fence):
    ]
    assert section.index(
        "python3 $PLUGIN_ROOT/scripts/swingle ledger begin-direct"
    ) < section.index("Build Bash from current mechanics")
    assert section.index("Build Bash from current mechanics") < announcement_at
    assert announcement_at < section.index("Launch only after")
    for required in (
        "#### Announce warm attempt 1",
        "run_id",
        "job_id",
        "artifact_dir",
        "known constant `1`",
        "resolved selection transported",
        "complete provider command is composed",
    ):
        assert required in section


def test_delegate_announces_ttl_zero_attempt_after_begin_and_before_launch():
    text = DELEGATE.read_text()
    section = _section(
        text,
        "### Announce TTL-zero attempt 1",
        "## Failure recovery",
    )
    block = _single_text_block(section)
    announcement_at = section.index(f"```text\n{block}\n```")

    assert block == ANNOUNCEMENT_BLOCK
    assert section.index("ledger begin-direct") < section.index(
        "compose the complete provider Bash command"
    )
    assert section.index("compose the complete provider Bash command") < announcement_at
    assert announcement_at < section.index("launch provider Bash")
    for required in (
        "ground_without_cache",
        "storage: none",
        "null receipt fields",
        "run_id",
        "job_id",
        "artifact_dir",
        "known constant `1`",
    ):
        assert required in section


def test_delegate_announces_each_batch_job_after_dispatched_and_before_launch():
    text = DELEGATE.read_text()
    section = _section(
        text,
        "### Announce each batch attempt",
        "### Finalize the batch",
    )
    block = _single_text_block(section)
    announcement_at = section.index(f"```text\n{block}\n```")

    assert block == ANNOUNCEMENT_BLOCK
    assert section.index("ledger allocate") < section.index(
        "ledger record dispatched --attempt 1"
    )
    assert section.index("ledger record dispatched --attempt 1") < section.index(
        "compose the complete provider command for that job"
    )
    assert (
        section.index("compose the complete provider command for that job")
        < announcement_at
    )
    assert announcement_at < section.index("launch that job")
    for required in (
        "one block per job per attempt",
        "shared run_id",
        "job_id",
        "artifact_dir",
        "returned by",
        "resolved selection transported",
    ):
        assert required in section


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
        "workspace show",
        "workspace verify",
        "workspace copy",
        "workspace delete",
        "The manifest is automatic.",
        "The ledger is authoritative for lifecycle state.",
        "The manifest is authoritative for file inventory and hashes.",
        "Copy never sends files to a network service.",
        "Copy never runs Git.",
        "Deletion never removes ledger files.",
        "Swingle has no workspace classification or retention policy.",
        "The workspace modules do not import `subprocess`, network clients, or Git bindings.",
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


FORBIDDEN_WORKSPACE_POLICY_VOCABULARY = (
    "sensitivity",
    "retention class",
    "legal hold",
    "archive receipt",
    "publication receipt",
    "workspace policy",
)


def test_delegate_reports_workspace_output_and_authorized_copy():
    text = DELEGATE.read_text()
    for required in (
        "ledger finish-direct --project $REPO_ROOT",
        "primary output path",
        "job directory",
        "workspace copy",
        "source-manifest.json",
        "original request names the exact destination and selection",
        "one confirmation",
    ):
        assert required in text


def test_sdd_passes_project_to_terminal_operations():
    text = SDD.read_text()
    for required in (
        "ledger record complete --project $REPO_ROOT",
        "ledger finalize-run --project $REPO_ROOT",
    ):
        assert required in text


def test_setup_inspects_workspace_parent_without_creating_state():
    text = SETUP.read_text()
    assert "nearest existing parent" in text
    assert "does not create the workspace during inspection" in text


def test_normal_workspace_guidance_excludes_policy_vocabulary():
    concepts = (ROOT / "references" / "concepts.md").read_text()
    entry_docs = "\n".join((ROOT / name).read_text() for name in ("README.md", "CLAUDE.md"))
    text = "\n".join((DELEGATE.read_text(), SDD.read_text(), SETUP.read_text(), concepts, entry_docs)).lower()
    for forbidden in FORBIDDEN_WORKSPACE_POLICY_VOCABULARY:
        assert forbidden not in text
