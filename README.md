# sdd-dispatch

Standalone harness-neutral plugin for subagent-driven development via external
CLIs (codex / opencode / agy): token-efficient plan execution plus the verified
knowledge base that makes dispatch safe.

Everything is self-contained. The `sdd` skill and provider packs are discovered
from this repository; no machine-specific paths are required.

**Version:** 1.3.1

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
skills/delegate/                  # direct one-off dispatch skill (no plan machinery)
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
| `delegate` | Directly dispatch an explicitly requested one-off job or homogeneous batch through the provider packs — no plan required |
| `sdd-dispatch-verify` | Re-run the CLI probe suite when versions bump or models release |

## Direct delegation

`delegate <task>` dispatches a self-contained job (or homogeneous batch) to an external
CLI with the full pack doctrine — role inference from `core/roles.md`, model tiering,
liveness, hardened evidence gates (staged + untracked + HEAD-unchanged), controller
commits, and session resume — but none of the SDD plan-execution ceremony. Levers:
`via <provider>`, `floor it` / `play it safe` / explicit model, `with review`,
`read-only`, `supervised` / `unsupervised`. Jobs implying ≥3 planned dispatch cycles
run supervised automatically (announced). Artifacts and the lifecycle ledger live in
`.sdd-dispatch/delegate/` (ignored via `.git/info/exclude`). The boundary is semantic:
multi-task implementation plans go to the `sdd` skill regardless of how they arrived;
tasks below the triviality floor stay inline unless delegation was explicitly
requested.

## Adding a provider

Add one directory under `providers/` satisfying the provider pack contract:
`pack.md`, `models.md`, and `verification-log.md` with the required manifest
fields and tables. Run:

```bash
python3 scripts/validate-packs --root .
```

Adding a provider requires zero edits to `core/`; routing is manifest-driven.

## Reporting verification findings

The packs are living documents: CLIs flip behavior between patch releases, models come
and go, and every live dispatch is evidence. Where a finding gets recorded depends on
what you can write to (the **recording ladder** — full rules in
`core/verification-protocol.md` §Recording and the `sdd-dispatch-verify` skill, step 0):

1. **Writable source checkout** — append to the pack's `verification-log.md`, update the
   pack facts, and commit. Never record into an installed plugin cache (Claude Code
   `~/.claude/plugins/cache/...`, Codex `~/.codex/plugins/cache/...`) — caches are
   clobbered on the next upgrade.
2. **Clone but no push rights** — commit locally and open an issue or PR carrying the
   log entry.
3. **No source tree** (installed copy only) — [open an issue](https://github.com/discreteds/sdd-dispatch-plugin/issues/new?template=verification-finding.md)
   using the **Verification finding** template (`verification` label), one issue per
   independent finding: CLI + plugin version, trigger, the pack assertion under test,
   verdict, verbatim evidence, impact. **Search first**: if an equivalent issue exists,
   a 👍 reaction adds weight to its prioritisation; comment only when you bring a new
   angle or wrinkle not already covered.

A finding recorded only in an installed cache is a finding lost.
