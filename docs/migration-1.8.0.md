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
