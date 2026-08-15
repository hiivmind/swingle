"""Step-0 dispatch simulator: the executable rendering of the skills' outcome table.

Extracted verbatim from the former scripts/validate-packs `--step0` branch. Kept a
single named implementation so it stays lockstep with the swingle-sdd / swingle-delegate
Markdown outcome tables (see repo CLAUDE.md). OUTCOME_PREFIXES enumerates every typed
line this module can emit; tests/test_step0_lockstep.py asserts it matches both skills.
"""

from .report import find, findings
from .config import load_config
from .environment import (
    detect_installed_providers,
    check_provider_version,
    check_provider_readiness,
)
from .resolve import parse_roles, resolve_models, candidate_order

# Every typed outcome line run_step0 can print or find(). Advisory/status lines plus the
# STOP:/ASK:/CHANNEL:/warning: classes the dispatch skills adjudicate.
OUTCOME_PREFIXES = {
    "STOP:",
    "ASK:",
    "CHANNEL:",
    "warning:",
    "native-subagents:",
    "installed:",
    "active:",
    "provider:",
    "layer:",
    "model:",
    "ready:",
    "available (auth unverified):",
}


def run_step0(
    manifests,
    root,
    path_dir,
    lever,
    task_provider,
    config_arg,
    role_arg,
    project,
    excluded,
):
    """Returns an exit code to short-circuit (findings already printed), or None to fall
    through to the caller's final findings print."""
    # Native bypass first (rev 4): no provider is selected, so provider config is irrelevant.
    if lever == "native-subagents":
        if findings:
            for finding in findings:
                print(finding)
            return 1
        print("native-subagents: bypass external dispatch (no provider selected)")
    else:
        cfg = load_config(config_arg, set(manifests))
        # Never detect or execute provider argv until every data-only input is valid.
        if findings:
            for finding in findings:
                print(finding)
            return 1
        installed = detect_installed_providers(manifests, path_dir)
        print(f"installed: {' '.join(installed) or '(none)'}")
        active = [
            provider
            for provider in installed
            if provider not in set(cfg.get("disable", []))
        ]
        strict = bool(cfg.get("require-verified-version"))
        if strict:
            # Full active-set probe is required only here: it filters the active set
            # before routing (an incompatible provider must not be routable).
            incompatible = []
            for provider in active:
                timeout = int(manifests[provider].get("readiness-timeout-seconds", 30))
                rc, output, actual_ver = check_provider_version(
                    manifests[provider], path_dir, timeout
                )
                verified_ver = manifests[provider].get("verified-version")
                if rc != 0 or not actual_ver or actual_ver != verified_ver:
                    actual = actual_ver if actual_ver else "unparseable"
                    print(
                        f"warning: incompatible: {provider} ({actual} != {verified_ver})"
                    )
                    incompatible.append(provider)
            dropped = set(incompatible)
            if dropped:
                print(
                    f"warning: incompatible providers removed: {' '.join(sorted(dropped))}"
                )
            active = [provider for provider in active if provider not in dropped]
        if not active:
            find("ASK: no active providers")
        else:
            print(f"active: {' '.join(active)}")
            role_tier_lane = None
            if role_arg:
                roles = parse_roles(root)
                role_tier_lane = next(
                    (value for key, value in roles.items() if role_arg.lower() in key),
                    None,
                )
                if not role_tier_lane:
                    find(f"STOP: unknown role: {role_arg}")
            lane = role_tier_lane[1] if role_tier_lane else None
            chosen = (
                task_provider
                or lever
                or (cfg.get("providers_by_lane", {}).get(lane) if lane else None)
                or cfg.get("default_provider")
                or (
                    "codex"
                    if "codex" in active
                    else (active[0] if len(active) == 1 else None)
                )
            )
            if chosen and chosen not in active:
                find(f"ASK: routed provider inactive: {chosen}")
            elif not chosen:
                find("ASK: route-selection: ask user (multiple active, no policy)")
            else:
                print(f"provider: {chosen}")
                if role_tier_lane:
                    layer, layer_path, layer_rows = resolve_models(
                        chosen, root, project
                    )
                    if layer_path is not None:
                        print(f"layer: {layer} path={layer_path.resolve()}")
                    order = candidate_order(
                        layer_rows, *role_tier_lane, excluded.get(chosen, set())
                    )
                    if not order and layer in ("env", "project", "user"):
                        find(
                            f"ASK: no eligible model for {role_tier_lane} in {chosen} — override at {layer_path} does not cover {role_tier_lane}"
                        )
                    elif not order:
                        find(f"ASK: no eligible model for {role_tier_lane} in {chosen}")
                    else:
                        print(
                            f"model: {order[0]['model']} (P{order[0]['prio']}); fallback: {', '.join(row['model'] for row in order)}"
                        )
                if not strict:
                    # Part A: probe ONLY the routed provider for the drift advisory.
                    timeout = int(
                        manifests[chosen].get("readiness-timeout-seconds", 30)
                    )
                    rc, output, actual_ver = check_provider_version(
                        manifests[chosen], path_dir, timeout
                    )
                    verified_ver = manifests[chosen].get("verified-version")
                    if rc != 0 or not actual_ver or actual_ver != verified_ver:
                        actual = actual_ver if actual_ver else "unparseable"
                        print(
                            f"warning: incompatible: {chosen} ({actual} != {verified_ver})"
                        )
                rc, _ = check_provider_readiness(
                    manifests[chosen],
                    path_dir,
                    int(manifests[chosen].get("readiness-timeout-seconds", 30)),
                )
                if rc != 0:
                    find(f"CHANNEL: provider not ready: {chosen} (exit {rc})")
                elif manifests[chosen].get("readiness-argv"):
                    print(f"ready: {chosen}")
                else:
                    # readiness fell back to version-argv — proves CLI availability, not auth.
                    print(f"available (auth unverified): {chosen}")
    return None
