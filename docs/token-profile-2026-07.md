# Token profile — orchestrator context cost of a swingle dispatch session (2026-07)

**Study spec:** `docs/specs/token-profiling-study.md`. One-off empirical study; the
profiler script is reproduced in the appendix, not shipped as tooling.

## TL;DR

1. **The plugin is not the cost center.** Swingle-attributable context (doctrine reads,
   workspace mechanics, dispatch cycles, plan/spec content) is **~44.5k tokens — 10.8%**
   of a heavy real session's total context growth (411k).
2. **Per-turn harness overhead dominates.** Every orchestrator request carries a fixed
   **~620-token overhead** not visible as message content (system reminders, tool
   envelopes, harness scaffolding). Over a 252-request session that is **~155k tokens
   (37.6%)** — more than 3× the plugin's entire footprint. The lever is therefore
   **turn count**, not prose length.
3. **The session floor is ~50k before anything happens.** Request 1 of a fresh session
   in this repo enters at ~49.9k tokens (system prompt, CLAUDE.md files, tool schemas,
   skill listing, memory) — half of the user-observed "90–100k before delegation" is
   paid before the first keystroke of work.
4. **The playbook's ~1–2k/task claim measures the wrong thing.** Real controller cost
   during plan execution was **~24k tokens and ~20 requests per task** (including its
   reviews and fix rounds); roughly half of that is the per-turn overhead. The ~1–2k
   figure only ever described marginal prompt content.

## Method

Approach C (hybrid) per the spec: the session JSONL's per-request `usage` block gives
ground-truth context totals (`input + cache_read + cache_creation`); message content
(tool results, skill injections, user/assistant text) is sized at ~4 chars/token and
tagged with a named cause; the two are reconciled by fitting
`delta = a × estimated_content + b` per request.

The fit on Transcript A: **`delta = 1.103 × content + 619` per request** (n=250,
residual σ ≈ 830). The tightness of that fit is itself the study's central result: the
content estimate explains context growth almost perfectly once you allow a constant
per-request term — i.e. the "unattributable" cost is not noise, it is a fixed per-turn
overhead.

## Evidence base

- **Transcript A (real-world):** the 2026-07-25 session, 10:50–14:45 UTC, 252 API
  requests: swingle-setup spec → two external adversarial design reviews → plan → 7-task
  SDD dispatch round with per-task reviews and a final whole-branch review. Includes a
  permission-failure investigation on the implementer CLI (real-world noise, deliberately
  retained).
- **Transcript B (controlled):** a fresh headless session in this repo (run on a
  mid-tier model; token structure is model-independent) performing exactly one trivial
  read-only `swingle-delegate` job. Isolates the session-fixed Step-0 cost.

## Transcript A — attribution (calibrated)

Total context growth 411,438 tokens over 252 requests; peak context 340,602; one manual
compaction at 11:24 (123k → 52k).

| Phase bucket | Tokens | Share |
| --- | ---: | ---: |
| per-turn overhead (fixed ~619/request) | 154,819 | 37.6% |
| conversation (user text, non-plugin reads, misc) | 89,386 | 21.7% |
| assistant output (text, thinking, tool-call args) | 72,762 | 17.7% |
| harness floor (request-1 context) | 49,866 | 12.1% |
| dispatch-cycles (prompts, logs, reports, review packages) | 16,422 | 4.0% |
| workspace-mechanics (validate-packs, git, scripts) | 14,808 | 3.6% |
| step0-doctrine (core/, providers/, contracts/ reads) | 12,458 | 3.0% |
| plan-and-spec-content | 822 | 0.2% |

**Plugin-attributable total (last four rows): ~44.5k / 10.8%.**
Tokens before the first external dispatch: **115,559** (request 27, 25 minutes in) —
matching the observed "90–100k before delegation begins".

Largest single named causes: request-1 floor (49.9k); a 14.9k Read of
`skills/delegate/SKILL.md` (development work on the skill itself, not Step-0); the
dispatch wrapper commands (14.8k of Bash tool-call text); the skill-listing attachment
(8.6k, re-injected by the harness); external review reports read back from disk (9.6k).

## Transcript B — controlled Step-0 isolate

A fresh headless session invoked the `swingle-delegate` skill for one trivial
read-only job (count and name the provider packs), dispatched externally, and exited.
The harness ran the skill in a subagent; both contexts were profiled.

**Orchestrator (main) context: 33.2k total** — 30.9k of it the request-1 floor; the
skill work never touched the main context.

**Subagent (the actual Step-0 + dispatch): 72.5k total over 20 requests:**

| Component | Tokens | Share |
| --- | ---: | ---: |
| context floor at request 1 (system prompt, CLAUDE.md, schemas) | 33,796 | 46.6% |
| skill-text injection (the `swingle-delegate` skill entering context) | ~12,000 | 16.5% |
| step0-doctrine reads (playbook, roles, safety, liveness, pack, models) | 11,939 | 16.5% |
| conversation + assistant output | ~14,300 | 19.8% |
| workspace mechanics (trust gate, probes, workspace setup) | 2,250 | 3.1% |
| dispatch cycle (prompt file, wrapper, log, report save) | 4,728 | 6.5% |
| per-turn overhead (~286/request here) | 5,433 | 7.5% |

Context stood at **~60k at the readiness probe and ~68k at the actual external
dispatch**. Add the larger floor of a real interactive session (~50k, vs ~34k for a
headless subagent) and normal conversational investigation, and the observed
"90–100k before delegation" is fully reproduced from measured parts.

**The plugin-controllable slice of Step-0 is ~26k tokens**: skill text (~12k) +
doctrine reads (~12k) + probes/mechanics (~2k). The rest is harness floor and
conversation. Note the installed plugin measured here is v2.1.0 (marketplace cache);
v3.1.0's `--health` mode had not yet replaced the multi-probe sequence this session ran.

## Findings

- **F1 — Turn count is the primary cost lever.** At ~620 tokens/request of fixed
  overhead plus ~1.1× content, every avoided round-trip saves more than most prose
  trims. Batching mechanical steps (playbook E-rules), single-call gates
  (`validate-packs --health` replacing several probe commands), and fewer
  confirm-loops have first-order impact; skill-prose slimming has second-order impact.
- **F2 — Step-0 doctrine reading is cheap (~12.5k) relative to its reputation.** The
  90–100k pre-dispatch observation decomposes as ~50k unavoidable session floor +
  ~30k conversation/investigation + ~12.5k doctrine + mechanics. Cutting doctrine
  prose in half would save ~6k — real but marginal; cutting the floor requires
  harness-level changes (CLAUDE.md size, skill listing, memory) outside the plugin.
- **F3 — The playbook's per-task cost claim needs re-statement.** Execution-phase
  measurement: ~24k tokens and ~20 requests per task including reviews and fix
  rounds (~12k of it per-turn overhead). The ~1–2k/task figure describes dispatch
  prompt content only and should be re-worded or replaced with measured numbers.
- **F4 — The controller re-reads its own repo's skills during development.** In A,
  the single largest plugin-adjacent read (14.9k) was `skills/delegate/SKILL.md` as a
  *development artifact*, not dispatch doctrine. Dev-on-the-plugin sessions double-pay:
  once via the installed skill, once via the working tree.
- **F5 — Harness floor is half the pre-dispatch budget.** ~50k of context exists at
  request 1. Within the plugin's control: nothing. Within the user's control: global
  CLAUDE.md size, memory volume, number of installed plugins/skills (the skill listing
  attachment alone re-injects ~8.6k).

## Reduction backlog (each item cites its evidence row)

- **R1 (from F1):** audit both skills' Step-0 sequences for collapsible round-trips —
  e.g. fold provider detection + config + version drift + readiness into a single
  `validate-packs --health` call (already shipped in v3.1.0) and say so in the skills,
  replacing the multi-command sequence. Filed as a GitHub issue.
- **R2 (from F3):** re-word the playbook's token-economics section with measured
  numbers: per-task ≈ 20 requests / ~24k controller tokens; fixed per-turn overhead
  ~620; session floor ~50k. Filed as a GitHub issue.
- **R3 (from F2):** treat further doctrine-prose slimming as low-priority; do not trade
  functionality for prose cuts (10.8% ceiling). Recorded here; no issue.
- **R4 (from F5/harness):** user-side hygiene note — trim global CLAUDE.md and memory
  when starting dispatch-heavy sessions. Out of plugin scope; recorded here.

## Limits

- One heavy session + one controlled probe; numbers are indicative, not distributions.
- Content-size attribution inside a request apportions by chars/4 and inherits ~10%
  scale error (corrected globally by the calibration fit, not per-row).
- External-provider-side consumption (implementer CLI tokens) is out of scope
  (spec §2); backlog item for a future round.
- Transcript A includes plugin-development work interleaved with dispatch; buckets
  separate them only where paths differ (see F4).

## Appendix — profiler source

The exact script used (stdlib-only Python; run as
`python3 profile_transcript.py <transcript.jsonl>[@stop_request]`):

```python
#!/usr/bin/env python3
"""One-off swingle token profiler (approach C: usage deltas = truth, content = shares).

Parses a Claude Code session transcript (JSONL) into a per-request ledger and a
phase-bucketed attribution table. Stdlib only. See docs/specs/token-profiling-study.md.
"""
import json
import re
import sys
from collections import Counter, defaultdict

CHARS_PER_TOKEN = 4.0

BUCKETS = [
    "harness-floor",
    "skill-injection",
    "step0-doctrine",
    "workspace-mechanics",
    "plan-and-spec-content",
    "dispatch-cycles",
    "assistant-output",
    "conversation",
    "residual",
]

DISPATCH_CMD = re.compile(r"\b(agy|opencode|codex|grok|pi)\b")
STEP0_PATH = re.compile(r"(core/|providers/|contracts/|harnesses/)")
MECH_CMD = re.compile(
    r"(validate-packs|codex-smoke|sdd-workspace|task-brief|review-package|"
    r"\bgit\b|command -v|\bwc\b|\bls\b|mkdir|\bcp\b|pytest|swingle-models|sdd-models)"
)
PLANSPEC_PATH = re.compile(r"(docs/specs/|plans/|-plan\.md|-design\.md)")
DISPATCH_PATH = re.compile(
    r"(-prompt\.md|-report\.md|-review\.md|-dispatch\.log|-brief\.md|"
    r"review-package|progress\.md|\.sdd-dispatch/|\.superpowers/)"
)


def est(text):
    return len(text) / CHARS_PER_TOKEN


def classify_tool(name, tool_input):
    """Bucket for a tool RESULT, from the tool call that produced it."""
    arg = ""
    if isinstance(tool_input, dict):
        arg = str(
            tool_input.get("file_path")
            or tool_input.get("command")
            or tool_input.get("skill")
            or tool_input.get("prompt")
            or ""
        )
    if name == "Skill":
        return "skill-injection", f"Skill:{tool_input.get('skill', '?')}"
    if name in ("Read", "Write", "Edit"):
        if STEP0_PATH.search(arg):
            return "step0-doctrine", f"{name}:{arg[-60:]}"
        if DISPATCH_PATH.search(arg):
            return "dispatch-cycles", f"{name}:{arg[-60:]}"
        if PLANSPEC_PATH.search(arg):
            return "plan-and-spec-content", f"{name}:{arg[-60:]}"
        return "conversation", f"{name}:{arg[-60:]}"
    if name == "Bash":
        if "codex-smoke" in arg or "validate-packs" in arg:
            return "workspace-mechanics", f"Bash:{arg[:60]}"
        if DISPATCH_CMD.search(arg) or DISPATCH_PATH.search(arg):
            return "dispatch-cycles", f"Bash:{arg[:60]}"
        if MECH_CMD.search(arg):
            return "workspace-mechanics", f"Bash:{arg[:60]}"
        return "conversation", f"Bash:{arg[:60]}"
    if name in ("TodoWrite", "TaskCreate", "TaskUpdate", "AskUserQuestion"):
        return "workspace-mechanics", name
    return "conversation", f"{name}"


def iter_records(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def profile(path, stop_request=None):
    # a subagent transcript is entirely sidechain records — profile it as the main line
    treat_sidechain_as_main = "subagents" in path
    tool_calls = {}  # tool_use_id -> (name, input)
    requests = []  # ledger rows
    pending = []  # content items since last assistant request: (bucket, cause, est_tokens)
    seen_msg_ids = set()
    first_dispatch_ctx = None
    sidechain_output = 0.0

    for rec in iter_records(path):
        rtype = rec.get("type")
        if rec.get("isSidechain") and not treat_sidechain_as_main:
            m = rec.get("message") or {}
            u = m.get("usage") or {}
            if m.get("id") and m["id"] not in seen_msg_ids:
                seen_msg_ids.add(m["id"])
                sidechain_output += u.get("output_tokens", 0)
            continue

        if rtype == "attachment":
            att = rec.get("attachment") or {}
            blob = json.dumps(att)
            pending.append(("harness-floor" if not requests else "conversation",
                            f"attachment:{att.get('hookName') or att.get('type')}",
                            est(blob)))
            continue

        if rtype == "user":
            m = rec.get("message") or {}
            content = m.get("content")
            if isinstance(content, str):
                pending.append(("conversation", "user-text", est(content)))
            elif isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    bt = block.get("type")
                    if bt == "tool_result":
                        name, tin = tool_calls.get(block.get("tool_use_id"), ("?", {}))
                        bucket, cause = classify_tool(name, tin or {})
                        pending.append((bucket, cause, est(json.dumps(block.get("content", "")))))
                    elif bt == "text":
                        txt = block.get("text", "")
                        if "<system-reminder>" in txt or "<command-name>" in txt:
                            cause = "system-reminder"
                            bucket = "skill-injection" if "<command-name>" in txt else "conversation"
                        else:
                            cause, bucket = "user-text", "conversation"
                        pending.append((bucket, cause, est(txt)))
            continue

        if rtype != "assistant":
            continue

        m = rec.get("message") or {}
        usage = m.get("usage") or {}
        msg_id = m.get("id") or rec.get("requestId")
        # register tool calls + assistant text
        for block in m.get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                tool_calls[block.get("id")] = (block.get("name"), block.get("input") or {})
                pending.append(("assistant-output", f"tool-call:{block.get('name')}",
                                est(json.dumps(block.get("input") or {}))))
            elif block.get("type") == "text":
                pending.append(("assistant-output", "assistant-text", est(block.get("text", ""))))
            elif block.get("type") == "thinking":
                pending.append(("assistant-output", "assistant-thinking",
                                est(block.get("thinking", ""))))
        if not usage or msg_id in seen_msg_ids:
            continue
        seen_msg_ids.add(msg_id)
        ctx = (usage.get("input_tokens", 0)
               + usage.get("cache_read_input_tokens", 0)
               + usage.get("cache_creation_input_tokens", 0))
        row = {
            "ts": rec.get("timestamp"),
            "ctx": ctx,
            "out": usage.get("output_tokens", 0),
            "items": pending,
        }
        pending = []
        requests.append(row)
        if stop_request and len(requests) >= stop_request:
            break

    # deltas + attribution
    ledger = []
    prev_ctx = 0
    buckets = defaultdict(float)
    causes = defaultdict(float)
    compactions = []
    for i, row in enumerate(requests):
        delta = row["ctx"] - prev_ctx
        explained = sum(t for (_, _, t) in row["items"])
        if i == 0:
            buckets["harness-floor"] += row["ctx"]
            causes["harness-floor:request-1"] += row["ctx"]
            resid = 0.0
        elif delta < -2000:
            compactions.append((i, row["ts"], prev_ctx, row["ctx"]))
            resid = 0.0
        else:
            resid = delta - explained
            for bucket, cause, t in row["items"]:
                buckets[bucket] += t
                causes[cause] += t
            buckets["residual"] += max(resid, 0)
            if resid > 0:
                causes["residual"] += resid
            # over-explained (resid<0): content estimate exceeded truth; scale note only
        ledger.append({**row, "i": i, "delta": delta, "explained": explained,
                       "resid": resid})
        prev_ctx = row["ctx"]

        # first external dispatch marker
        if first_dispatch_ctx is None:
            for bucket, cause, _t in row["items"]:
                if (bucket == "dispatch-cycles" and cause.startswith("Bash:")
                        and DISPATCH_CMD.search(cause)):
                    first_dispatch_ctx = (i, row["ctx"], row["ts"])
                    break
    # calibration: fit delta = a*explained + b over non-compaction requests 1..n
    fit = [r for r in ledger[1:] if r["delta"] > -2000]
    a = b = None
    if len(fit) >= 8:
        n = len(fit)
        sx = sum(r["explained"] for r in fit)
        sy = sum(r["delta"] for r in fit)
        sxx = sum(r["explained"] ** 2 for r in fit)
        sxy = sum(r["explained"] * r["delta"] for r in fit)
        denom = n * sxx - sx * sx
        if denom:
            a = (n * sxy - sx * sy) / denom
            b = (sy - a * sx) / n

    calibrated = None
    if a is not None:
        calibrated = {}
        for bucket, v in buckets.items():
            if bucket in ("harness-floor", "residual"):
                continue
            calibrated[bucket] = v * a
        calibrated["harness-floor"] = buckets.get("harness-floor", 0)
        calibrated["per-turn-overhead"] = b * len(fit)
        growth = ledger[0]["ctx"] + sum(max(r["delta"], 0) for r in ledger[1:])
        calibrated["residual"] = max(growth - sum(calibrated.values()), 0)

    return {
        "requests": ledger,
        "buckets": dict(buckets),
        "causes": dict(causes),
        "compactions": compactions,
        "first_dispatch": first_dispatch_ctx,
        "sidechain_output": sidechain_output,
        "fit": (a, b, len(fit)),
        "calibrated": calibrated,
    }


def report(res, label):
    reqs = res["requests"]
    print(f"\n===== {label} =====")
    print(f"requests: {len(reqs)}   compaction events: {len(res['compactions'])}")
    if res["first_dispatch"]:
        i, ctx, ts = res["first_dispatch"]
        print(f"tokens-before-first-external-dispatch: {ctx:,} (request #{i}, {ts})")
    peak = max(r["ctx"] for r in reqs)
    total_out = sum(r["out"] for r in reqs)
    print(f"peak context: {peak:,}   total assistant output: {total_out:,.0f}"
          f"   sidechain output: {res['sidechain_output']:,.0f}")
    growth = sum(max(r["delta"], 0) for r in reqs[1:]) + reqs[0]["ctx"]
    print(f"total context growth (sum of positive deltas): {growth:,.0f}")
    print("\n-- phase buckets, raw content estimate (tokens, share of growth) --")
    for b in BUCKETS:
        v = res["buckets"].get(b, 0)
        if v:
            print(f"  {b:24s} {v:10,.0f}  {100*v/growth:5.1f}%")
    a, bconst, nfit = res["fit"]
    if a is not None:
        print(f"\n-- calibration: delta = {a:.3f} * explained + {bconst:.0f}"
              f" per request (n={nfit}) --")
        print("-- phase buckets, CALIBRATED (tokens, share of growth) --")
        for b in BUCKETS + ["per-turn-overhead"]:
            v = (res["calibrated"] or {}).get(b, 0)
            if v:
                print(f"  {b:24s} {v:10,.0f}  {100*v/growth:5.1f}%")
    print("\n-- top 25 causes --")
    for cause, v in sorted(res["causes"].items(), key=lambda kv: -kv[1])[:25]:
        print(f"  {v:10,.0f}  {cause}")
    print("\n-- top 10 residual requests (delta far above explained content) --")
    worst = sorted((r for r in reqs if r["resid"] > 0), key=lambda r: -r["resid"])[:10]
    for r in worst:
        top = sorted(r["items"], key=lambda it: -it[2])[:2]
        tops = "; ".join(f"{c}~{t:,.0f}" for (_, c, t) in top)
        print(f"  req#{r['i']:4d} delta={r['delta']:8,} explained={r['explained']:8,.0f}"
              f" resid={r['resid']:8,.0f}  [{tops}]")
    if res["compactions"]:
        print("\n-- compactions --")
        for i, ts, a, b in res["compactions"]:
            print(f"  req#{i} {ts}: {a:,} -> {b:,}")
    # curve (10 samples)
    print("\n-- cumulative context curve (sampled) --")
    step = max(1, len(reqs) // 12)
    for r in reqs[::step]:
        bar = "#" * int(r["ctx"] / 4000)
        print(f"  #{r['i']:4d} {r['ts'][11:19] if r['ts'] else '?':8s} {r['ctx']:9,} {bar}")


if __name__ == "__main__":
    for spec in sys.argv[1:]:
        path, _, stop = spec.partition("@")
        report(profile(path, int(stop) if stop else None),
               path.rsplit("/", 1)[-1] + (f" (first {stop} requests)" if stop else ""))
```
