# Codex notes

CLI: `codex`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| open stdin waits for end-of-input and prevents completion | headless dispatch hangs | close stdin with `/dev/null` before launch; do not mistake the startup stdin banner for progress | `codex exec --help`; approved invocation smoke (2026-08-24) |
| a mutation runs with `workspace-write` and approval `never` but repository state is not independently checked | provider completion can be mistaken for an exact write, and local execpolicy can affect `.git` | keep the authored briefing intact, verify exact bytes and unexpected paths, and record the repository result separately from the provider result | `codex exec --help`; approved mutation smoke (2026-08-24) |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| result-only headless dispatch | use the `exec` subcommand with JSON output, an explicit `$MODEL`, `model_reasoning_effort="$EFFORT"`, sandbox mode, project directory, and an absolute `$ARTIFACT` capture | Codex's headless command is a subcommand and its prompt may be positional or stdin; the effort setting is a config key rather than a generic flag | `codex exec --help`; approved invocation smoke (2026-08-24) |
| prompt and stdin transport | pass the complete authored `$PROMPT` as the positional prompt and close stdin with `/dev/null`; use `-C "$PROJECT"` for the working directory | Codex appends stdin to the prompt and reads to EOF, so an open pipe is a completion trap | `codex exec --help`; approved invocation smoke (2026-08-24) |
| model discovery and effort encoding | run `codex debug models`, choose a listed slug in `$MODEL`, and pass its supported level through `-c "model_reasoning_effort=\"$EFFORT\""` | the live JSON catalog carries slugs and supported reasoning levels; top-level help is not the catalog | `codex debug models`; `codex exec --help` |
| structured result interpretation | require a `turn.completed` event and take final text from the last completed `agent_message`; retain `thread.started.thread_id` and `turn.completed.usage` | Codex JSONL separates lifecycle, messages, completion, session, and usage | approved invocation smoke (2026-08-24) |
| mutation permission and verification | pass the complete authored mutation briefing through stdin unchanged, use only the requested write sandbox and approval settings, and verify exact bytes plus unexpected paths | provider `WRITE_OK` and process exit do not establish repository correctness; user-local execpolicy remains a separate gate | approved mutation smoke (2026-08-24) |

### Result-only command

```bash
codex exec --json --ephemeral --skip-git-repo-check -m "$MODEL" -c "model_reasoning_effort=\"$EFFORT\"" -s read-only -C "$PROJECT" "$(cat "$PROMPT")" < /dev/null > "$ARTIFACT"
```

### Structured output

```bash
codex exec --json --ephemeral --skip-git-repo-check -m "$MODEL" -c "model_reasoning_effort=\"$EFFORT\"" -s read-only -C "$PROJECT" "$(cat "$PROMPT")" < /dev/null > "$ARTIFACT"
```

The result-only command emits JSONL. Accept final text only from the last completed `agent_message` after a `turn.completed` event. Retain the `thread.started.thread_id` and `turn.completed.usage`; lifecycle events and the startup stdin banner are not final text.
