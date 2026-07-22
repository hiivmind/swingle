# sdd-dispatch

Standalone Claude Code plugin for **subagent-driven development via external CLIs**
(codex / opencode / agy): token-efficient plan execution plus the empirically-verified
knowledge base that makes it safe.

Everything is self-contained — skills reference plugin files via `${CLAUDE_PLUGIN_ROOT}`;
no dependence on global CLAUDE.md tables or machine-specific paths.

## Install

```
/plugin marketplace add /path/to/sdd-dispatch-plugin
/plugin install sdd-dispatch@sdd-dispatch-marketplace
```

Requires: the `superpowers` plugin (this wraps its subagent-driven-development skill),
and whichever dispatch CLIs you use on PATH (`codex`, `opencode`, `agy` — each
authenticated once interactively).

## Skills

| Skill | Purpose |
| --- | --- |
| `sdd` | Execute an implementation plan: wraps superpowers:subagent-driven-development, replacing its Agent-tool dispatch with external-CLI dispatch (contracts as files, resume-based Q&A/fixes, enforced read-only reviewers, controller commits, liveness protocol, risk-scaled gate) |
| `sdd-dispatch-verify` | Re-run the CLI probe suite when versions bump or models release; updates the living references and appends to the verification log |

## Layout

```
skills/sdd/                      # plan-execution skill (the entry point)
skills/sdd-dispatch-verify/      # CLI re-verification skill
contracts/                       # implementer + task-reviewer operating contracts
                                 #   (copied once per session into the SDD workspace)
references/
  sdd-external-dispatch.md       # the playbook: role→lane mapping, token-efficiency rules
  dispatch-reference.md          # verified per-CLI behavior, gotchas, liveness protocol
  model-catalog.md               # role→tier→model policy table + provider inventories
  verification-protocol.md       # the repeatable probe suite (P1–P12)
  verification-log.md            # append-only verdict history (never rewrite entries)
```

## Living-document rules

Facts in `references/` are version-stamped and empirically probed — vendor claims enter
as *reported* until verified. Re-verification triggers: CLI version bump, model release,
a gotcha firing (or failing to fire), or quarterly. Run the `sdd-dispatch-verify` skill;
it appends to the log, updates the references, and bumps the plugin version.

Origin: seeded 2026-07-22 from a full three-CLI verification round
(codex 0.144.3, opencode 1.17.18, agy 1.1.4).
