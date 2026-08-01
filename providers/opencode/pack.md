---
schema-version: 1
id: opencode
cli: opencode
verified-version: "1.18.10"
version-argv: ["opencode", "--version"]
resume-argv: ["opencode", "run", "-s", "{session_id}"]
fork-flag: "--fork"
session-source: session-list
session-list-argv: ["opencode", "session", "list"]
stall-signal: log-age
report-transport: report-file
sandbox: none
readiness-argv: ["opencode", "session", "list"]
---
