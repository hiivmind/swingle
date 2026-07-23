---
name: Verification finding
about: Report a live dispatch finding against a provider pack (behavior change, new gotcha, model change) when you cannot commit to a source checkout
title: "[<provider> <cli-version>] <one-line finding>"
labels: verification
---

## Environment

- Provider / CLI version (`<version-argv>` output):
- Plugin version (README `**Version:**` of the copy you ran):
- Copy type: installed cache (Claude Code / Codex) or source checkout:
- OS:

## Trigger

version bump | model release | anomaly during a run | quarterly re-verify

## Finding

- **Assertion under test** (quote the pack.md/models.md line):
- **Verdict**: Confirmed / Refuted / Refined / New
- **Evidence** (verbatim command + observed output; redact secrets):

```text

```

## Impact

Which dispatch step breaks or changes (template, liveness, permissions, resume,
model resolution), and any workaround you used.
