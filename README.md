# sdd-dispatch

Standalone harness-neutral plugin for subagent-driven development via external
CLIs (codex / opencode / agy): token-efficient plan execution plus the verified
knowledge base that makes dispatch safe.

Everything is self-contained. The `sdd` skill and provider packs are discovered
from this repository; no machine-specific paths are required.

**Version:** 1.2.4

## Install with Claude Code

Requires the `superpowers` plugin and whichever dispatch CLIs you use on PATH
(`codex`, `opencode`, `agy`), each authenticated once interactively.

```text
/plugin marketplace add discreteds/sdd-dispatch-plugin
/plugin install sdd-dispatch@sdd-dispatch-marketplace
```

(A local checkout also works: `/plugin marketplace add /path/to/sdd-dispatch-plugin`.)

## Install with Codex

This repository is also a Codex plugin (`.codex-plugin/plugin.json`) with a self-hosted
marketplace:

```bash
codex plugin marketplace add discreteds/sdd-dispatch-plugin
codex plugin add sdd-dispatch@sdd-dispatch-marketplace
```

Manual alternative
(clone + symlink into `$HOME/.agents/skills/`) and full details:
[codex/INSTALL.md](codex/INSTALL.md). The Codex entry point is `skills/sdd/SKILL.md`.

## Layout

```
skills/sdd/                       # plan-execution skill and harness adapters
skills/sdd-dispatch-verify/       # CLI re-verification skill
core/                             # shared doctrine, playbook, roles, and logs
providers/<id>/                    # self-contained provider packs
contracts/                         # implementer and reviewer contracts
codex/INSTALL.md                   # Codex installation instructions
archive/v1.1/                      # verbatim legacy references
references/                        # v1.1 tombstones with migration links
scripts/validate-packs             # pack validator and resolver
scripts/codex-smoke                # Codex layout and validator smoke test
```

## Skills

| Skill | Purpose |
| --- | --- |
| `sdd` | Execute an implementation plan through the active harness and provider packs |
| `sdd-dispatch-verify` | Re-run the CLI probe suite when versions bump or models release |

## Adding a provider

Add one directory under `providers/` satisfying the provider pack contract:
`pack.md`, `models.md`, and `verification-log.md` with the required manifest
fields and tables. Run:

```bash
python3 scripts/validate-packs --root .
```

Adding a provider requires zero edits to `core/`; routing is manifest-driven.
