# Claude notes

CLI: `claude`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| A headless write returns `WRITE_OK` but the target bytes differ from the authored request | provider completion is a false repository-success signal | inspect the result, then verify exact bytes and unexpected paths independently before recording success | `claude --help`; approved mutation smoke (2026-08-24) |
| A never-closing non-TTY stdin pipe leaves `claude -p` running | the headless subprocess does not reach completion | close stdin with `/dev/null` before launch | `claude --help`; approved invocation smoke (2026-08-24) |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| result-only headless dispatch | use `-p` with the complete authored `$PROMPT`, pass `$MODEL` and `$EFFORT` separately, allow only the tool classes required by the prompt, disable session persistence, and capture stdout to absolute `$ARTIFACT` | Claude's print mode, model/effort slots, permission scope, and session behavior are separate controls | `claude --help`; approved invocation smoke (2026-08-24) |
| prompt and stdin transport | pass prompt text as `-p "$(cat \"$PROMPT\")"` and close stdin with `/dev/null` | the approved headless shape completed with closed stdin; the closure avoids the observed open-pipe completion trap | approved invocation smoke (2026-08-24) |
| model discovery and effort encoding | there is no model-listing command; use a current help-supported alias or full model name in `$MODEL`, and pass the requested level as `--effort "$EFFORT"` | aliases such as `fable`, `opus`, and `sonnet` are documented, but entitlement and prices remain live facts | `claude --help` |
| structured result interpretation | require `is_error == false`, a successful subtype, and a completed terminal reason; read final text from `result` and retain `session_id`, usage, model usage, and permission denials | the JSON object separates final text, completion, session, accounting, and denial evidence | approved invocation smoke (2026-08-24) |
| mutation permission and verification | pass the complete authored mutation briefing unchanged, grant only the required tool classes, and verify exact bytes after completion | the approved `acceptEdits` smoke returned `WRITE_OK` while writing incorrect bytes, so provider output cannot replace repository verification | approved mutation smoke (2026-08-24) |

### Result-only command

```bash
claude -p "$(cat "$PROMPT")" --output-format json --model "$MODEL" --effort "$EFFORT" --allowedTools Read --no-session-persistence < /dev/null > "$ARTIFACT"
```

### Structured output

```bash
claude -p "$(cat "$PROMPT")" --output-format json --model "$MODEL" --effort "$EFFORT" --allowedTools Read --no-session-persistence < /dev/null > "$ARTIFACT"
```

The result-only command emits one JSON object. Accept final text from `result` only when `is_error` is false, the subtype is successful, and the terminal reason indicates completion. Keep `session_id`, usage/model-usage, and `permission_denials` as evidence fields; do not infer cost or entitlement from aliases.
