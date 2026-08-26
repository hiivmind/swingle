# Agy notes

CLI: `agy`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| A permission-denied headless run exits successfully without the requested work | the controller can record a phantom success | use the mode supported by the requested tool, then verify the expected bytes and paths independently | `agy --help`; approved mutation smoke (2026-08-24) |
| JSON output is one buffered terminal object with no incremental progress | a healthy run can be diagnosed as stalled while it is still working | retain the process, observe `--print-timeout`, and use the generic liveness policy rather than silence alone | `agy --help`; approved invocation smoke (2026-08-24) |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| result-only headless dispatch | read the complete authored `$PROMPT` into `PROMPT_TEXT`, pass it as the `--print` argument, select `$MODEL` and `$EFFORT` separately, set `--mode plan`, and capture stdout to the absolute `$ARTIFACT` path | Agy's evidenced noninteractive shape takes the prompt as the `--print` argument; the shell read preserves prompt newlines without command substitution | `agy --help`; approved invocation smoke (2026-08-24) |
| prompt and workspace transport | load `$PROMPT` with Bash's NUL-delimited `read` builtin, pass `"$PROMPT_TEXT"` to `--print`, and select the project with `--add-dir "$REPO_ROOT"` | the approved smoke used the `--print` argument, while the shell read preserves quotes, metacharacters, and trailing newlines | `agy --help`; approved invocation smoke (2026-08-24) |
| model discovery and effort encoding | run `agy models`, then pass one listed effort-qualified ID to `$MODEL` and its requested level to `--effort "$EFFORT"` | the live IDs carry `-low`, `-medium`, or `-high` suffixes, while help exposes a separate effort flag; neither should be guessed | `agy models`; `agy --help` |
| structured result interpretation | require JSON `status == SUCCESS`, then read final text from `response`; retain `conversation_id`, duration, turns, and usage fields as provider metadata | Agy emits one terminal object whose success and final-text fields are distinct from process exit status | approved invocation smoke (2026-08-24) |
| mutation permission and verification | pass the complete authored mutation briefing unchanged, use the mode required by the tool class, and verify exact bytes plus unexpected paths after completion | `--mode accept-edits` completed the approved write smoke, but provider success is not repository verification | approved mutation smoke (2026-08-24) |

### Result-only command

```bash
IFS= read -r -d '' PROMPT_TEXT < "$PROMPT" || true
agy --print "$PROMPT_TEXT" --model "$MODEL" --effort "$EFFORT" --output-format json --print-timeout 180s --mode plan --add-dir "$REPO_ROOT" < /dev/null > "$ARTIFACT"
```

### Structured output

```bash
IFS= read -r -d '' PROMPT_TEXT < "$PROMPT" || true
agy --print "$PROMPT_TEXT" --model "$MODEL" --effort "$EFFORT" --output-format json --print-timeout 180s --mode plan --add-dir "$REPO_ROOT" < /dev/null > "$ARTIFACT"
```

The result-only command emits one JSON object. Accept it only when `status` is `SUCCESS`; use `response` as final text, and retain `conversation_id`, duration, turns, and usage for the report. Do not treat a zero exit code without that status as completion.
