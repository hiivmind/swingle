# Opencode notes

CLI: `opencode`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| result-only headless dispatch | read the complete authored `$PROMPT` into `PROMPT_TEXT`, pass it as the positional `message` to `run`, and set `--dir "$REPO_ROOT"`, provider-prefixed `$MODEL`, `--variant "$EFFORT"`, the output format, and absolute `$ARTIFACT` capture | Opencode documents the prompt as positional `message` input; project, model, effort, and output controls are separate | `opencode run --help`; approved invocation smoke (2026-08-24) |
| prompt and workspace transport | load `$PROMPT` with Bash's NUL-delimited `read` builtin, pass `"$PROMPT_TEXT"` as the positional message, and select the project with `--dir "$REPO_ROOT"` | the approved smoke used a positional prompt; the shell read preserves prompt bytes without command substitution | `opencode run --help`; approved invocation smoke (2026-08-24) |
| model discovery and effort encoding | run `opencode models`, preserve the provider prefix in `$MODEL`, and pass the selected model's supported value as `--variant "$EFFORT"`; verify the route because unsupported variants may be ignored | provider-prefixed IDs are required, and absence of a variant error is not proof that the effort took effect | `opencode models`; `opencode run --help`; approved invocation smoke (2026-08-24) |
| absolute artifact capture | redirect or tee to an absolute `$ARTIFACT` path outside assumptions about `--dir` | shell capture paths follow the shell working directory, not Opencode's provider project directory | approved invocation smoke (2026-08-24) |
| structured result interpretation | in JSON mode concatenate `text.part.text` and require `step_finish`; retain session, stop, token, cache, and cost fields from `step_finish` | event output separates final text and completion/accounting from ordinary progress events | approved invocation smoke (2026-08-24) |
| session identity | retain the session ID from `step_finish`; treat `--continue`/`--fork` as live operations rather than continuity guarantees | current evidence captured identity and help syntax but did not run a second-turn resume/fork | `opencode run --help`; approved invocation smoke (2026-08-24) |
| mutation permission and verification | preserve the complete authored mutation briefing, use the selected noninteractive permission route, and verify exact bytes plus unexpected paths | the approved default route performed read/write/read and matched the target exactly; provider `WRITE_OK` is not repository proof | approved mutation smoke (2026-08-24) |

### Result-only command

```bash
IFS= read -r -d '' PROMPT_TEXT < "$PROMPT" || true
opencode run --dir "$REPO_ROOT" --model "$MODEL" --variant "$EFFORT" --format default "$PROMPT_TEXT" < /dev/null > "$ARTIFACT"
```

### Structured output

```bash
IFS= read -r -d '' PROMPT_TEXT < "$PROMPT" || true
opencode run --dir "$REPO_ROOT" --model "$MODEL" --variant "$EFFORT" --format json "$PROMPT_TEXT" < /dev/null > "$ARTIFACT"
```

In JSON mode, concatenate `text.part.text` for final text and require `step_finish` for completion. Retain its session ID, stop reason, tokens, cache fields, and cost; ordinary `step_start`/`text` events are progress, not completion.
