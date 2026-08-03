---
schema-version: 1
id: agy
cli: agy
verified-version: "1.1.9"
version-argv: ["agy", "--version"]
readiness-argv: ["agy", "models"]
resume-argv: ["agy", "--conversation", "{session_id}"]
session-source: conversation-id
stall-signal: process+print-timeout
report-transport: captured-output
sandbox: none
---
