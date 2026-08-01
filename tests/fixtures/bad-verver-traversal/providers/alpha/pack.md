---
schema-version: 1
nested:
  key: v
id: alpha
cli: alpha
verified-version: "../../evil"
version-argv: ['alpha', '--version']
resume-argv: ["alpha", "resume", "{session_id}"]
session-source: exec-output
stall-signal: log-age
sandbox: enforced
---
