# Cursor-agent notes

CLI: `cursor-agent`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| `--print` in an untrusted workspace exits 1 with `Workspace Trust Required` | headless dispatch fails before doing work | pass `--trust` for unattended workspace use, then verify the result | `cursor-agent --help`; approved mutation smoke (2026-08-24) |
| a listed named model is rejected by the account plan while `auto` succeeds | model discovery is mistaken for entitlement and dispatch fails before the task | treat the live list as orientation, retry only with the account-accepted model route, and record the live rejection | `cursor-agent models`; approved invocation and mutation smokes (2026-08-24) |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| result-only headless dispatch | read the complete authored `$PROMPT` into `PROMPT_TEXT`, pass it as Cursor's positional prompt, and use `--print`, JSON output, `--trust`, `$MODEL`, and `$REPO_ROOT`; capture stdout to absolute `$ARTIFACT` | Cursor documents the initial prompt as a positional argument, separate from its workspace, trust, model, and output controls | `cursor-agent --help`; approved invocation smoke (2026-08-24) |
| prompt and workspace transport | load `$PROMPT` with Bash's NUL-delimited `read` builtin, pass `"$PROMPT_TEXT"` as the positional prompt, set `--workspace "$REPO_ROOT"`, and close stdin with `/dev/null` | the approved smoke used a positional prompt with closed stdin; the shell read preserves the authored briefing without command substitution | `cursor-agent --help`; approved invocation smoke (2026-08-24) |
| model discovery and effort encoding | run `cursor-agent models` (or the equivalent `--list-models` help surface), then pass a permitted model in `$MODEL`; encode effort as a quoted bracket override such as `[effort=$EFFORT]` when the selected model supports it | listing is account-scoped, and parameterized model syntax is separate from entitlement | `cursor-agent --help`; `cursor-agent models` |
| structured result interpretation | require `type=result`, `subtype=success`, and `is_error=false`; read final text from `result` and retain session, request, duration, and usage fields | the JSON result includes narration before final text, so the `result` field must remain separate from surrounding output | approved invocation smoke (2026-08-24) |
| mutation permission and verification | preserve the complete authored mutation briefing, pass `--trust`, and verify exact bytes plus unexpected paths after completion | the corrected `auto` route wrote the expected bytes, while the named model was plan-ineligible; provider output is still not repository proof | approved mutation smoke (2026-08-24) |

### Result-only command

```bash
IFS= read -r -d '' PROMPT_TEXT < "$PROMPT" || true
cursor-agent --print --output-format json --trust --model "$MODEL" --workspace "$REPO_ROOT" "$PROMPT_TEXT" < /dev/null > "$ARTIFACT"
```

### Structured output

```bash
IFS= read -r -d '' PROMPT_TEXT < "$PROMPT" || true
cursor-agent --print --output-format json --trust --model "$MODEL" --workspace "$REPO_ROOT" "$PROMPT_TEXT" < /dev/null > "$ARTIFACT"
```

The result-only command emits one JSON object. Accept final text only when `type=result`, `subtype=success`, and `is_error=false`; use `result` as final text and retain `session_id`, `request_id`, duration, and usage. A successful object may contain narration before the final text.
