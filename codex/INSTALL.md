# Codex installation

Clone or check out the whole repository at a stable location. The `sdd` skill requires
its sibling directories `core/`, `providers/`, and `contracts/`; copying only `SKILL.md`
is unsupported. For example, replace `<repository-url>` with this repository's clone URL:

```bash
git clone <repository-url> "$HOME/src/sdd-dispatch-plugin"
export SDD_DISPATCH_PLUGIN="$HOME/src/sdd-dispatch-plugin"
```

Register the skill directory with Codex discovery by symlinking it into Codex's skills
path. This preserves the physical sibling layout that the skill uses to resolve its root:

```bash
export CODEX_SKILLS_DIR="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$CODEX_SKILLS_DIR"
ln -s "$SDD_DISPATCH_PLUGIN/skills/sdd" "$CODEX_SKILLS_DIR/sdd"
```

If `$CODEX_SKILLS_DIR/sdd` already exists, inspect it first; replace it only when it is an
obsolete registration for this skill. Codex should now discover the skill as `sdd`.

On first use, read the Codex harness adapter:

```
skills/sdd/harnesses/codex.md
```

From the clone, verify the registered skill's repository layout and release gate with:

```bash
cd "$SDD_DISPATCH_PLUGIN"
./scripts/codex-smoke
```
