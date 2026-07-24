# sdd-dispatch

![sdd-dispatch hero banner](docs/images/hero-banner.jpg)

Standalone harness-neutral plugin for subagent-driven development via external
CLIs (codex / opencode / agy / grok / pi / claude): token-efficient plan execution plus the verified
knowledge base that makes dispatch safe.

Everything is self-contained. The `sdd` skill and provider packs are discovered
from this repository; no machine-specific paths are required.

**Version:** 1.9.2

## Install with Claude Code

Requires the `superpowers` plugin and whichever dispatch CLIs you use on PATH
(`codex`, `opencode`, `agy`, `grok`, `pi`, `claude`), each authenticated once interactively.

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

## Install with opencode

opencode has no Claude Code plugin loader — its `plugin` config key takes npm packages
and local `.ts` modules only. Plugins reach opencode as **skills trees** instead, which
costs this repository nothing: it ships skills exclusively (no commands, agents, or
hooks). Skills register under their bare frontmatter names (`sdd`, `delegate`,
`sdd-dispatch-verify`); opencode has no plugin namespace and dedupes by name, so install
by exactly one of the routes below.

### Route A — expose every installed Claude Code plugin (recommended)

If you already run this plugin under Claude Code, the whole plugin set can be handed to
opencode at once. Generate version-pinned `skills.paths` entries from Claude Code's own
install registry:

```bash
scripts/opencode-skills-path --merge ~/.config/opencode/opencode.json   # global
scripts/opencode-skills-path --merge ./opencode.json                    # per-project
```

Run it again after installing, updating, or removing a Claude Code plugin.

**Do not shortcut this by pointing `skills.paths` at `~/.claude/plugins/cache` directly.**
That directory retains every version ever installed (`cache/<marketplace>/<plugin>/<version>/`),
and because opencode dedupes by skill name it will silently register an arbitrary version
per skill — including mismatched versions within a single plugin. Observed on a real
machine: the bare cache path loaded `sdd` 1.0.0 next to `delegate` 1.5.0, and superpowers
6.0.3 while 6.1.1 was the installed version. The script reads `installed_plugins.json` and
emits only the pinned `installPath` of each installed plugin, which resolves all three
correctly.

### Route B — this plugin alone, from a checkout

For a source checkout (or if you do not use Claude Code at all), point `skills.paths` at
the repository's `skills/` directory in `~/.config/opencode/opencode.json` (global) or
`./opencode.json` (per-project). Entries are scanned recursively for `**/SKILL.md`; `~/`
is expanded and relative paths resolve against the working directory.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "skills": {
    "paths": ["~/src/sdd-dispatch-plugin/skills"]
  }
}
```

A symlink into `~/.claude/skills/` works too — opencode scans Claude Code's skill
directories by default — but it has two drawbacks Route B avoids: the compat scan is
switched off by `OPENCODE_DISABLE_EXTERNAL_SKILLS` / `OPENCODE_DISABLE_CLAUDE_CODE`, and
skill locations are reported *through* the symlink, so the asset-root derivation in
[skills/sdd/harnesses/opencode.md](skills/sdd/harnesses/opencode.md) must resolve the
physical path before it can find `core/` and `providers/`.

### After either route

Restart opencode and confirm the skills are registered before first use:

```bash
opencode debug skill | grep -E '"name": "(sdd|delegate|sdd-dispatch-verify)"'
```

`sdd` wraps `superpowers:subagent-driven-development`, so superpowers must be reachable by
the same route (Route A covers it automatically). Dispatch CLIs (`codex`, `opencode`,
`agy`, `grok`, `pi`, `claude`) must be on PATH and authenticated once interactively, as with the other
harnesses. Harness-specific behaviour — the missing shell background mode, the
`subagent_depth` cap, and session-id attribution when opencode dispatches its own pack —
is documented in [skills/sdd/harnesses/opencode.md](skills/sdd/harnesses/opencode.md).

## Layout

```
skills/sdd/                       # plan-execution skill and harness adapters
skills/delegate/                  # direct one-off dispatch skill (no plan machinery)
skills/sdd-dispatch-verify/       # CLI re-verification skill
core/                             # shared doctrine, playbook, roles, and logs
providers/<id>/                    # self-contained provider packs
contracts/                         # implementer, task-reviewer, design-reviewer, and reader contracts
codex/INSTALL.md                   # Codex installation instructions
archive/v1.1/                      # verbatim legacy references
references/                        # v1.1 tombstones with migration links
scripts/validate-packs             # pack validator and resolver
scripts/codex-smoke                # Codex layout and validator smoke test
scripts/opencode-skills-path       # opencode skills.paths from installed Claude Code plugins
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
`.sdd-dispatch/delegate/`, ignored via `.git/info/exclude` (`.sdd-dispatch/models/` is committable project config). The boundary is semantic:
multi-task implementation plans go to the `sdd` skill regardless of how they arrived;
tasks below the triviality floor stay inline unless delegation was explicitly
requested.

## Adding a provider

Add one directory under `providers/` satisfying the provider pack contract:
`pack.md`, `models.yaml` (the model table of record), `models.md` (documentary narrative), and `verification-log.md` with the required manifest fields. Run:

```bash
python3 scripts/validate-packs --root .
```

Adding a provider requires zero edits to `core/`; routing is manifest-driven.

The manifest is the YAML front matter of `pack.md`. Required: `schema-version`, `id`,
`cli`, `verified-version`, `version-argv`, `resume-argv`, `session-source`,
`stall-signal`, `sandbox`. Optional: `fork-flag`, `session-list-argv`,
`readiness-argv`, `readiness-timeout-seconds`, and:

| Field | Values | Meaning |
| --- | --- | --- |
| `report-transport` | `report-file` (default) · `captured-output` | How an agent's report gets back to the controller |
| `list-models-argv` | argv array | How to enumerate an open catalog provider's live model list (e.g. pi). Surfaced by `sdd-models init`, never auto-executed |

Declare `captured-output` when the CLI cannot reliably write an agent-authored file to a
workspace path. The skills then ask for **no file** and take the full report as the
captured final message, saving it themselves. Getting this wrong is not cosmetic: on such
a provider a report-file request fails *intermittently* while the exit code stays 0, so
the report is silently missing and any reviewer downstream loses an input. `agy` is
`captured-output`; `codex`, `opencode`, and `grok` are `report-file`.

Every value is validator-enforced, and `*-argv` arrays are data — `argv[0]` must equal
`cli`, and shell metacharacters are rejected, so a manifest can never smuggle in a
command to execute.

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
