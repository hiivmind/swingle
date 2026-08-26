# Copilot notes

CLI: `copilot`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| a headless tool request repeats `Permission denied and could not request permission from user`, then returns `WRITE_FAILED` with exit 0 | the controller can mistake a denied mutation for a completed dispatch; a broad-permission retry can instead stop on quota | for a prompt that needs tools, explicitly choose `--allow-all-tools`, then verify repository state and treat quota/authentication as a separate failure | `copilot --help`; approved mutation smoke (2026-08-24) |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| result-only headless dispatch | read the complete authored `$PROMPT` into `PROMPT_TEXT`, pass it to `-p`, pass `$MODEL` and `$EFFORT` separately, set JSON output, disable color and auto-update, and capture stdout to absolute `$ARTIFACT` | Copilot documents `-p/--prompt <text>`; the approved account-blocked call establishes the remaining command shape but not a successful result | `copilot --help`; approved invocation smoke (2026-08-24) |
| prompt and workspace transport | load `$PROMPT` with Bash's NUL-delimited `read` builtin, pass `"$PROMPT_TEXT"` to `-p`, and use `-C "$REPO_ROOT"` for the workspace | the documented prompt interface takes text as an argument; the shell read avoids lossy command substitution | `copilot --help`; approved account-blocked smoke |
| model and effort encoding | pass a live-account model in `$MODEL` and a separate help-supported level in `--effort "$EFFORT"` (or its documented alias `--reasoning-effort`) | help separates model selection from the effort enum; authentication and entitlement were not established by the blocked smoke | `copilot --help` |
| mutation permission and verification | preserve the complete authored mutation briefing, add `--allow-all-tools` only when the prompt requires tools, and verify exact bytes plus unexpected paths after completion | default denial returned exit 0, while the permission-enabled retry hit quota before mutation | approved mutation smoke (2026-08-24) |

### Result-only command

```bash
IFS= read -r -d '' PROMPT_TEXT < "$PROMPT" || true
copilot -C "$REPO_ROOT" -p "$PROMPT_TEXT" --model "$MODEL" --effort "$EFFORT" --output-format json --no-color --no-auto-update < /dev/null > "$ARTIFACT"
```

This command shape is current help- and smoke-supported, but the approved account returned `No authentication information found` before model dispatch. Treat the captured artifact as an error report unless a live run supplies a successful completion; no JSON result schema is shipped here.
