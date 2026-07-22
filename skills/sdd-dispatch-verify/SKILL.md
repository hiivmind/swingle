---
name: sdd-dispatch-verify
description: Re-verify SDD dispatch CLI behavior (codex, opencode, agy) against this plugin's living knowledge base. Use when a CLI version bump is observed, a vendor releases new models, a dispatch behaves contrary to documented gotchas, or the user asks to "verify/test the dispatch CLIs", "re-run the CLI probes", or "check if the SDD reference is current".
---

# SDD Dispatch Verification

Knowledge base (all paths are relative to the plugin tree root `<root>`):

- `<root>/core/verification-protocol.md` — the probe suite P1–P12
- `<root>/core/verification-log.md` — cross-provider append-only history
- `<root>/providers/<id>/pack.md` — provider facts, version stamp, and canonical dispatch
- `<root>/providers/<id>/models.md` — provider model inventory and statuses
- `<root>/providers/<id>/verification-log.md` — provider-specific append-only verdicts

## Process

1. **Read first**: the verification protocol (probe suite and ground rules) and each
   relevant provider pack. Determine which CLI(s) need a round: compare the manifest's
   `version-argv` output against `verified-version`, and inspect the pack's model inventory.

2. **Run the probe suite** for each affected CLI, in the session scratchpad directory.
   Ground rules that must not be skipped:
   - never mask exit codes with pipes (use `${PIPESTATUS[0]}` or unpiped `$?`)
   - verify side effects on disk, never from agent prose
   - bound every probe with `timeout`; treat 124/143 as "hangs"
   - use each CLI's cheapest model for probes

3. **Record**: append a dated verdict-matrix entry to the appropriate
   `providers/<id>/verification-log.md` (Confirmed / Refuted / Refined / New, with one-line
   raw evidence). Never edit prior entries — contradictions date behavior changes.

4. **Update the living docs**: the active pack's `pack.md` (facts + version stamp) and
   `models.md` (inventories, verified-status, watch list, release history). If findings
   change how the `sdd` skill should dispatch, update `<root>/skills/sdd/SKILL.md`, its
   applicable harness adapter, and `<root>/contracts/` in the same round.

5. **Clean up** all probe artifacts: scratchpad files, throwaway git repos, and any
   `/tmp` files created by the sandbox-escape probe (P7).

6. **Commit** in the plugin's own repo (`git -C <root> …` if working the installed copy is
   the source checkout; otherwise commit in the source checkout and reinstall). Bump the
   plugin version in `.claude-plugin/plugin.json` for behavior-fact changes. Message like:
   `verify: round YYYY-MM-DD — <cli> <old>→<new>, <headline finding>`.

## Cautions

- Never assume a provider's permission or sandbox behavior survived a version bump.
- Follow the active pack's canonical dispatch template and all recorded caveats.
- These probes can write: run only in the scratchpad, on a clean tree, and diff after.
