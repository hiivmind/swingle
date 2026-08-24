# Devin notes

CLI: `devin`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| `-p`/`--print` in an untrusted workspace exits 1 with `Refusing to run in an untrusted workspace` | headless dispatch fails before doing work | pass `--respect-workspace-trust false` for unattended use, then verify the repository result | `devin --help`; approved mutation smoke (2026-08-24) |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| result-only headless dispatch | use `--prompt-file "$PROMPT" -p`, disable workspace-trust prompting, and capture complete stdout to absolute `$ARTIFACT`; leave `$MODEL` unset unless a live route is known to work | Devin's current successful route used a prompt file and provider-selected model, and exposes no structured result mode | `devin --help`; approved invocation smoke (2026-08-24) |
| prompt and workspace trust | preserve the complete authored briefing in `$PROMPT` and pass `--respect-workspace-trust false` for unattended workspace use; do not claim stdin semantics | prompt-file success does not establish behavior for an unrelated open stdin pipe | `devin --help`; approved invocation smoke (2026-08-24) |
| model and effort encoding | choose `$MODEL` only from a successful current account route; do not pass `$EFFORT` because Devin exposes no CLI-level effort control | top-level and model help expose `--model` but no effort flag or bracket syntax | `devin --help`; `devin models --help` |
| final text and completion | treat complete stdout as the result and require normal process completion; retain provider narration rather than trying to select a field | current Devin output is plain stdout with no structured selector or completion event | approved invocation smoke (2026-08-24) |
| mutation permission and verification | preserve the complete authored mutation briefing, use `--permission-mode accept-edits` when writes are requested, and verify exact bytes plus unexpected paths | the approved mutation smoke required both trust override and write mode; provider narration and `WRITE_OK` are not repository proof | approved mutation smoke (2026-08-24) |

### Result-only command

```bash
devin --prompt-file "$PROMPT" -p --respect-workspace-trust false > "$ARTIFACT"
```

The current result smoke omitted `--permission-mode` for read-only work and used a provider-selected model. Add the write mode only for a mutation briefing; capture all stdout because Devin exposes no structured output mode.
