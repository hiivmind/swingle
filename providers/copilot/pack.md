# Copilot notes

CLI: `copilot`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| a headless tool request repeats `Permission denied and could not request permission from user`, then returns `WRITE_FAILED` with exit 0 | the controller can mistake a denied mutation for a completed dispatch; a broad-permission retry can instead stop on quota | for a prompt that needs tools, explicitly choose `--allow-all-tools`, then verify repository state and treat quota/authentication as a separate failure | `copilot --help`; approved mutation smoke (2026-08-24) |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| result-only headless dispatch | use `-p` with the complete authored `$PROMPT`, pass `$MODEL` and `$EFFORT` separately, set JSON output, disable color and auto-update, and capture stdout to absolute `$ARTIFACT` | Copilot's print, project, model, effort, and output controls are distinct; the approved account-blocked call establishes the shape but not a successful result | `copilot --help`; approved invocation smoke (2026-08-24) |
| prompt and workspace transport | pass the prompt with `-p` and the project with `-C "$PROJECT"`; do not infer stdin behavior because no current closure probe reached model execution | the account-blocked smoke omitted stdin comparison, so no mandatory closure rule is supported | `copilot --help`; approved invocation smoke (2026-08-24) |
| model and effort encoding | pass a live-account model in `$MODEL` and a separate help-supported level in `--effort "$EFFORT"` (or its documented alias `--reasoning-effort`) | help separates model selection from the effort enum; authentication and entitlement were not established by the blocked smoke | `copilot --help` |
| mutation permission and verification | preserve the complete authored mutation briefing, add `--allow-all-tools` only when the prompt requires tools, and verify exact bytes plus unexpected paths after completion | default denial returned exit 0, while the permission-enabled retry hit quota before mutation | approved mutation smoke (2026-08-24) |

### Result-only command

```bash
copilot -C "$PROJECT" -p "$(cat "$PROMPT")" --model "$MODEL" --effort "$EFFORT" --output-format json --no-color --no-auto-update > "$ARTIFACT"
```

This command shape is current help- and smoke-supported, but the approved account returned `No authentication information found` before model dispatch. Treat the captured artifact as an error report unless a live run supplies a successful completion; no JSON result schema is shipped here.
