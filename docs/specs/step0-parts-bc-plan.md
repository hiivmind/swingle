# Step-0 Parts B & C — Honest Auth + Optional Probe Cache — Implementation Plan (follow-up)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (B) Stop reporting a logged-out provider as `ready:` when its readiness is only a `--version` fallback; (C) *optionally* cache expensive per-provider version/drift probes across sessions — never gates, routing, or auth.

**Architecture:** Part B adds a third Step-0 readiness outcome, `available (auth unverified):`, emitted when the routed pack has no real `readiness-argv`; both skills' outcome tables gain the row. Part C adds a narrow `~/.cache` receipt caching only version/drift results keyed by a strong CLI identity, with live routing/gate/readiness always recomputed.

**Tech Stack:** Python 3 stdlib (`scripts/validate-packs`, `fcntl` for locking), pytest, Markdown skills, `swingle-setup` skill.

## Global Constraints

- Purity boundary: `skills/**` contains no CLI-invocation strings (enforced). All CLI spawning stays in `validate-packs`.
- Living-document lockstep: Step-0 outcome table is normative; script is its executable rendering — change together.
- Hard gate before every commit, chained with `&&`: `python3 scripts/validate-packs --root . && ./scripts/codex-smoke && git commit ...`.
- Part C caches **only** version/drift probe results — never a gate, routing input, or auth/readiness verdict.
- Design source: `docs/specs/warm-start-receipt-design.md` Parts B & C + "Review history".

## ⚠️ Part C gate (both design reviewers)

**Do not start Part C (Task 5+) until Part A (`docs/specs/step0-part-a-plan.md`) is merged and rebenchmarked.** After Part A only the routed provider is probed, and for the four fallback providers its version is parsed from the live readiness call — so Part C saves at most one `version-argv` spawn for a routed `grok`/`opencode` dispatch. If that residual is negligible, **cancel Part C** and ship only Part B. Record the post-Part-A `--step0` timing here before deciding: `__________`.

---

## Part B — Honest readiness/auth semantics (independently shippable)

### Task 1: `--step0` emits `available (auth unverified):` for fallback-readiness providers

**Files:**
- Modify: `scripts/validate-packs` — the readiness print at the end of the `--step0` route block (`ready: {chosen}` line).
- Test: `tests/test_validate_packs.py`

**Interfaces:**
- Consumes: `manifests[chosen]` (the routed pack's parsed front-matter); `check_provider_readiness`.
- Produces: a new stdout token `available (auth unverified): <id>` alongside the existing `ready: <id>` and `CHANNEL: provider not ready`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_validate_packs.py`:

```python
def test_step0_ready_when_real_readiness_probe(tmp_path):
    """A pack that declares a real readiness-argv reports ready: on success."""
    r = run("--step0", "--root", str(FIX / "good-lanes"),
            "--path-dir", str(FIX / "bins-alpha"), "--role", "per-task reviewer")
    assert r.returncode == 0 and "ready: alpha" in r.stdout

def test_step0_auth_unverified_when_readiness_falls_back(tmp_path):
    """A pack with no readiness-argv falls back to --version, which cannot prove
    auth, so report 'available (auth unverified):', never 'ready:'."""
    cfg = tmp_path / "lane-beta.json"
    cfg.write_text('{"providers_by_lane": {"review": "beta"}}')
    r = run("--step0", "--root", str(FIX / "good-two-providers"),
            "--path-dir", str(FIX / "bins-two"), "--config", str(cfg),
            "--role", "per-task reviewer")
    assert r.returncode == 0
    assert "provider: beta" in r.stdout
    assert "available (auth unverified): beta" in r.stdout
    assert "ready: beta" not in r.stdout
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --with pytest pytest tests/test_validate_packs.py::test_step0_auth_unverified_when_readiness_falls_back -q`
Expected: FAIL — current code prints `ready: beta` regardless of readiness-argv presence.

- [ ] **Step 3: Branch the readiness print on `readiness-argv` presence**

In `scripts/validate-packs`, replace the final readiness block of the `--step0` route (`if rc != 0: find(CHANNEL) else: print("ready: …")`) with:

```python
                    rc, _ = check_provider_readiness(manifests[chosen], a.path_dir, int(manifests[chosen].get("readiness-timeout-seconds", 30)))
                    if rc != 0:
                        find(f"CHANNEL: provider not ready: {chosen} (exit {rc})")
                    elif manifests[chosen].get("readiness-argv"):
                        print(f"ready: {chosen}")
                    else:
                        # readiness fell back to version-argv — proves CLI availability, not auth.
                        print(f"available (auth unverified): {chosen}")
```

- [ ] **Step 4: Run to verify pass + no regression**

Run: `uv run --with pytest pytest tests/test_validate_packs.py -q`
Expected: PASS. Note: `test_step0_channel_prefix_on_not_ready` (readiness rc != 0) still yields `CHANNEL:`; `test_step0_lane_routing_and_resolution` (good-two-providers beta, no readiness-argv) may now print `available (auth unverified): beta` instead of `ready:` — update that assertion if it checks the readiness token (it currently asserts only `provider: beta` and `model:`, so it passes unchanged).

- [ ] **Step 5: Commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
  git add scripts/validate-packs tests/test_validate_packs.py && \
  git commit -m "feat(step0): report 'available (auth unverified)' when readiness is a --version fallback"
```

### Task 2: Skill lockstep — add the `available (auth unverified)` outcome row

**Files:**
- Modify: `skills/delegate/SKILL.md` — Step-0 outcome table + readiness phase prose.
- Modify: `skills/sdd/SKILL.md` — same.

- [ ] **Step 1: Add the row to `skills/delegate/SKILL.md` outcome table**

After the `ready`/exit-0 row, add:

```
| `available (auth unverified): <id>` (exit 0) | routed CLI is present but its readiness is a `--version` fallback that cannot prove auth | proceed; auth is unverified, so a channel failure on THIS dispatch is a provider-wide STOP (Failure handling), not a candidate glitch |
```

Update the readiness-phase prose to: `→ readiness (the pack's bounded probe; a real readiness-argv yields ready:/CHANNEL, a version-argv fallback yields available (auth unverified))`.

- [ ] **Step 2: Apply the identical edits to `skills/sdd/SKILL.md`.**

- [ ] **Step 3: Verify skill suites**

Run: `uv run --with pytest pytest tests/test_delegate_skill.py tests/test_setup_skill.py -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
  git add skills/delegate/SKILL.md skills/sdd/SKILL.md && \
  git commit -m "docs(step0): add 'available (auth unverified)' outcome row (lockstep)"
```

### Task 3: Manifest completeness — real `readiness-argv` per dispatchable provider (verification-gated)

**Files:**
- Modify: `providers/<id>/pack.md` for each of `agy`, `claude`, `codex`, `pi` — **only after live verification**.
- Modify: `README.md` "Adding a provider" notes if the guidance changes.

**This task cannot be completed from code alone** — each candidate readiness command must be confirmed to (a) require auth (fails cleanly when logged out) and (b) be cheap and non-mutating. Do NOT invent `readiness-argv` values.

- [ ] **Step 1:** For each provider, per `swingle-verify <id>`, identify a candidate authenticated read (e.g. a `whoami`/`models`/`session list` equivalent from the provider's `--help`). Record the exact argv.
- [ ] **Step 2:** Verify logged-in: the command exits 0 within the pack's `readiness-timeout-seconds`. Verify logged-out (or with a revoked token): it exits non-zero. Only a command that distinguishes the two qualifies.
- [ ] **Step 3:** Add `readiness-argv: [...]` to that pack's manifest; run `python3 scripts/validate-packs --root .` (argv grammar is validated).
- [ ] **Step 4:** Append the verification evidence to the provider's log shard per `core/verification-protocol.md` Recording.
- [ ] **Step 5:** Commit per provider. A provider with no qualifying command stays on the honest `available (auth unverified)` path — that is an acceptable terminal state, not a gap.

---

## Part C — Optional cross-session probe cache (gated; see the ⚠️ gate above)

### Task 4: Receipt I/O + strong identity (module functions, no wiring yet)

**Files:**
- Modify: `scripts/validate-packs` — add receipt helpers near `resolve_models`.
- Test: `tests/test_validate_packs.py`

**Interfaces:**
- Produces: `receipt_path() -> Path`; `cli_identity(fm, path_dirs) -> dict|None` = `{"exe","version","verified"}`; `load_receipt_trusted(path) -> dict|None`; `write_receipt_merge(path, provider_id, entry, universe) -> None`.

- [ ] **Step 1: Write failing tests**

```python
def test_receipt_untrusted_is_cold_miss(tmp_path, monkeypatch):
    p = tmp_path / "receipt.json"
    p.write_text('{"schema": 1, "providers": {}}')
    p.chmod(0o666)  # group/other writable -> untrusted
    assert vp.load_receipt_trusted(p) is None
    p.chmod(0o600); p.write_text("{ not json")
    assert vp.load_receipt_trusted(p) is None
    p.write_text('{"schema": 999}')
    assert vp.load_receipt_trusted(p) is None

def test_receipt_merge_preserves_other_providers(tmp_path):
    p = tmp_path / "receipt.json"
    vp.write_receipt_merge(p, "alpha", {"version": "1.0.0", "drift": False}, ["alpha", "beta"])
    vp.write_receipt_merge(p, "beta", {"version": "2.0.0", "drift": True}, ["alpha", "beta"])
    data = vp.load_receipt_trusted(p)
    assert set(data["providers"]) == {"alpha", "beta"}
    assert data["providers"]["alpha"]["version"] == "1.0.0"
```

- [ ] **Step 2: Run to verify failure** (`AttributeError: load_receipt_trusted`).

- [ ] **Step 3: Implement the helpers**

```python
import fcntl, stat as _stat
RECEIPT_SCHEMA = 1

def receipt_path():
    cache = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return Path(cache) / "swingle" / "receipt.json"

def cli_identity(fm, path_dirs):
    cli = fm.get("cli", "")
    resolved = next((os.path.realpath(Path(d) / cli) for d in get_path_dirs(path_dirs)
                     if (Path(d) / cli).exists() and os.access(Path(d) / cli, os.X_OK)), None)
    if not resolved:
        return None
    _, _, ver = check_provider_version(fm, path_dirs, int(fm.get("readiness-timeout-seconds", 30)))
    return {"exe": resolved, "version": ver, "verified": fm.get("verified-version")}

def load_receipt_trusted(path):
    try:
        st = os.lstat(path)
    except OSError:
        return None
    if _stat.S_ISLNK(st.st_mode) or not _stat.S_ISREG(st.st_mode):
        return None
    if st.st_uid != os.getuid() or (st.st_mode & 0o022):
        return None
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("schema") != RECEIPT_SCHEMA:
        return None
    return data

def write_receipt_merge(path, provider_id, entry, universe):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    with open(lock, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)      # serialize read-merge-write across sessions
        data = load_receipt_trusted(path) or {"schema": RECEIPT_SCHEMA, "providers": {}}
        data["schema"] = RECEIPT_SCHEMA
        data.setdefault("providers", {})[provider_id] = entry
        data["universe"] = sorted(universe)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(data)); os.replace(tmp, path)
        fcntl.flock(lf, fcntl.LOCK_UN)
```

- [ ] **Step 4: Run to verify pass.** Run: `uv run --with pytest pytest tests/test_validate_packs.py -k receipt -q`. Expected: PASS.
- [ ] **Step 5: Commit** (`feat(receipt): trusted receipt I/O + strong CLI identity`).

### Task 5: `--step0 --write-receipt <path>` self-heals the routed entry

**Files:** Modify `scripts/validate-packs` (`main()` argparse + the `--step0` clean-route tail); Test `tests/test_validate_packs.py`.

- [ ] **Step 1:** Failing test: after a clean `--step0 --write-receipt <p>`, `load_receipt_trusted(p)["providers"]` contains the routed provider with `version`/`drift`, and `universe` lists all installed providers.
- [ ] **Step 2:** Run → fail (unknown arg `--write-receipt`).
- [ ] **Step 3:** Add `ap.add_argument("--write-receipt")`. After the routed-provider drift probe in `--step0` (Part A), when `a.write_receipt` and no `findings`, call `write_receipt_merge(Path(a.write_receipt), chosen, {"version": actual_ver, "drift": bool(...), "identity": cli_identity(manifests[chosen], a.path_dir)}, installed)`.
- [ ] **Step 4:** Run → pass; full suite green.
- [ ] **Step 5:** Commit.

### Task 6: `--check-receipt` warm path (field-by-field; live routing + readiness)

**Files:** Modify `scripts/validate-packs` (`main()`); Test `tests/test_validate_packs.py`.

**Interface / algorithm (authoritative):** `--check-receipt <path> --root <root> --role <r> --project <repo> [--config <f>] [--task-provider <id>|--lever ...] [--path-dir ...]`:
1. `load_receipt_trusted(path)`; `None` → print `cold: no-trusted-receipt` and exit 1.
2. Recompute **live**: config load+gate, provider detection, `installed`/`active`, routing → `chosen` (identical code path to `--step0`). If `installed` set != `receipt["universe"]` → `cold: universe-changed`, exit 1.
3. Recompute `cli_identity(manifests[chosen], path_dir)`; if it != `receipt["providers"][chosen]["identity"]` → `cold: identity-changed <chosen>`, exit 1.
4. Emit cached `provider:`/`model:` (model re-resolved live via `resolve_models` — never cached) + the cached drift `warning:` if `drift`.
5. Always run the **live** routed readiness probe and emit `ready:`/`available (auth unverified):`/`CHANNEL:` (Part B rules). Nothing about routing or the gate comes from the cache.

- [ ] **Step 1:** Failing tests: (a) warm hit on an unchanged env prints `provider:`+`model:`+ a readiness token and exit 0; (b) after removing a provider from `universe` (or PATH change) it prints `cold: universe-changed`; (c) missing/untrusted receipt prints `cold: no-trusted-receipt`.
- [ ] **Step 2:** Run → fail (unknown arg).
- [ ] **Step 3:** Implement the `elif a.check_receipt:` branch per the algorithm above, reusing the routing/resolution/readiness helpers.
- [ ] **Step 4:** Run → pass; full suite green.
- [ ] **Step 5:** Commit.

### Task 7: Concurrency — no lost update under simultaneous writers

**Files:** Test `tests/test_validate_packs.py` (the lock is already in Task 4).

- [ ] **Step 1:** Test: spawn two `write_receipt_merge` calls for distinct providers from two threads/processes against the same path; assert the final receipt contains BOTH entries (no lost update). Use `concurrent.futures` or `multiprocessing`.
- [ ] **Step 2:** Run → PASS with the Task-4 `flock`. If it flakes, the lock is wrong — fix Task 4, not the test.
- [ ] **Step 3:** Commit.

### Task 8: Skill Step-0 warm-first integration (both skills, lockstep)

**Files:** Modify `skills/delegate/SKILL.md` and `skills/sdd/SKILL.md` Step-0 + outcome tables.

- [ ] **Step 1:** In both skills, insert the warm-first step: run `validate-packs --check-receipt <cache-path> --root <root> --role <r> --project <repo> [levers]` first; on `warm` (exit 0, `provider:`/`model:`/readiness token) proceed; on any `cold: <reason>` (exit 1) fall through to `--step0 --write-receipt <cache-path>` and adjudicate its outcome as today.
- [ ] **Step 2:** Add outcome-table rows: `warm` → proceed; `cold: <reason>` → run `--step0` (self-heal). Preserve the SDD per-task rerun rule (rerun when role/provider/native/lane inputs differ).
- [ ] **Step 3:** `uv run --with pytest pytest tests/test_delegate_skill.py tests/test_setup_skill.py -q` → PASS (no CLI strings added to skills; the flags live in the documented command line, same as the existing `--step0` invocation already present in the skill).
- [ ] **Step 4:** Commit.

### Task 9: Setup writes the receipt with consent (all installed providers)

**Files:** Modify `skills/swingle-setup/SKILL.md` (Phase A report + Phase C offer); possibly `scripts/validate-packs` if a batch `--write-receipt` over all providers is added.

- [ ] **Step 1:** Phase A: report receipt freshness (present with matching universe / stale / absent) from `load_receipt_trusted` + a live universe compare.
- [ ] **Step 2:** Phase C: one consented item — authoritative write covering all installed providers (loop `--step0 --write-receipt` per provider, or a batch mode). Re-inspect after write (before→after), per setup doctrine.
- [ ] **Step 3:** `uv run --with pytest pytest tests/test_setup_skill.py -q` → PASS.
- [ ] **Step 4:** Commit.

---

## Self-Review

- **Spec coverage:** Part B (§Part B) = Tasks 1–3; Part C (§Part C) = Tasks 4–9, covering strong identity, universe-awareness, lock/CAS, untrusted=cold-miss, live routing+readiness, warm-path skill integration, setup write. All map to `warm-start-receipt-design.md` Parts B/C.
- **Placeholder scan:** Part B and Task 4 carry concrete code + tests. Tasks 5–9 give the authoritative algorithm/interface and concrete test assertions; Task 3 is explicitly verification-gated (values cannot be fabricated — that is a correctness requirement, not a placeholder).
- **Type consistency:** `cli_identity`/`load_receipt_trusted`/`write_receipt_merge` signatures are used identically in Tasks 5–6; `receipt_path()` and `RECEIPT_SCHEMA` are shared.
- **Independence:** Part B ships without Part C. Part C is gated on the Part A rebenchmark and may be cancelled — record the number in the ⚠️ gate before starting Task 5.
