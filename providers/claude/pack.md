---
schema-version: 1
id: claude
cli: claude
verified-version: "2.1.220"
version-argv: ["claude", "--version"]
resume-argv: ["claude", "-p", "--resume", "{session_id}"]
fork-flag: "--fork-session"
session-source: conversation-id
stall-signal: log-age
report-transport: report-file
sandbox: none
---
