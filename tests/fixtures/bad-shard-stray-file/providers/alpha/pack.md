---
schema-version: 1
id: alpha
cli: alpha
verified-version: "1.0.0"
version-argv: ["alpha", "--version"]
resume-argv: ["alpha", "resume", "{session_id}"]
readiness-argv: ["alpha", "ready"]
session-source: exec-output
stall-signal: log-age
sandbox: enforced
---

