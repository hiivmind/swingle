"""CLI contract + default-mode ordering lock.

Captured from the pre-decomposition code so it holds byte-identical across the
scripts/ -> lib/swingle/ move. The default-mode finding ORDER (version-sync ->
per-pack structural -> hygiene -> purity -> one global path-sorted link scan) is the
highest-risk property of the refactor, so it is asserted exactly.

The multi-region tree is built in tmp_path, never tracked: `validate-packs --root .`
rglobs every *.md in the repo, so a tracked broken-link fixture would fail the real
gate. Building it at runtime keeps the ordering lock isolated from the repo scan.
"""

import os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIX = Path(__file__).parent / "fixtures"
GOOD = FIX / "good-lanes"
BINS = FIX / "bins-alpha"


def isolated_env(**overrides):
    e = dict(os.environ, XDG_CONFIG_HOME=str(FIX / "no-such-xdg"))
    e.pop("SWINGLE_CONFIG", None)
    e.pop("SWINGLE_MODELS", None)
    for name, value in overrides.items():
        e.pop(name, None) if value is None else e.__setitem__(name, value)
    return e


def run(script, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True,
        text=True,
        env=isolated_env(),
    )


def norm(text, *roots):
    """Replace absolute root prefixes with <ROOT> so assertions are portable."""
    for r in roots:
        text = text.replace(str(Path(r).resolve()), "<ROOT>")
    return text


def build_multi_region(root: Path):
    """Materialise a tree that fires exactly one finding in each default-mode region,
    exercised in order: version-sync, per-pack structural, hygiene, purity, link scan."""
    import shutil

    shutil.copytree(GOOD, root, dirs_exist_ok=True)
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (root / ".claude-plugin" / "plugin.json").write_text('{\n  "version": "9.9.9"\n}\n')
    (root / "README.md").write_text(
        "# Fixture\n\n**Version:** 0.0.0\n\n[dead](nope.md)\n"
    )
    with (root / "providers" / "alpha" / "pack.md").open("a") as f:
        f.write("body extra\n")
    with (root / "providers" / "alpha" / "models.md").open("a") as f:
        f.write("\nSome ~~struck~~ text.\n")
    (root / "core" / "doctrine.md").write_text(
        "# doctrine\n\nUse gpt-5.6 for this.\n\nSee [missing](missing.md) for details.\n"
    )


def test_default_mode_ordering_lock(tmp_path):
    root = tmp_path / "multi"
    build_multi_region(root)
    r = run("validate-packs", "--root", str(root))
    assert r.returncode == 1
    expected = (
        "version mismatch: plugin.json 9.9.9 != README 0.0.0\n"
        "<ROOT>/providers/alpha/pack.md: pack.md must be manifest-only\n"
        "<ROOT>/providers/alpha/models.md:5: pack-hygiene: strikethrough: Some ~~struck~~ text.\n"
        "<ROOT>/core/doctrine.md:3: purity violation: Use gpt-5.6 for this.\n"
        "<ROOT>/README.md:5: broken link nope.md\n"
        "<ROOT>/core/doctrine.md:5: broken link missing.md\n"
    )
    assert norm(r.stdout, root) == expected


def test_resolve_output(tmp_path):
    r = run(
        "validate-packs", "--root", str(GOOD), "--resolve", "per-task reviewer", "alpha"
    )
    assert r.returncode == 0
    assert norm(r.stdout, ROOT) == (
        "layer: default path=<ROOT>/tests/fixtures/good-lanes/providers/alpha/models.yaml\n"
        "per-task reviewer -> ('standard', 'review') -> review-model-exact "
        "(P1, verified); fallback order: review-model-exact, review-model-any\n"
    )


def test_step0_output():
    r = run("validate-packs", "--step0", "--root", str(GOOD), "--path-dir", str(BINS))
    assert r.returncode == 0
    assert (
        r.stdout == "installed: alpha\nactive: alpha\nprovider: alpha\nready: alpha\n"
    )


def test_health_output():
    r = run("validate-packs", "--health", "--root", str(GOOD), "--path-dir", str(BINS))
    assert r.returncode == 0
    assert r.stdout == (
        "alpha: installed=yes version=1.0.0 verified=1.0.0 drift=no readiness=ok "
        "registry-layer=default\nconfig-layer=none\n"
    )


def test_check_config_malformed():
    r = run("validate-packs", "--check-config", str(FIX / "config-malformed.json"))
    assert r.returncode == 1 and "unreadable/malformed" in r.stdout


def test_swingle_models_which():
    """Repo-wide; assert shape + coverage rather than a brittle provider list."""
    r = run("swingle-models", "which")
    assert r.returncode == 0
    lines = norm(r.stdout, ROOT).splitlines()
    providers = sorted(
        p.name for p in (ROOT / "providers").glob("*/") if (p / "pack.md").exists()
    )
    assert len(lines) == len(providers)
    for line in lines:
        assert re.fullmatch(
            r"[a-z0-9-]+: layer=default path=<ROOT>/providers/[a-z0-9-]+/models\.yaml",
            line,
        ), line


def test_shard_logs_read_only_index_only():
    """`shard-logs --root .` is read-only and exits 1: retained logs are indexes with
    no top-level entries (scripts/shard-logs write path is guarded behind --write)."""
    r = run("shard-logs", "--root", str(ROOT))
    assert r.returncode == 1
    assert "no top-level verification-log entries" in (r.stdout + r.stderr)
