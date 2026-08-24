# Grok notes

CLI: `grok`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| a terminal tool call is cancelled under `--permission-mode acceptEdits` | a filesystem write can be blocked even though the intended effect is a file edit | select the permission mode that authorizes the actual tool class, then verify exact bytes and unexpected paths | `grok --help`; approved mutation smoke (2026-08-24) |
| single-object JSON output buffers until exit and can appear stalled | log-age monitoring reports a false stall | use the live CLI's streaming-JSON format when incremental signals and session capture are needed; only then diagnose unremitting no-output through generic liveness policy | `grok --help`; approved invocation smoke (2026-08-24) |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| result-only headless dispatch | use `--cwd "$PROJECT"`, `--prompt-file "$PROMPT"`, `$MODEL`, `--reasoning-effort "$EFFORT"`, streaming JSON, and an absolute `$ARTIFACT` capture | Grok's prompt-file, project, model, effort, and output controls are distinct and the current successful route uses a stream | `grok --help`; approved invocation smoke (2026-08-24) |
| prompt and stdin transport | preserve the complete authored briefing in `$PROMPT` and use `--prompt-file`; do not add a Codex-style stdin workaround | current prompt-file dispatch completed without consuming piped stdin, so prompt-file transport is the relevant closure boundary | approved invocation smoke (2026-08-24) |
| model discovery and effort encoding | run `grok models`, choose an account-listed `$MODEL`, and pass the selected route's supported value as `--reasoning-effort "$EFFORT"` | the live list supplies the account default and available models, while help exposes the effort slot without proving every model/value combination | `grok models`; `grok --help` |
| structured result interpretation | concatenate ordered `text.data` fragments and require the terminal `end` event; retain its session ID, request ID, usage, and cost | streaming JSON makes final text, completion, session, and accounting fields explicit | approved invocation smoke (2026-08-24) |
| session identity | retain the session ID from the terminal `end` event; treat resume/fork as a live operation rather than a continuity guarantee | current evidence captured identity and help syntax but did not run a second-turn continuity probe | `grok --help`; approved invocation smoke (2026-08-24) |
| mutation permission and verification | preserve the complete authored mutation briefing, select permission for the model's actual tool class, and verify exact bytes plus unexpected paths | `acceptEdits` cancelled a terminal write while `auto` completed it; intended filesystem effect does not determine tool authorization | approved mutation smoke (2026-08-24) |

### Result-only command

```bash
grok --cwd "$PROJECT" --model "$MODEL" --prompt-file "$PROMPT" --output-format streaming-json --reasoning-effort "$EFFORT" --no-alt-screen --no-subagents --no-plan --permission-mode default > "$ARTIFACT"
```

### Structured output

```bash
grok --cwd "$PROJECT" --model "$MODEL" --prompt-file "$PROMPT" --output-format streaming-json --reasoning-effort "$EFFORT" --no-alt-screen --no-subagents --no-plan --permission-mode default > "$ARTIFACT"
```

The result-only command emits streaming JSONL. Concatenate only `text.data` fragments in order, require the terminal `end` event, and retain its session, request, usage, and cost fields. Reasoning and command-inventory events are progress artifacts, not final text.
