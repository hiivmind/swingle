---
schema-version: 1
id: pi
cli: pi
verified-version: "0.83.0"
version-argv: ["pi", "--version"]
resume-argv: ["pi", "-p", "--session-id", "{session_id}"]
fork-flag: "--fork"
session-source: conversation-id
stall-signal: log-age
report-transport: report-file
list-models-argv: ["pi", "--list-models"]
sandbox: none
---
