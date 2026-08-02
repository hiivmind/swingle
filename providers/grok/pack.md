---
schema-version: 1
id: grok
cli: grok
verified-version: "0.2.117"
version-argv: ["grok", "--version"]
resume-argv: ["grok", "--resume", "{session_id}"]
fork-flag: "--fork-session"
session-source: exec-output
session-list-argv: ["grok", "sessions", "list"]
stall-signal: log-age
report-transport: report-file
sandbox: enforced
readiness-argv: ["grok", "models"]
---
