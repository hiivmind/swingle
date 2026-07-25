# Layered YAML Model Tables Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move each provider's model priority table from a markdown table in `providers/<id>/models.md` to `providers/<id>/models.yaml`, resolved through a layered whole-file-precedence walk (`$SDD_DISPATCH_MODELS` env dir → project `.sdd-dispatch/models/` → XDG user dir → plugin default), per the approved spec `docs/superpowers/specs/2026-07-24-layered-model-config-design.md`.

**Architecture:** `scripts/validate-packs` (stdlib-only, single file) gains a restricted-YAML parser and a layered resolver; it stays the single resolution authority (`--resolve`/`--step0` gain `--project`). A new `scripts/sdd-models` helper (init/which) imports the same resolver. The five shipped packs and the test fixtures migrate their tables to `models.yaml`; `models.md` remains as documentary prose guarded against carrying eligible rows. Skills, core docs, README, and the verify skill update in the same PR.

**Tech Stack:** Python 3 stdlib only (NO PyYAML — the validator's first line promises "stdlib only" and the hard gate runs under bare `python3`; CI installs pytest only). `models.yaml` files are valid YAML authored in a restricted grammar the stdlib parser accepts — same philosophy as the pack.md front-matter grammar.

## Global Constraints

- Branch: `feature/layered-model-config`; PR targets `develop`. Never push to `main`.
- Hard gate before EVERY commit, chained with `&&`, never `;`:
  `python3 scripts/validate-packs --root . && ./scripts/codex-smoke && git commit …`
- Purity boundary: model ids and invocation strings never appear in `core/`, `contracts/`, or `skills/**` (enforced by `tests/test_delegate_skill.py`). Provider *names* are allowed in `core/`.
- Verification logs are append-only; this plan never edits any `verification-log.md`.
- `tests/fixtures/p13/` is an evidence artifact — do not touch it.
- Version lands at **1.8.0** in `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, and the README `**Version:**` line (Task 7 only — earlier tasks leave 1.7.0).
- Test command: `uv run --with pytest pytest tests/ -q` (all tests), or `-k <name>` for one.
- Restricted models.yaml grammar (the contract for every file this plan writes):
  top-level `schema: 1`, `provider: <id>`, `models:` (block list or literal `[]`);
  rows start `  - tier: …` (two spaces, dash, space) and continue `    key: value`
  (four spaces); scalars are bare or double-quoted (no single quotes, no flow
  mappings, no anchors); `#` comments allowed on their own line or after a value.
  Row keys: required `tier, lane, priority, model, status`; optional `pricing, rationale`;
  anything else is an error.

---

### Task 1: Restricted-YAML parser + per-file validation in validate-packs

**Files:**
- Modify: `scripts/validate-packs` (add parser + row checks; wire pack loop to prefer `models.yaml` when present)
- Create: `tests/fixtures/good-yaml/providers/alpha/models.yaml`, plus copies of `pack.md`, `models.md` (documentary only), `verification-log.md` from `tests/fixtures/good-lanes/providers/alpha/`
- Create: `tests/fixtures/bad-yaml-unknown-key/…`, `tests/fixtures/bad-yaml-schema/…` (same copy pattern, broken `models.yaml`)
- Test: `tests/test_validate_packs.py`

**Interfaces:**
- Produces: `parse_models_yaml(path: Path, provider_id: str) -> list[dict]` returning rows shaped exactly like `parse_models` today: `{"tier": str, "lane": str, "prio": int, "model": str, "status": str}` — so `candidate_order` needs no change. Errors go through the module-global `find()`.
- Produces: `check_rows(label: str, rows: list[dict]) -> None` — the duplicate-priority and priority-1-per-(tier,lane) checks, factored out of `parse_models` so both formats share them.
- Transition behavior (until Task 3): a pack with `models.yaml` is validated from YAML (and its `models.md` must carry no eligible table row); a pack without one falls back to the current md-table path. The real tree (all md) stays green.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_validate_packs.py`:

```python
def test_yaml_pack_valid_and_resolvable():
    r = run("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha")
    assert r.returncode == 0 and "review-model-exact" in r.stdout

def test_yaml_unknown_row_key_fails():
    r = run("--root", str(FIX / "bad-yaml-unknown-key"))
    assert r.returncode == 1 and "unknown row key" in r.stdout

def test_yaml_bad_schema_or_provider_fails():
    r = run("--root", str(FIX / "bad-yaml-schema"))
    assert r.returncode == 1 and "schema" in r.stdout and "provider" in r.stdout

def test_yaml_pack_clean_tree_passes():
    r = run("--root", str(FIX / "good-yaml"))
    assert r.returncode == 0

def test_yaml_eligible_md_row_guard(tmp_path):
    import shutil as _sh
    root = tmp_path / "drift"; _sh.copytree(FIX / "good-yaml", root)
    md = root / "providers" / "alpha" / "models.md"
    md.write_text(md.read_text() +
        "\n| cheapest | any | 9 | sneaky-model | verified | - | drift |\n")
    r = run("--root", str(root))
    assert r.returncode == 1 and "eligible" in r.stdout
```

- [ ] **Step 2: Create the fixtures**

```bash
mkdir -p tests/fixtures/good-yaml/providers/alpha
cp tests/fixtures/good-lanes/providers/alpha/pack.md tests/fixtures/good-yaml/providers/alpha/
cp tests/fixtures/good-lanes/providers/alpha/verification-log.md tests/fixtures/good-yaml/providers/alpha/
```

Write `tests/fixtures/good-yaml/providers/alpha/models.md` (documentary only — no table):

```markdown
# alpha models

The table of record is [models.yaml](models.yaml). This file carries narrative only.
```

Write `tests/fixtures/good-yaml/providers/alpha/models.yaml`:

```yaml
schema: 1
provider: alpha
models:
  - tier: cheapest
    lane: any
    priority: 1
    model: cheap-any-model
    status: verified
  - tier: standard
    lane: review
    priority: 1
    model: review-model-exact
    status: verified
    pricing: "$1/$2"  # trailing comment exercises the grammar
    rationale: "test row"
  - tier: standard
    lane: any
    priority: 1
    model: review-model-any
    status: verified
```

Then `cp -r tests/fixtures/good-yaml tests/fixtures/bad-yaml-unknown-key` and in its `models.yaml` change the `rationale:` line to `rationalle: "typo"`. `cp -r tests/fixtures/good-yaml tests/fixtures/bad-yaml-schema` and in its `models.yaml` change the header to `schema: 2` / `provider: wrong-name`.

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_validate_packs.py -q -k yaml`
Expected: FAIL — the validator currently reports `good-yaml…/models.md` has "no priority 1 row"/parses nothing useful (no YAML support yet).

- [ ] **Step 4: Implement parser + checks in `scripts/validate-packs`**

Add after the `parse_front_matter` function:

```python
MODEL_ROW_KEYS = {"tier", "lane", "priority", "model", "status", "pricing", "rationale"}
MODEL_ROW_REQ = ("tier", "lane", "priority", "model", "status")
Y_TOP_RE = re.compile(r"^([a-z]+):\s*(.*)$")
Y_FIRST_RE = re.compile(r"^  - ([a-z]+):\s*(.*)$")
Y_CONT_RE = re.compile(r"^    ([a-z]+):\s*(.*)$")

def yaml_scalar(path, n, raw):
    """One restricted-grammar scalar: bare or double-quoted, optional trailing comment."""
    raw = raw.strip()
    if raw.startswith('"'):
        end = raw.find('"', 1)
        if end == -1: find(f"{path}:{n}: unterminated quote"); return None
        trailing = raw[end + 1:].strip()
        if trailing and not trailing.startswith("#"): find(f"{path}:{n}: trailing content after quote"); return None
        return raw[1:end]
    return raw.split("#", 1)[0].strip()

def parse_models_yaml(path, provider_id):
    """Restricted-YAML models file (spec 2026-07-24): flat header + fixed-shape row list."""
    header, raw_rows, current = {}, [], None
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"): continue
        if "'" in line: find(f"{path}:{n}: grammar violation: single quotes"); continue
        m_first, m_cont = Y_FIRST_RE.match(line), Y_CONT_RE.match(line)
        m_top = Y_TOP_RE.match(line) if not line.startswith(" ") else None
        if m_first:
            if current is not None: raw_rows.append(current)
            current, key, value = {}, m_first.group(1), yaml_scalar(path, n, m_first.group(2))
        elif m_cont and current is not None:
            key, value = m_cont.group(1), yaml_scalar(path, n, m_cont.group(2))
        elif m_top:
            key, raw = m_top.group(1), m_top.group(2)
            if key == "models":
                bare = raw.split("#", 1)[0].strip()
                if bare not in ("", "[]"): find(f"{path}:{n}: models must be a block list or []")
                continue
            if key in header: find(f"{path}:{n}: duplicate key {key}")
            header[key] = yaml_scalar(path, n, raw)
            continue
        else:
            find(f"{path}:{n}: grammar violation: {line!r}"); continue
        if key not in MODEL_ROW_KEYS: find(f"{path}:{n}: unknown row key {key}"); continue
        if key in current: find(f"{path}:{n}: duplicate row key {key}"); continue
        current[key] = value
    if current is not None: raw_rows.append(current)
    if str(header.get("schema")) != "1": find(f"{path}: schema must be 1 (got {header.get('schema')})")
    if header.get("provider") != provider_id: find(f"{path}: provider must be {provider_id} (got {header.get('provider')})")
    for key in header:
        if key not in {"schema", "provider"}: find(f"{path}: unknown key {key}")
    rows = []
    for row in raw_rows:
        missing = [k for k in MODEL_ROW_REQ if k not in row]
        if missing: find(f"{path}: row missing {' '.join(missing)}"); continue
        if row["tier"] not in TIERS: find(f"{path}: bad tier {row['tier']}"); continue
        if row["lane"] not in LANES: find(f"{path}: bad lane {row['lane']}")
        if row["status"] not in STATUSES: find(f"{path}: bad status {row['status']}")
        if not str(row["priority"]).isdigit() or int(row["priority"]) < 1: find(f"{path}: bad priority {row['priority']}")
        else: rows.append({"tier": row["tier"], "lane": row["lane"], "prio": int(row["priority"]), "model": row["model"], "status": row["status"]})
    return rows

def check_rows(label, rows):
    seen = set()
    for row in rows:
        key = row["tier"], row["lane"], row["prio"]
        if key in seen: find(f"{label}: duplicate priority {key}")
        seen.add(key)
    for tier_lane in {(row["tier"], row["lane"]) for row in rows}:
        if not any(row["prio"] == 1 for row in rows if (row["tier"], row["lane"]) == tier_lane): find(f"{label}: {tier_lane} has no priority 1 row")

def check_md_has_no_eligible_rows(pack):
    """Eligible-row guard: once models.yaml is the table of record, models.md may keep
    prose and documentary tables but never an eligible-status tier row (table rows only —
    prose mentions are out of scope by design)."""
    for n, line in enumerate((pack / "models.md").read_text().splitlines(), 1):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and line.lstrip().startswith("|") and cells[0] in TIERS and cells[4] in ELIGIBLE:
            find(f"{pack}/models.md:{n}: eligible-row guard: eligible status row belongs in models.yaml")
```

In `parse_models`, delete its trailing duplicate/priority-1 block (the `seen = set()` … `has no priority 1 row` lines) and end it with `check_rows(f"{pack}/models.md", rows); return rows` instead.

In `main()`, replace the pack loop body line

```python
        if (pack / "models.md").exists(): rows_by_id[pack.name] = parse_models(pack)
```

with

```python
        if (pack / "models.yaml").exists():
            rows = parse_models_yaml(pack / "models.yaml", pack.name)
            check_rows(f"{pack}/models.yaml", rows)
            rows_by_id[pack.name] = rows
            if (pack / "models.md").exists(): check_md_has_no_eligible_rows(pack)
        elif (pack / "models.md").exists(): rows_by_id[pack.name] = parse_models(pack)
```

- [ ] **Step 5: Run the yaml tests, then the full suite**

Run: `uv run --with pytest pytest tests/ -q`
Expected: all PASS (real tree still md-based and green; yaml fixtures green).

- [ ] **Step 6: Commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
git add scripts/validate-packs tests/ && \
git commit -m "feat(validator): restricted-YAML models.yaml parser + eligible-row guard"
```

---

### Task 2: Layered resolution (env → project → user → default) in --resolve/--step0

**Files:**
- Modify: `scripts/validate-packs` (layer walk, `--project` flag, `layer:` output line, override no-cover message)
- Create: `tests/fixtures/proj-override/.sdd-dispatch/models/alpha.yaml`
- Test: `tests/test_validate_packs.py`

**Interfaces:**
- Consumes: `parse_models_yaml`, `check_rows` from Task 1.
- Produces: `resolve_models(provider_id: str, root: Path, project: str|None) -> tuple[str|None, Path|None, list[dict]]` returning `(layer, path, rows)` where layer ∈ {"env","project","user","default"}; STOPs via `find()` when `$SDD_DISPATCH_MODELS` is set but not a directory, or when a found file is malformed (whole-file precedence: a found file is never skipped). Task 5's `sdd-models` imports exactly this function.
- Produces: `--resolve`/`--step0` print `layer: <layer> path=<absolute path>` (spec-pinned format) before the existing model line. Bare validation runs (no `--resolve`/`--step0`) validate ONLY the plugin-default files — never the developer's user/env layers, so repo validation stays hermetic.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_validate_packs.py` (note the new `env=` support in `run`):

```python
import os

def run_env(*args, **env):
    e = dict(os.environ, XDG_CONFIG_HOME=str(FIX / "no-such-xdg"))
    e.pop("SDD_DISPATCH_MODELS", None)
    e.update(env)
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=e)

def test_resolve_default_layer_line():
    r = run_env("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha")
    assert r.returncode == 0
    assert "layer: default path=" in r.stdout and "models.yaml" in r.stdout

def test_resolve_project_layer_wins():
    r = run_env("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha",
                "--project", str(FIX / "proj-override"))
    assert r.returncode == 0
    assert "layer: project path=" in r.stdout and "project-review-model" in r.stdout

def test_resolve_env_layer_beats_project(tmp_path):
    env_dir = tmp_path / "envmodels"; env_dir.mkdir()
    (env_dir / "alpha.yaml").write_text(
        "schema: 1\nprovider: alpha\nmodels:\n"
        "  - tier: standard\n    lane: review\n    priority: 1\n"
        "    model: env-review-model\n    status: experimental\n")
    r = run_env("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha",
                "--project", str(FIX / "proj-override"), SDD_DISPATCH_MODELS=str(env_dir))
    assert r.returncode == 0
    assert "layer: env path=" in r.stdout and "env-review-model" in r.stdout

def test_env_layer_unreadable_stops(tmp_path):
    r = run_env("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha",
                SDD_DISPATCH_MODELS=str(tmp_path / "missing-dir"))
    assert r.returncode == 1 and "SDD_DISPATCH_MODELS" in r.stdout

def test_override_not_covering_slot_asks_with_path(tmp_path):
    proj = tmp_path / "proj"; (proj / ".sdd-dispatch" / "models").mkdir(parents=True)
    (proj / ".sdd-dispatch" / "models" / "alpha.yaml").write_text(
        "schema: 1\nprovider: alpha\nmodels: []\n")
    r = run_env("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha",
                "--project", str(proj))
    assert r.returncode == 1
    assert "no eligible model" in r.stdout and "does not cover" in r.stdout

def test_malformed_override_stops_never_falls_through(tmp_path):
    proj = tmp_path / "proj"; (proj / ".sdd-dispatch" / "models").mkdir(parents=True)
    (proj / ".sdd-dispatch" / "models" / "alpha.yaml").write_text("models: {broken\n")
    r = run_env("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha",
                "--project", str(proj))
    assert r.returncode == 1 and "layer: default" not in r.stdout
```

Create `tests/fixtures/proj-override/.sdd-dispatch/models/alpha.yaml`:

```yaml
schema: 1
provider: alpha
models:
  - tier: standard
    lane: review
    priority: 1
    model: project-review-model
    status: experimental
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_validate_packs.py -q -k "layer or override or env_layer"`
Expected: FAIL — `--project` is an unknown argument.

- [ ] **Step 3: Implement the layer walk**

In `scripts/validate-packs`, add after `check_rows`:

```python
def resolve_models(provider_id, root, project):
    """Layered models.yaml walk (spec 2026-07-24): env -> project -> user -> default.
    First file found is the whole table; a found-but-malformed file is a STOP, never
    a fall-through."""
    env_dir = os.environ.get("SDD_DISPATCH_MODELS")
    if env_dir and not Path(env_dir).is_dir():
        find(f"SDD_DISPATCH_MODELS set but not a readable directory: {env_dir}")
        return None, None, []
    layers = []
    if env_dir: layers.append(("env", Path(env_dir) / f"{provider_id}.yaml"))
    if project: layers.append(("project", Path(project) / ".sdd-dispatch" / "models" / f"{provider_id}.yaml"))
    xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    layers.append(("user", Path(xdg) / "sdd-dispatch" / "models" / f"{provider_id}.yaml"))
    layers.append(("default", root / "providers" / provider_id / "models.yaml"))
    for layer, path in layers:
        if path.exists():
            rows = parse_models_yaml(path, provider_id)
            check_rows(f"{path}", rows)
            return layer, path, rows
    return None, None, []
```

Add the flag in `main()`'s argparse line: `ap.add_argument("--project")`.

Rewrite the `elif a.resolve:` branch:

```python
    elif a.resolve:
        role, provider = a.resolve[0].lower(), a.resolve[1]; roles = parse_roles(root); tier_lane = next((value for key, value in roles.items() if role in key), None)
        if not tier_lane: find(f"unknown role: {role}")
        elif provider not in rows_by_id: find(f"unknown provider: {provider}")
        else:
            layer, layer_path, rows = resolve_models(provider, root, a.project)
            if layer is None and not findings: layer, layer_path, rows = "default", None, rows_by_id[provider]
            if layer_path is not None: print(f"layer: {layer} path={layer_path.resolve()}")
            order = candidate_order(rows, *tier_lane, excluded.get(provider, set()))
            if order: print(f"{role} -> {tier_lane} -> {order[0]['model']} (P{order[0]['prio']}, {order[0]['status']}); fallback order: {', '.join(row['model'] for row in order)}")
            elif layer in ("env", "project", "user"): find(f"no eligible model for {tier_lane} in {provider} — override at {layer_path} does not cover {tier_lane}")
            else: find(f"no eligible model for {tier_lane} in {provider}")
```

(The `layer is None and not findings` line covers the Task-1→Task-3 transition window where a pack still has only `models.md`; after Task 3 every pack has a default `models.yaml` and it is dead code you then remove.)

In the `--step0` model-resolution block, replace

```python
                        order = candidate_order(rows_by_id.get(chosen, []), *role_tier_lane, excluded.get(chosen, set()))
```

with

```python
                        layer, layer_path, layer_rows = resolve_models(chosen, root, a.project)
                        if layer is None and not findings: layer_rows = rows_by_id.get(chosen, [])
                        elif layer_path is not None: print(f"layer: {layer} path={layer_path.resolve()}")
                        order = candidate_order(layer_rows, *role_tier_lane, excluded.get(chosen, set()))
```

and extend its empty-order finding identically (`— override at {layer_path} does not cover …` when `layer` is an override layer).

- [ ] **Step 4: Run the full suite**

Run: `uv run --with pytest pytest tests/ -q`
Expected: all PASS. (Existing `--resolve` tests run against md-based fixtures and keep their current output; the transition line keeps them green.)

- [ ] **Step 5: Commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
git add scripts/validate-packs tests/ && \
git commit -m "feat(validator): layered models resolution (env/project/user/default) with --project"
```

---

### Task 3: Migrate the five shipped packs and all fixtures to models.yaml

**Files:**
- Create: `providers/{codex,agy,opencode,grok,pi}/models.yaml`
- Modify: `providers/{codex,agy,opencode,grok,pi}/models.md` (remove the `## Resolvable` table; add pointer line)
- Modify: fixture packs `tests/fixtures/{good-lanes,good-two-providers,bad-missing-p1,bad-dup-priority,bad-rejected-only}/providers/*/` (tables → models.yaml)
- Modify: `scripts/validate-packs` (models.yaml becomes REQUIRED per pack; delete the md fallback, `parse_models`, and the Task-2 transition lines)
- Modify: `tests/test_delegate_skill.py` (`_model_ids` reads YAML)
- Test: `tests/test_validate_packs.py` (two tests updated in place)

**Interfaces:**
- Consumes: Task 1 parser/guard; Task 2 resolver.
- Produces: every pack directory (real and fixture) satisfies: `models.yaml` present and valid; `models.md` present with no eligible table row. `parse_models` (md tables) no longer exists.

- [ ] **Step 1: Write the five pack YAML files** (transcribed from the current md tables — statuses, priorities, pricing, and rationale carried verbatim; rationale prose stays in models.md where it is narrative)

`providers/codex/models.yaml`:

```yaml
schema: 1
provider: codex
models:
  - tier: cheapest
    lane: any
    priority: 1
    model: gpt-5.6-luna
    status: verified
    pricing: "seat"
    rationale: "transcription/explore; recall ~41% — escalate to terra on large codebases"
  - tier: standard
    lane: any
    priority: 1
    model: gpt-5.6-terra
    status: verified
    pricing: "seat"
    rationale: "workhorse; ~90% recall; default reviewer"
  - tier: most-capable
    lane: any
    priority: 1
    model: gpt-5.6-sol
    status: verified
    pricing: "seat"
    rationale: "final/design review; ~90% recall"
```

`providers/agy/models.yaml`:

```yaml
schema: 1
provider: agy
models:
  - tier: cheapest
    lane: any
    priority: 1
    model: gemini-3.6-flash-low
    status: verified
    rationale: "current Flash workhorse; cheapest dispatch lane"
  - tier: standard
    lane: any
    priority: 1
    model: gemini-3.6-flash-medium
    status: verified
    rationale: "verified 2026-07-23: implement + 2 task reviews + resume, all clean gates"
  - tier: most-capable
    lane: any
    priority: 1
    model: gemini-3.1-pro-high
    status: verified
    rationale: "agy's only Pro; verified 2026-07-23 final whole-branch review"
```

`providers/opencode/models.yaml`:

```yaml
schema: 1
provider: opencode
models:
  - tier: cheapest
    lane: any
    priority: 1
    model: opencode-go/deepseek-v4-flash
    status: verified
    pricing: "$0.14/$0.28"
    rationale: "cheapest paid coder; transcription/explore"
  - tier: standard
    lane: implement
    priority: 1
    model: opencode-go/minimax-m3
    status: verified
    pricing: "$0.30/$1.20"
    rationale: "adaptation (eager — watch over-build)"
  - tier: standard
    lane: implement
    priority: 2
    model: opencode-go/qwen3.7-plus
    status: verified
    pricing: "$0.40/$1.60"
    rationale: "adaptation alternate"
  - tier: standard
    lane: review
    priority: 1
    model: opencode-go/deepseek-v4-pro
    status: verified
    pricing: "$1.74/$3.48"
    rationale: "per-task reviewer (caught planted defect)"
  - tier: most-capable
    lane: implement
    priority: 1
    model: opencode-go/deepseek-v4-pro
    status: verified
    pricing: "$1.74/$3.48"
    rationale: "1M ctx heavy implement"
  - tier: most-capable
    lane: implement
    priority: 2
    model: opencode-go/kimi-k2.7-code
    status: experimental
    rationale: "coding-strong, 256K ctx"
  - tier: most-capable
    lane: review
    priority: 1
    model: opencode-go/glm-5.2
    status: verified
    pricing: "$1.40/$4.40"
    rationale: "final review; #1 open-weights AA 51"
```

`providers/grok/models.yaml`:

```yaml
schema: 1
provider: grok
models:
  - tier: cheapest
    lane: any
    priority: 1
    model: grok-4.5
    status: verified
    pricing: "seat / SuperGrok"
    rationale: "sole inventory row; transcription/explore"
  - tier: standard
    lane: any
    priority: 1
    model: grok-4.5
    status: verified
    pricing: "seat / SuperGrok"
    rationale: "sole inventory row; default implement/review"
  - tier: most-capable
    lane: any
    priority: 1
    model: grok-4.5
    status: verified
    pricing: "seat / SuperGrok"
    rationale: "sole inventory row; final/design review until inventory grows"
```

`providers/pi/models.yaml`:

```yaml
schema: 1
provider: pi
models:
  - tier: cheapest
    lane: any
    priority: 1
    model: opencode-go/deepseek-v4-flash
    status: verified
    pricing: "$0.14/$0.28"
    rationale: "cheapest paid coder; dispatched repeatedly through pi (PONG, read, write, shell)"
  - tier: standard
    lane: implement
    priority: 1
    model: opencode-go/minimax-m3
    status: verified
    pricing: "$0.30/$1.20"
    rationale: "adaptation (eager — watch over-build). PONG through pi"
  - tier: standard
    lane: implement
    priority: 2
    model: opencode-go/qwen3.7-plus
    status: experimental
    pricing: "$0.40/$1.60"
    rationale: "adaptation alternate; in catalog, dispatch-through-pi not yet exercised"
  - tier: standard
    lane: review
    priority: 1
    model: opencode-go/deepseek-v4-pro
    status: verified
    pricing: "$1.74/$3.48"
    rationale: "per-task reviewer. PONG through pi"
  - tier: most-capable
    lane: implement
    priority: 1
    model: opencode-go/deepseek-v4-pro
    status: verified
    pricing: "$1.74/$3.48"
    rationale: "1M-ctx heavy implement. PONG through pi"
  - tier: most-capable
    lane: implement
    priority: 2
    model: opencode-go/kimi-k2.7-code
    status: experimental
    rationale: "coding-strong, 256K ctx; in catalog, dispatch-through-pi not yet exercised"
  - tier: most-capable
    lane: review
    priority: 1
    model: opencode-go/glm-5.2
    status: verified
    pricing: "$1.40/$4.40"
    rationale: "final review; 1M ctx. PONG through pi"
```

- [ ] **Step 2: Trim each shipped models.md**

In each of the five `providers/<id>/models.md`: delete the `## Resolvable` heading and its table (header row, separator, data rows) ONLY. Immediately after the document's opening `#` title line (and any intro paragraph), insert:

```markdown
> The table of record is [models.yaml](models.yaml) (layered overrides: see README
> "Model tables and overrides"). This file carries the documentary layer only —
> verification narrative, watch lists, and corrections.
```

Documentary sections, watch lists, history, and all prose stay byte-identical. Do NOT touch any `verification-log.md`.

- [ ] **Step 3: Migrate the model-table fixtures**

For each fixture pack with a models.md table — `good-lanes/alpha`, `good-two-providers/alpha`, `good-two-providers/beta`, `bad-missing-p1/*`, `bad-dup-priority/*`, `bad-rejected-only/*` (list the actual pack dirs with `ls tests/fixtures/*/providers/`): write the equivalent `models.yaml` (same rows, same defect — e.g. `bad-missing-p1` keeps a slot with only priority 2; `bad-dup-priority` keeps two rows with the same (tier, lane, priority); `bad-rejected-only` keeps its only row `status: rejected`) and replace each fixture `models.md` body with the documentary pointer line from Task 1's `good-yaml` fixture. Fixture packs that test manifest failures only (`bad-argv0`, `bad-empty-argv`, `bad-grammar`, `bad-id-mismatch`, `bad-interpreter-cli`, `bad-metachar`, `bad-shell-detect`) get the same treatment so the required-models.yaml rule passes where their tests expect manifest findings only — copy `good-yaml`'s `models.yaml` adjusting `provider:` to each pack's dirname.

- [ ] **Step 4: Make models.yaml required; delete the md path**

In `scripts/validate-packs` `main()` pack loop, replace the Task-1 block and the required-files loop with:

```python
        for filename in ("models.yaml", "models.md", "verification-log.md"):
            if not (pack / filename).exists(): find(f"{pack}: missing {filename}")
        if (pack / "models.yaml").exists():
            rows = parse_models_yaml(pack / "models.yaml", pack.name)
            check_rows(f"{pack}/models.yaml", rows)
            rows_by_id[pack.name] = rows
            if (pack / "models.md").exists(): check_md_has_no_eligible_rows(pack)
```

Delete the whole `parse_models` function. Delete the two Task-2 transition lines (`if layer is None and not findings: …`) in `--resolve` and `--step0`.

In `tests/test_validate_packs.py`, update two tests in place:
- `test_resolvable_table_rejects_bad_tier` → rename to `test_yaml_rejects_bad_tier`; instead of appending an md row, append to `root/providers/alpha/models.yaml`:
  `"  - tier: premium\n    lane: review\n    priority: 2\n    model: invalid-tier\n    status: verified\n"`; assert `"bad tier premium" in r.stdout`.
- `test_link_scan_checks_relative_target_beginning_with_p` keeps its md-append (models.md still exists) — unchanged.

In `tests/test_delegate_skill.py`, replace `_model_ids` with:

```python
def _model_ids():
    """Every model id declared in any provider's models.yaml."""
    ids = set()
    for models in (ROOT / "providers").glob("*/models.yaml"):
        for line in models.read_text().splitlines():
            m = re.match(r'\s*(?:- )?model:\s*"?([^"\s#]+)"?', line)
            if m:
                ids.add(m.group(1))
    return ids
```

- [ ] **Step 5: Run the full suite and the hard gate**

Run: `uv run --with pytest pytest tests/ -q` then `python3 scripts/validate-packs --root .`
Expected: all PASS; validator exit 0. If the purity test now fails on a skill, a model id leaked — fix the file, don't relax the test.

- [ ] **Step 6: Commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
git add providers/ tests/ scripts/validate-packs && \
git commit -m "feat(packs): models.yaml is the table of record for all five packs"
```

---

### Task 4: `list-models-argv` manifest field

**Files:**
- Modify: `scripts/validate-packs` (one-line OPTIONAL addition)
- Modify: `providers/pi/pack.md` (declare the field)
- Test: `tests/test_validate_packs.py`

**Interfaces:**
- Produces: optional manifest field `list-models-argv` (JSON array of strings, `argv[0] == cli`, metacharacter/absolute-path rejection — all inherited from the generic `-argv` validation). Declared by pi only; opencode's catalog command is NOT declared here because pack facts require live verification — left to the next `sdd-dispatch-verify opencode` round.

- [ ] **Step 1: Write the failing test**

```python
def test_list_models_argv_accepted_and_validated(tmp_path):
    import shutil as _sh
    root = tmp_path / "lm"; _sh.copytree(FIX / "good-yaml", root)
    pack = root / "providers" / "alpha" / "pack.md"
    pack.write_text(pack.read_text().replace(
        "---\n## ", 'list-models-argv: ["alpha", "--list-models"]\n---\n## ', 1))
    assert run("--root", str(root)).returncode == 0
    pack.write_text(pack.read_text().replace(
        '["alpha", "--list-models"]', '["wrong-cli", "--list-models"]'))
    r = run("--root", str(root))
    assert r.returncode == 1 and "argv[0]" in r.stdout
```

(If the fixture pack.md's closing `---` is not followed by `## `, check its actual text first and adapt the replace anchor — the intent is: insert the field as the last front-matter line.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_validate_packs.py -q -k list_models`
Expected: FAIL with "unknown field list-models-argv" in stdout.

- [ ] **Step 3: Implement**

In `scripts/validate-packs`, extend the OPTIONAL set:

```python
OPTIONAL = {"fork-flag", "session-list-argv", "readiness-argv", "readiness-timeout-seconds", "report-transport", "list-models-argv"}
```

In `providers/pi/pack.md` front-matter, add after the `readiness-argv` line:

```yaml
list-models-argv: ["pi", "--list-models"]
```

- [ ] **Step 4: Run tests**

Run: `uv run --with pytest pytest tests/ -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
git add scripts/validate-packs providers/pi/pack.md tests/ && \
git commit -m "feat(manifest): optional list-models-argv field; pi declares its catalog command"
```

---

### Task 5: `scripts/sdd-models` helper (init / which)

**Files:**
- Create: `scripts/sdd-models` (executable, `chmod +x`)
- Test: `tests/test_validate_packs.py` (subprocess tests, same style)

**Interfaces:**
- Consumes: `resolve_models` and `parse_front_matter` — imported from `scripts/validate-packs` via SourceFileLoader (single resolver implementation; no reimplementation of precedence).
- Produces CLI:
  - `sdd-models which [<provider>] [--root R] [--project P]` → one line per provider: `<id>: layer=<layer> path=<abspath>`
  - `sdd-models init <provider> (--project P | --user) [--root R] [--force]` → copies the currently-winning file to the chosen layer; refuses to overwrite without `--force`; prints the pack's `list-models-argv` as a hint when declared (never executes it).

- [ ] **Step 1: Write the failing tests**

```python
SDD_MODELS = ROOT / "scripts" / "sdd-models"

def run_models(*args, **env):
    e = dict(os.environ, XDG_CONFIG_HOME=str(FIX / "no-such-xdg"))
    e.pop("SDD_DISPATCH_MODELS", None)
    e.update(env)
    return subprocess.run([sys.executable, str(SDD_MODELS), *args], capture_output=True, text=True, env=e)

def test_sdd_models_which_default_layer():
    r = run_models("which", "alpha", "--root", str(FIX / "good-yaml"))
    assert r.returncode == 0 and "alpha: layer=default path=" in r.stdout

def test_sdd_models_init_project_seeds_and_refuses_overwrite(tmp_path):
    proj = tmp_path / "proj"; proj.mkdir()
    r = run_models("init", "alpha", "--root", str(FIX / "good-yaml"), "--project", str(proj))
    assert r.returncode == 0
    seeded = proj / ".sdd-dispatch" / "models" / "alpha.yaml"
    assert seeded.exists() and "cheap-any-model" in seeded.read_text()
    r2 = run_models("init", "alpha", "--root", str(FIX / "good-yaml"), "--project", str(proj))
    assert r2.returncode == 1 and "exists" in (r2.stdout + r2.stderr)
    r3 = run_models("init", "alpha", "--root", str(FIX / "good-yaml"), "--project", str(proj), "--force")
    assert r3.returncode == 0

def test_sdd_models_init_user_layer(tmp_path):
    r = run_models("init", "alpha", "--root", str(FIX / "good-yaml"), "--user",
                   XDG_CONFIG_HOME=str(tmp_path / "xdg"))
    assert r.returncode == 0
    assert (tmp_path / "xdg" / "sdd-dispatch" / "models" / "alpha.yaml").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_validate_packs.py -q -k sdd_models`
Expected: FAIL — script does not exist.

- [ ] **Step 3: Write `scripts/sdd-models`**

```python
#!/usr/bin/env python3
"""Layered models.yaml helper: seed and inspect override layers.

Resolution is imported from scripts/validate-packs — the single implementation of the
layered walk (spec 2026-07-24). This script adds no precedence logic of its own."""
import argparse, importlib.machinery, importlib.util, os, shutil, sys
from pathlib import Path

def load_validate_packs():
    path = Path(__file__).with_name("validate-packs")
    loader = importlib.machinery.SourceFileLoader("validate_packs", str(path))
    spec = importlib.util.spec_from_loader("validate_packs", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module

def main():
    ap = argparse.ArgumentParser(prog="sdd-models")
    sub = ap.add_subparsers(dest="command", required=True)
    which = sub.add_parser("which"); which.add_argument("provider", nargs="?")
    init = sub.add_parser("init"); init.add_argument("provider")
    dest = init.add_mutually_exclusive_group(required=True)
    dest.add_argument("--project"); dest.add_argument("--user", action="store_true")
    init.add_argument("--force", action="store_true")
    for p in (which, init):
        p.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
        if p is which: p.add_argument("--project")
    a = ap.parse_args()
    vp = load_validate_packs()
    root = Path(a.root)
    providers = sorted(d.name for d in (root / "providers").glob("*/") if (d / "pack.md").exists())
    targets = [a.provider] if a.provider else providers
    for provider in targets:
        if provider not in providers:
            print(f"unknown provider: {provider}", file=sys.stderr); return 1
    if a.command == "which":
        for provider in targets:
            layer, path, _ = vp.resolve_models(provider, root, a.project)
            if vp.findings:
                for f in vp.findings: print(f, file=sys.stderr)
                return 1
            print(f"{provider}: layer={layer} path={path.resolve()}")
        return 0
    # init
    provider = a.provider
    layer, source, _ = vp.resolve_models(provider, root, getattr(a, "project", None))
    if vp.findings:
        for f in vp.findings: print(f, file=sys.stderr)
        return 1
    if a.user:
        xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        dest_path = Path(xdg) / "sdd-dispatch" / "models" / f"{provider}.yaml"
    else:
        dest_path = Path(a.project) / ".sdd-dispatch" / "models" / f"{provider}.yaml"
    if dest_path.exists() and not a.force:
        print(f"{dest_path} exists — pass --force to overwrite", file=sys.stderr); return 1
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest_path)
    print(f"seeded {dest_path} from layer={layer} ({source})")
    manifest = vp.parse_front_matter(root / "providers" / provider / "pack.md")
    argv = manifest.get("list-models-argv")
    if argv:
        print(f"open catalog: align rows with the live list — run: {' '.join(argv)}")
    return 0

if __name__ == "__main__": sys.exit(main())
```

Then: `chmod +x scripts/sdd-models`

- [ ] **Step 4: Run tests**

Run: `uv run --with pytest pytest tests/ -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
git add scripts/sdd-models tests/ && \
git commit -m "feat(scripts): sdd-models init/which — seed and inspect model override layers"
```

---

### Task 6: Skills, core docs, and verify-skill updates

**Files:**
- Modify: `skills/delegate/SKILL.md` (pack-reference bullet ~line 48; Tier lever ~line 58; Setup step 6 ~line 95; Workspace step 8 ~line 101)
- Modify: `skills/sdd/SKILL.md` (pack-reference bullet line 38; step 8 lines 76–80)
- Modify: `skills/sdd-dispatch-verify/SKILL.md` (reference line 21; step 2 line 75; step 5 line 100)
- Modify: `core/roles.md` (line 46 footnote), `core/playbook.md` (lines 5, 48), `core/verification-protocol.md` (lines 5, 28, 140)
- Test: existing `tests/test_delegate_skill.py` (must stay green — it pins purity, the single `.superpowers/sdd` mention, and skill structure)

Exact edits (old → new; keep hard-wrap style of each file):

- [ ] **Step 1: `skills/delegate/SKILL.md`**

1. Line 48–50 bullet → `- \`<root>/providers/<id>/pack.md\`, \`models.yaml\`, and \`models.md\` — validated provider behavior, canonical dispatch, session source, report transport, recovery rules, and model candidates (models.yaml is the table of record; models.md is narrative)`
2. Tier lever (~line 58): `the tier/lane candidate walk in the routed pack's models.md` → `the tier/lane candidate walk in the provider's resolved models.yaml`
3. Setup step 6 → replace with:

```markdown
6. **Model resolution**: role → (tier, lane) via `core/roles.md` → the provider's
   layered models.yaml (first found wins whole-file: `$SDD_DISPATCH_MODELS/<id>.yaml` →
   `<project>/.sdd-dispatch/models/<id>.yaml` →
   `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/models/<id>.yaml` → the pack's
   `models.yaml`) → ordered candidates (statuses verified/experimental; exact-lane rows
   by priority, then (tier, any) rows by priority); take the first; none → ask, naming
   the winning file. A found-but-malformed override, or set-but-unreadable
   `$SDD_DISPATCH_MODELS`, is a STOP, never a fall-through.
   (`scripts/validate-packs --resolve "<role>" <id> --project <repo>` prints the layer
   and walk; `scripts/sdd-models which|init` inspects and seeds override layers.)
```

4. Workspace step 8: `append \`.sdd-dispatch/\` to the file resolved by` → `append \`.sdd-dispatch/delegate/\` to the file resolved by`; and after the "user's separate commit)." sentence add: `\`.sdd-dispatch/models/\` is committable project config — never ignore \`.sdd-dispatch/\` at the root.`

- [ ] **Step 2: `skills/sdd/SKILL.md`**

1. Line 38 bullet → same rewording as delegate's pack-reference bullet.
2. Step 8 (lines 76–80) → replace with:

```markdown
8. **Resolve model within the routed provider**: role → (tier, lane) via core/roles.md →
   the provider's layered models.yaml (first found wins whole-file:
   `$SDD_DISPATCH_MODELS/<id>.yaml` → `<project>/.sdd-dispatch/models/<id>.yaml` →
   `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/models/<id>.yaml` → the pack's
   `models.yaml`) → ordered candidates (eligible statuses verified/experimental;
   exact-lane rows by priority, THEN (tier, any) rows by priority — this order is the
   complete fallback sequence); take the first; none → ask the user, naming the winning
   file. A found-but-malformed override, or set-but-unreadable `$SDD_DISPATCH_MODELS`,
   is a STOP, never a fall-through.
   (`scripts/validate-packs --resolve "<role>" <provider> --project <repo>` prints the
   layer and the walk order.)
```

- [ ] **Step 3: `skills/sdd-dispatch-verify/SKILL.md`**

1. Line 21 → `- \`<root>/providers/<id>/models.yaml\` — provider model table of record (statuses); \`models.md\` — narrative inventory`
2. Step 2 line 75: `its \`pack.md\`, \`models.md\`, and verification log` → `its \`pack.md\`, \`models.yaml\`, \`models.md\`, and verification log`
3. Step 5 line 100: `Update only that pack's \`pack.md\` and \`models.md\` when evidence changes facts, versions, or model status.` → `Update only that pack's \`pack.md\` and \`models.yaml\` when evidence changes facts, versions, or model status (stamps land in models.yaml — the table of record; models.md keeps the narrative entry).`

- [ ] **Step 4: core docs**

1. `core/roles.md:46` → `Tier→model mapping lives in each pack's models.yaml — the table of record, resolved through the layered override walk (env → project → user → pack default; whole-file precedence) — resolution algorithm and status eligibility in the spec §Resolution algorithm; priority 1 = default, ascending = fallback, only Status verified/experimental resolve. models.md carries the narrative.`
2. `core/playbook.md:5`: `the active pack's models.md` → `the active provider's resolved models.yaml`; line 48: `Resolve the selected tier against the active pack's models.md` → `Resolve the selected tier against the provider's layered models.yaml`
3. `core/verification-protocol.md` lines 5, 28, 140: each `pack.md / models.md` (or `pack.md and models.md`) → `pack.md / models.yaml / models.md` (line 140: `Update the active pack's pack.md and models.yaml (models.md for narrative).`)

No model ids, no invocation strings in any of these edits (purity).

- [ ] **Step 5: Run the structural suite**

Run: `uv run --with pytest pytest tests/test_delegate_skill.py -q`
Expected: all PASS (purity, single-mention rules, status vocabulary intact).

- [ ] **Step 6: Commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
git add skills/ core/ && \
git commit -m "docs(skills,core): layered models.yaml resolution; narrow delegate workspace ignore"
```

---

### Task 7: README, migration doc, version 1.8.0, final gate

**Files:**
- Modify: `README.md` (Adding a provider; Direct delegation ignore text; new "Model tables and overrides" section; `**Version:**` line)
- Create: `docs/migration-1.8.0.md`
- Modify: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` (version 1.8.0)
- Check only: `codex/INSTALL.md` (`grep -n models codex/INSTALL.md` — update any table-location claim the grep surfaces; if none, no edit)

- [ ] **Step 1: README edits**

1. "Adding a provider" first paragraph: `\`pack.md\`, \`models.md\`, and \`verification-log.md\` with the required manifest fields and tables.` → `\`pack.md\`, \`models.yaml\` (the model table of record), \`models.md\` (documentary narrative), and \`verification-log.md\` with the required manifest fields.`
2. Optional-fields table: add row `| \`list-models-argv\` | argv array | How to enumerate an open catalog provider's live model list (e.g. pi). Surfaced by \`sdd-models init\`, never auto-executed |`
3. "Direct delegation" section: `(ignored via \`.git/info/exclude\`)` → `(\`.sdd-dispatch/delegate/\` is ignored via \`.git/info/exclude\`; \`.sdd-dispatch/models/\` is committable project config)`
4. Insert a new section after "Adding a provider":

```markdown
## Model tables and overrides

Each pack ships its model priority table in `providers/<id>/models.yaml` (restricted
YAML: flat header + a list of `tier/lane/priority/model/status[/pricing/rationale]`
rows). At dispatch time the table is resolved per provider, first file found wins
whole-file (no merging):

1. `$SDD_DISPATCH_MODELS/<id>.yaml` (env override — a directory)
2. `<project>/.sdd-dispatch/models/<id>.yaml` (committable, team-shared)
3. `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/models/<id>.yaml` (this machine)
4. the pack default

Seed an override with `scripts/sdd-models init <id> --project <repo>|--user`; inspect
with `scripts/sdd-models which`. Override statuses are your own assertion — the
`verified` stamps in pack defaults come from live dispatch evidence only. A malformed
override is a hard error, never a silent fall-through; an override that omits a
(tier, lane) slot resolves that slot to "no eligible model — ask", which is the
supported way to keep a provider from auto-routing in one project.
```

5. `**Version:** 1.7.0` → `**Version:** 1.8.0`

- [ ] **Step 2: Write `docs/migration-1.8.0.md`**

```markdown
# Migrating to 1.8.0 — layered model tables

- Every pack's model priority table moved from a markdown table in
  `providers/<id>/models.md` to `providers/<id>/models.yaml` (the table of record).
  `models.md` remains for narrative, watch lists, and corrections; the validator now
  rejects any eligible-status table row left in it.
- Model resolution is layered, whole-file precedence:
  `$SDD_DISPATCH_MODELS/<id>.yaml` → `<project>/.sdd-dispatch/models/<id>.yaml` →
  `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/models/<id>.yaml` → pack default.
  Seed overrides with `scripts/sdd-models init`.
- `validate-packs --resolve` gained `--project <dir>` and now prints
  `layer: <layer> path=<abspath>` above the candidate walk.
- **Action needed in existing repos that ran the delegate skill:** earlier versions
  appended a blanket `.sdd-dispatch/` to `.git/info/exclude`. Replace that line with
  `.sdd-dispatch/delegate/`, or project model overrides under `.sdd-dispatch/models/`
  will be silently unstageable.
- **Cached plugin installs** (Codex plugin cache, Claude Code marketplace cache) carry
  the old md tables until refreshed — re-install/upgrade to 1.8.0 before relying on
  layered resolution.
- New optional manifest field: `list-models-argv` (open-catalog providers; pi declares
  `pi --list-models`).
```

- [ ] **Step 3: Version bumps**

In `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`: `"version": "1.7.0"` → `"version": "1.8.0"`.

- [ ] **Step 4: Full suite + hard gate + commit**

Run: `uv run --with pytest pytest tests/ -q`
Expected: all PASS (the validator's version-sync check confirms plugin.json == README).

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
git add README.md docs/migration-1.8.0.md .claude-plugin/plugin.json .codex-plugin/plugin.json codex/INSTALL.md && \
git commit -m "docs+chore: model-table override docs, migration note, bump to 1.8.0"
```

- [ ] **Step 5: Push and open the PR to `develop`**

```bash
git push -u origin feature/layered-model-config
gh pr create --base develop --title "Layered YAML model tables (v1.8.0)" \
  --body "Implements docs/superpowers/specs/2026-07-24-layered-model-config-design.md …"
```

(PR body: summary of the layer walk, the delegate-ignore narrowing, the eligible-row guard, and the GLM-5.2 design-review evidence path. End with the standard generated-with footer.)
