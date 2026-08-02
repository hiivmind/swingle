---
schema-version: 1
id: codex
cli: codex
verified-version: "0.146.0"
version-argv: ["codex", "--version"]
readiness-argv: ["codex", "login", "status"]
resume-argv: ["codex", "exec", "resume", "{session_id}"]
session-source: exec-output
stall-signal: log-age
report-transport: report-file
sandbox: enforced
---
