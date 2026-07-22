# Codex installation

Clone or check out the whole repository. The `sdd` skill requires its sibling
directories `core/`, `providers/`, and `contracts/`; copying only `SKILL.md` is
unsupported.

Point Codex skill discovery at:

```
skills/sdd/SKILL.md
```

On first use, read the Codex harness adapter:

```
skills/sdd/harnesses/codex.md
```

From the repository root, verify the installation with:

```bash
python3 scripts/validate-packs --root .
```
