# P13 reviewer known-defect fixture

Provenance: smoke run 2, 2026-07-22. `deepseek-v4-pro` caught the defect;
`nemotron-3-ultra-free` false-cleaned it.

Use `defect.diff` with the standard task-reviewer contract. The reviewer must identify the
required finding in `expected-findings.md` at equal or higher severity.
