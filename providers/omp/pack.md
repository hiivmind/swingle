# Omp notes

CLI: `omp`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| direct non-PTY `-p @file` waits for stdin instead of consuming the referenced file | headless dispatch does not complete | pipe the prompt file contents to `omp ... -p` so end-of-input is explicit | `omp --help`; approved invocation smoke (2026-08-24) |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| result-only headless dispatch | pipe the complete authored `$PROMPT` through native stdin into `omp -p`, pass `$MODEL`, `--thinking "$EFFORT"`, JSON mode, no-tools/no-session as required, set `--cwd "$REPO_ROOT"`, and capture to absolute `$ARTIFACT` | OMP's print mode consumes stdin and its model, thinking, mode, session, tool, and cwd controls are separate | `omp --help`; approved invocation smoke (2026-08-24) |
| prompt, stdin, and workspace transport | use native stdin from `$PROMPT` with `omp ... -p`; do not pass `@file` as the only prompt transport in a non-PTY process | stdin closes naturally and preserves trailing newline bytes | approved invocation smoke (2026-08-24) |
| model discovery and effort encoding | run `omp models`, choose an account-usable `$MODEL` from its grouped provider catalog, and pass its supported level as `--thinking "$EFFORT"` | OMP aggregates providers and exposes per-model context, max-out, and thinking data; the catalog is orientation, not entitlement | `omp models`; `omp --help` |
| structured result interpretation | read final text from the assistant `message_end`, require `agent_end`, and retain the first `session` plus assistant usage/provider/model/cache/cost/stop fields | JSONL separates session identity, incremental lifecycle, final assistant text, completion, and accounting | approved invocation smoke (2026-08-24) |
| mutation permission and verification | preserve the complete authored mutation briefing, pass `--approval-mode write` only for requested writes, and verify exact bytes plus unexpected paths | the approved write mode changed the target exactly, but provider completion remains distinct from repository verification | approved mutation smoke (2026-08-24) |

### Result-only command

```bash
cat "$PROMPT" | omp --model "$MODEL" --thinking "$EFFORT" --mode json --no-tools --no-session --cwd "$REPO_ROOT" -p > "$ARTIFACT"
```

### Structured output

```bash
cat "$PROMPT" | omp --model "$MODEL" --thinking "$EFFORT" --mode json --no-tools --no-session --cwd "$REPO_ROOT" -p > "$ARTIFACT"
```

The result-only command emits JSONL. Use assistant `message_end` text as final response only after `agent_end`; retain the initial `session` identifier and assistant usage/provider/model/cache/cost/stop fields. Lifecycle and tool events are progress signals, not final text.
