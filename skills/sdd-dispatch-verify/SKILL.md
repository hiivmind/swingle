---
name: sdd-dispatch-verify
description: Re-verify SDD dispatch CLI behavior (codex, opencode, agy) against this plugin's living knowledge base. Use when a CLI version bump is observed, a vendor releases new models, a dispatch behaves contrary to documented gotchas, or the user asks to "verify/test the dispatch CLIs", "re-run the CLI probes", or "check if the SDD reference is current".
---

# SDD Dispatch Verification

Knowledge base (this plugin's `references/` directory — the living source of truth):
- `${CLAUDE_PLUGIN_ROOT}/references/verification-protocol.md` — the probe suite P1–P12
- `${CLAUDE_PLUGIN_ROOT}/references/dispatch-reference.md` — per-CLI facts + version stamps
- `${CLAUDE_PLUGIN_ROOT}/references/model-catalog.md` — model inventories + tiering
- `${CLAUDE_PLUGIN_ROOT}/references/verification-log.md` — append-only verdict history

## Process

1. **Read first**: the verification protocol (probe suite and ground rules) and the
   current dispatch-reference version stamps. Determine which CLI(s) need a round:
   compare `codex --version` / `opencode --version` / `agy --version` against the stamps,
   and `opencode models` / `agy models` against the model catalog.

2. **Run the probe suite** for each affected CLI, in the session scratchpad directory.
   Ground rules that must not be skipped:
   - never mask exit codes with pipes (use `${PIPESTATUS[0]}` or unpiped `$?`)
   - verify side effects on disk, never from agent prose
   - bound every probe with `timeout`; treat 124/143 as "hangs"
   - use each CLI's cheapest model for probes

3. **Record**: append a dated verdict-matrix entry to `references/verification-log.md`
   (Confirmed / Refuted / Refined / New, with one-line raw evidence). Never edit prior
   entries — contradictions date behavior changes.

4. **Update the living docs**: `references/dispatch-reference.md` (facts + version
   stamps), `references/model-catalog.md` (inventories, verified-status, watch list,
   release history). If findings change how the `sdd` skill should dispatch, update
   `${CLAUDE_PLUGIN_ROOT}/skills/sdd/SKILL.md` and the contracts in
   `${CLAUDE_PLUGIN_ROOT}/contracts/` in the same round.

5. **Clean up** all probe artifacts: scratchpad files, throwaway git repos, and any
   `/tmp` files created by the sandbox-escape probe (P7).

6. **Commit** in the plugin's own repo (`git -C "${CLAUDE_PLUGIN_ROOT}" …` if working the
   installed copy is the source checkout; otherwise commit in the source checkout and
   reinstall). Bump the plugin version in `.claude-plugin/plugin.json` for behavior-fact
   changes. Message like:
   `verify: round YYYY-MM-DD — <cli> <old>→<new>, <headline finding>`.

## Cautions

- agy's permission model flipped completely between patch releases (1.1.1 → 1.1.4);
  never assume any CLI's permission/sandbox behavior survived a version bump.
- agy dispatches must put `-p "<PROMPT>"` last; codex and agy need `< /dev/null`.
- These probes execute real dispatches that can WRITE (agy/opencode have no sandbox):
  run only in the scratchpad, on a clean tree, and diff after.
