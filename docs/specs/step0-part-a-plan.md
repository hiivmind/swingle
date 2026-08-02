# Step-0 Part A — Probe Only the Routed Provider — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut the ~4s first-dispatch Step-0 latency by version-probing only the *routed* provider (not every active provider) when `require-verified-version` is off, with zero caching and zero staleness risk.

**Architecture:** In `scripts/validate-packs` `--step0`, move the per-active-provider version loop so it runs in full **only** under `require-verified-version` (where it filters the active set before routing). Otherwise route first, then version-probe only the chosen provider for the drift advisory. Update both skills' Step-0 prose + outcome table in lockstep so "drift is in effect" means the routed provider.

**Tech Stack:** Python 3 stdlib (`scripts/validate-packs`), pytest (`tests/test_validate_packs.py`), Markdown skills.

## Global Constraints

- Purity boundary: `skills/**` contains no CLI-invocation strings (enforced by `tests/test_delegate_skill.py`). All CLI spawning stays in `validate-packs`.
- Living-document lockstep: the Step-0 outcome table is normative and the script is its executable rendering — change them together (repo `CLAUDE.md`).
- Hard gate before every commit, chained with `&&`: `python3 scripts/validate-packs --root . && ./scripts/codex-smoke && git commit ...`.
- No new manifest field; `REQ`/`OPTIONAL`/`ENUMS` untouched.
- Behavior parity under `require-verified-version`: the full active-set loop and its `warning: incompatible: …` + `warning: incompatible providers removed: …` lines are unchanged.
- Design source: `docs/specs/warm-start-receipt-design.md` Part A + "Control flow reorder" + "Drift semantics narrow".

---

### Task 1: `--step0` routes first, then probes only the routed provider (non-strict)

**Files:**
- Modify: `scripts/validate-packs` — the `elif a.step0:` external branch in `main()` (the version loop currently at ~lines 518–526 and the routing/readiness block ~lines 531–552).
- Test: `tests/test_validate_packs.py`

**Interfaces:**
- Consumes: `detect_installed_providers(manifests, path_dirs)`, `check_provider_version(fm, path_dirs, timeout) -> (rc, output, actual_ver)`, `candidate_order`, `resolve_models`, `parse_roles`, `check_provider_readiness`, `load_config` — all unchanged.
- Produces: identical stdout tokens (`installed:`, `active:`, `provider:`, `model:`, `ready:`, `warning: incompatible: …`, `ASK:`/`CHANNEL:`/`STOP:`) with the version-probe *scope* changed. No new tokens.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_validate_packs.py` (near the other `--step0` tests, ~line 149):

```python
def test_step0_nonrouted_provider_drift_not_probed(tmp_path):
    """Non-strict multi-active: a stale NON-routed provider must not emit a drift
    warning — only the routed provider's version is probed."""
    cfg = tmp_path / "lane-beta.json"
    cfg.write_text('{"providers_by_lane": {"review": "beta"}}')
    r = run("--step0", "--root", str(FIX / "good-two-providers"),
            "--path-dir", str(FIX / "bins-two-alpha-oldver"),
            "--config", str(cfg), "--role", "per-task reviewer")
    assert r.returncode == 0
    assert "provider: beta" in r.stdout
    assert "warning: incompatible: alpha" not in r.stdout   # non-routed, not probed

def test_step0_routed_provider_drift_still_warns(tmp_path):
    """Non-strict: the routed provider's drift still surfaces a warning (exit 0)."""
    cfg = tmp_path / "lane-alpha.json"
    cfg.write_text('{"providers_by_lane": {"review": "alpha"}}')
    r = run("--step0", "--root", str(FIX / "good-two-providers"),
            "--path-dir", str(FIX / "bins-two-alpha-oldver"),
            "--config", str(cfg), "--role", "per-task reviewer")
    assert r.returncode == 0
    assert "provider: alpha" in r.stdout
    assert "warning: incompatible: alpha" in r.stdout
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_validate_packs.py::test_step0_nonrouted_provider_drift_not_probed tests/test_validate_packs.py::test_step0_routed_provider_drift_still_warns -q`
Expected: FAIL — `test_step0_nonrouted_provider_drift_not_probed` fails because the current full loop probes `alpha` and prints `warning: incompatible: alpha` even when `beta` is routed.

- [ ] **Step 3: Reorder the `--step0` branch — full loop only under strict, else probe routed after routing**

In `scripts/validate-packs`, replace the current sequence (version loop → strict removal → `if not active` → route → resolve → readiness) so the loop is strict-only and the non-strict drift probe happens on the chosen provider. Target shape (adapt to the exact surrounding lines):

```python
            installed = detect_installed_providers(manifests, a.path_dir)
            print(f"installed: {' '.join(installed) or '(none)'}")
            active = [provider for provider in installed if provider not in set(cfg.get("disable", []))]
            strict = bool(cfg.get("require-verified-version"))
            if strict:
                # Full active-set probe is required only here: it filters the active
                # set before routing (an incompatible provider must not be routable).
                incompatible = []
                for provider in active:
                    timeout = int(manifests[provider].get("readiness-timeout-seconds", 30))
                    rc, output, actual_ver = check_provider_version(manifests[provider], a.path_dir, timeout)
                    verified_ver = manifests[provider].get("verified-version")
                    if rc != 0 or not actual_ver or actual_ver != verified_ver:
                        actual = actual_ver if actual_ver else "unparseable"
                        print(f"warning: incompatible: {provider} ({actual} != {verified_ver})")
                        incompatible.append(provider)
                dropped = set(incompatible)
                if dropped:
                    print(f"warning: incompatible providers removed: {' '.join(sorted(dropped))}")
                active = [provider for provider in active if provider not in dropped]
            if not active:
                find("ASK: no active providers")
            else:
                print(f"active: {' '.join(active)}"); role_tier_lane = None
                if a.role:
                    roles = parse_roles(root); role_tier_lane = next((value for key, value in roles.items() if a.role.lower() in key), None)
                    if not role_tier_lane: find(f"STOP: unknown role: {a.role}")
                lane = role_tier_lane[1] if role_tier_lane else None
                chosen = a.task_provider or a.lever or (cfg.get("providers_by_lane", {}).get(lane) if lane else None) or cfg.get("default_provider") or ("codex" if "codex" in active else (active[0] if len(active) == 1 else None))
                if chosen and chosen not in active: find(f"ASK: routed provider inactive: {chosen}")
                elif not chosen: find("ASK: route-selection: ask user (multiple active, no policy)")
                else:
                    print(f"provider: {chosen}")
                    if role_tier_lane:
                        layer, layer_path, layer_rows = resolve_models(chosen, root, a.project)
                        if layer_path is not None: print(f"layer: {layer} path={layer_path.resolve()}")
                        order = candidate_order(layer_rows, *role_tier_lane, excluded.get(chosen, set()))
                        if not order and layer in ("env", "project", "user"): find(f"ASK: no eligible model for {role_tier_lane} in {chosen} — override at {layer_path} does not cover {role_tier_lane}")
                        elif not order: find(f"ASK: no eligible model for {role_tier_lane} in {chosen}")
                        else: print(f"model: {order[0]['model']} (P{order[0]['prio']}); fallback: {', '.join(row['model'] for row in order)}")
                    if not strict:
                        # Part A: probe ONLY the routed provider for the drift advisory.
                        timeout = int(manifests[chosen].get("readiness-timeout-seconds", 30))
                        rc, output, actual_ver = check_provider_version(manifests[chosen], a.path_dir, timeout)
                        verified_ver = manifests[chosen].get("verified-version")
                        if rc != 0 or not actual_ver or actual_ver != verified_ver:
                            actual = actual_ver if actual_ver else "unparseable"
                            print(f"warning: incompatible: {chosen} ({actual} != {verified_ver})")
                    rc, _ = check_provider_readiness(manifests[chosen], a.path_dir, int(manifests[chosen].get("readiness-timeout-seconds", 30)))
                    if rc != 0: find(f"CHANNEL: provider not ready: {chosen} (exit {rc})")
                    else: print(f"ready: {chosen}")
```

- [ ] **Step 4: Run the new tests to verify they pass**

Run: `uv run --with pytest pytest tests/test_validate_packs.py::test_step0_nonrouted_provider_drift_not_probed tests/test_validate_packs.py::test_step0_routed_provider_drift_still_warns -q`
Expected: PASS.

- [ ] **Step 5: Run the full validator suite to verify no regression**

Run: `uv run --with pytest pytest tests/test_validate_packs.py -q`
Expected: PASS — in particular the pre-existing `test_step0_version_mismatch_warns_but_remains_active_without_strict_mode` (single active provider is the routed one → warning still fires), `test_step0_strict_removal_*` and `test_step0_version_mismatch_blocks_when_required` (strict path unchanged), and `test_step0_readiness_failure_reported` (readiness unchanged).

- [ ] **Step 6: Commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
  git add scripts/validate-packs tests/test_validate_packs.py && \
  git commit -m "feat(step0): probe only the routed provider unless require-verified-version"
```

---

### Task 2: Skill Step-0 lockstep — drift advisory means the routed provider

**Files:**
- Modify: `skills/delegate/SKILL.md` — the Step-0 pipeline prose ("drift advisory") and the outcome-table `warning:` row.
- Modify: `skills/sdd/SKILL.md` — the equivalent Step-0 pipeline prose and outcome-table `warning:` row.

**Interfaces:**
- Consumes: Task 1's behavior (routed-only probe; strict full loop).
- Produces: skill prose whose normative outcome table matches Task 1's stdout.

- [ ] **Step 1: Update `skills/delegate/SKILL.md`**

In the Step-0 pipeline sentence, change the `→ drift advisory →` phase to name the scope, e.g.:
`→ drift advisory (routed provider only; the full active-set version probe runs only under require-verified-version, where it filters routing) →`.
In the outcome table, change the `warning: …` row's Meaning cell to:
`routed-provider drift, or strict-mode removals, with a valid route` (keep the Action cell "note **drift is in effect**" unchanged).

- [ ] **Step 2: Apply the identical edits to `skills/sdd/SKILL.md`**

Same two edits in the sdd Step-0 pipeline sentence and outcome table.

- [ ] **Step 3: Verify skill-structure suites still pass**

Run: `uv run --with pytest pytest tests/test_delegate_skill.py tests/test_setup_skill.py -q`
Expected: PASS (purity + single-mention disclaimers unaffected — no CLI strings added).

- [ ] **Step 4: Commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
  git add skills/delegate/SKILL.md skills/sdd/SKILL.md && \
  git commit -m "docs(step0): drift advisory is routed-provider-scoped (lockstep with validate-packs)"
```

---

## Self-Review

- **Spec coverage:** Part A (probe routed only; strict keeps full loop), control-flow reorder, and drift-semantics narrowing are all in Task 1 (script + tests) and Task 2 (skills). Part B/C are out of scope (follow-up plan).
- **Placeholder scan:** none — code and tests are concrete.
- **Type consistency:** reuses existing `check_provider_version` / `check_provider_readiness` / `resolve_models` signatures verbatim; no renamed symbols.
- **Note for executor:** Tasks 1 and 2 are a single living-document change — land both before merging; do not ship the script change without the skill lockstep.
