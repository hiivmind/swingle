---
schema-version: 1
id: omp
cli: omp
verified-version: "17.2.4"
version-argv: ["omp", "--version"]
resume-argv: ["omp", "-p", "-r", "{session_id}"]
session-source: exec-output
stall-signal: log-age
report-transport: captured-output
list-models-argv: ["omp", "models"]
sandbox: none
---
