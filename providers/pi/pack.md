# Pi notes

CLI: `pi`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| result-only headless dispatch | use `-p`, JSON mode, an account-usable `$MODEL`, `--thinking "$EFFORT"`, a session directory under the project, and the complete authored prompt-file reference; capture output to absolute `$ARTIFACT` | Pi's help establishes the headless, model, thinking, session-directory, and file-prompt slots, while the current account-blocked smoke does not certify a successful result | `pi --help`; approved invocation shape (2026-08-24) |
| prompt and project transport | preserve the complete authored briefing in `$PROMPT` and pass it as `"@$PROMPT"`; select the session directory explicitly under `$PROJECT` | the accepted command shape uses Pi's file-prompt syntax; current stdin behavior was not promoted because the model route was blocked before execution | `pi --help`; approved invocation shape (2026-08-24) |
| model and effort encoding | resolve an account-usable provider/id route for `$MODEL`, then pass the supported level as `--thinking "$EFFORT"` (or the documented `provider/id:<thinking>` form); do not infer entitlement from unavailable inventory | help establishes the encoding, but the live inventory returned no models and the approved call stopped at a usage limit | `pi --help`; `pi --list-models`; approved invocation smoke (2026-08-24) |

### Result-only command

```bash
pi -p --mode json --model "$MODEL" --thinking "$EFFORT" --session-dir "$PROJECT/.swingle-session" "@$PROMPT" < /dev/null > "$ARTIFACT"
```

The current smoke reached Pi but stopped at a provider usage-limit error before model execution. Treat the artifact as an error report unless a live account supplies a model result; no output schema, session continuity, permission, or liveness interpretation is shipped from the blocked evidence.
