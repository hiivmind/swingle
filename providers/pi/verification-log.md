# SDD Dispatch Verification Log — pi

Append-only. Never rewrite prior entries — a later contradiction dates a behavior change.
Format per [verification-protocol.md](../../core/verification-protocol.md).

---

## 2026-07-24 — pi 0.81.1 (trigger: new provider pack — initial verification)

Provider `opencode-go` (Zen) only authed on this machine. Model ids in `provider/model`
form. Scratchpad dispatches, artifacts removed after.

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P1 | Version + surface + catalog | New | `pi --version` = 0.81.1; `pi --list-models opencode-go` lists 16 models incl. deepseek-v4-flash/-pro, minimax-m3, glm-5.2, kimi-k2.7-code, qwen3.7-plus |
| P2 | `pi -p --model <provider/model> "<prompt>"` dispatches | Confirmed | PONG, exit 0, **no banner**, clean stdout |
| P3 | Bogus model error path | New | `Warning: … Using custom model id` then `401 {"type":"ModelError"}`, exit 1 — **validation is remote**, a typo is not caught locally |
| P4 | stdin protection mandatory | Refuted | open stdin under 60s backstop → exit 0; `pi -p` does not read stdin |
| P5 | Read, no flags | Confirmed | returned `XYZZY42` from readtest.txt, exit 0 |
| P6 (file) | Write, no flags | Confirmed | writetest.txt = `HELLO` on disk, exit 0 |
| P6 (command) | Shell, no flags | Confirmed | `echo P6CMD > cmdtest.txt` → `P6CMD` on disk (one earlier attempt exited 0 having only *described* the command — a cheap-model quality miss, not a permission denial; re-run executed it, and `-a` run wrote P6CMD2) |
| P7 | Sandbox escape | N/A | no sandbox claimed (`sandbox: none`); `security.md` documents no isolation |
| P9 | `--thinking` knob | New | valid `high` → exit 0; invalid `bogus` → `Warning: Invalid thinking level … Valid values: off,minimal,low,medium,high,xhigh,max` then proceeds (exit 0) — **locally validated, warned not silently ignored** |
| P10 | Output contract | New | clean stdout, no banner, tool calls print incrementally (log-age stall detection viable); no artifact diversion — `write` tool targets workspace paths (`report-transport: report-file`) |
| P11 | Argument-parsing footguns | New | prompt is a **trailing positional**; `"<prompt>" --thinking low` parsed correctly — no `-p`-eats-next-arg (agy) and no `-p`=password (opencode). `-p`/`--print` REQUIRED for headless |
| Session | Controller-assigned id: create-or-resume | New | `--session-id sdd-test-1` created (warned "creating a new session with that id"); resume by same id recalled `4242` — **`session-source: conversation-id`, no recovery step** |
| Session | Resume portability | New | resume by `--session-id` without `--session-dir` works; sessions stored per-cwd at `~/.pi/agent/sessions/<cwd-slug>/…_<id>.jsonl` — resume from the dispatch cwd |
| Session | Fork | New | `--fork sdd-test-1 --session-id sdd-fork-child` → child recalled parent's `4242`, new session file, parent untouched |
| P12 | Priority-1 tier models dispatch through pi | Confirmed | deepseek-v4-flash, minimax-m3, deepseek-v4-pro, glm-5.2 → PONG exit 0. qwen3.7-plus / kimi-k2.7-code left `experimental` (catalog-present, not dispatched through pi) |

**Not yet run**: P8 (git commit inside workspace — no sandbox, expected writable),
P13 (reviewer known-defect benchmark — required before any pi model is trusted for the
review lane in anger; the review-lane rows are stamped `verified` for *dispatch*, not yet
for *review quality*). Run P13 before relying on pi for adversarial review.

**verified-version stamped 0.81.1** on live end-to-end dispatch evidence above.
