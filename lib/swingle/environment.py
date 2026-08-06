"""Environment introspection: install/version/readiness probes and health report.

Extracted verbatim from the former scripts/validate-packs (stdlib only). No findings
collector: these functions probe the machine and return values; callers decide.
"""
import os
import subprocess
from pathlib import Path

from .packs import VERSION_TOKEN_RE, VER_RE
from .resolve import resolve_models

HEALTH_PROBE_TIMEOUT_SECONDS = 30


def get_path_dirs(path_dirs):
    return path_dirs if path_dirs else os.environ.get("PATH", "").split(os.pathsep)


def is_provider_installed(fm, path_dirs):
    cli = fm.get("cli", "")
    if not cli: return False
    return any((Path(directory) / cli).exists() and os.access(Path(directory) / cli, os.X_OK) for directory in get_path_dirs(path_dirs))


def detect_installed_providers(manifests, path_dirs):
    return [provider for provider, fm in manifests.items() if is_provider_installed(fm, path_dirs)]


def check_provider_version(fm, path_dirs, timeout):
    rc, output = run_argv(fm["version-argv"], path_dirs, timeout)
    if rc < 0:
        # timeout (-2) / OSError (-1): output is the exception message, and a
        # dotted number in it (e.g. the timeout value) is not a version.
        return rc, output, None
    # Preserve the CLI's raw version token.  A suffix (or any other wrapper)
    # makes the token unparseable; never compare an extracted numeric prefix.
    match = VERSION_TOKEN_RE.search(output or "")
    raw_token = match.group(0) if match else None
    return rc, output, raw_token if raw_token and VER_RE.fullmatch(raw_token) else None


def check_provider_readiness(fm, path_dirs, timeout):
    ready_argv = fm.get("readiness-argv") or fm["version-argv"]
    rc, output = run_argv(ready_argv, path_dirs, timeout)
    if rc == 0: status = "ok"
    elif rc == -2: status = "timeout"
    else: status = "fail"
    return rc, status


def run_health(manifests, path_dirs, root, project, scoped_providers, config_arg):
    from .config import resolve_config_layer
    target_providers = sorted(manifests.keys())
    if scoped_providers:
        scoped_set = set(scoped_providers)
        target_providers = [p for p in scoped_providers if p in manifests] + [p for p in sorted(manifests.keys()) if p in scoped_set and p not in scoped_providers]

    for provider_id in target_providers:
        fm = manifests[provider_id]
        installed = is_provider_installed(fm, path_dirs)
        verified_ver = fm.get("verified-version", "")

        if not installed:
            inst_str = "no"
            ver_str = "-"
            drift_str = "no"
            readiness_str = "skipped"
        else:
            inst_str = "yes"
            rc, output, actual_ver = check_provider_version(fm, path_dirs, HEALTH_PROBE_TIMEOUT_SECONDS)
            if actual_ver:
                ver_str = actual_ver
                drift_str = "no" if actual_ver == verified_ver else "yes"
            else:
                ver_str = "-"
                drift_str = "yes"

            ready_rc, ready_status = check_provider_readiness(fm, path_dirs, HEALTH_PROBE_TIMEOUT_SECONDS)
            readiness_str = ready_status

        layer, _, _ = resolve_models(provider_id, root, project)
        reg_layer_str = layer if layer else "-"

        print(f"{provider_id}: installed={inst_str} version={ver_str} verified={verified_ver} drift={drift_str} readiness={readiness_str} registry-layer={reg_layer_str}")

    cfg_layer = resolve_config_layer(config_arg, project)
    print(f"config-layer={cfg_layer}")


def run_argv(argv, path_dirs, timeout):
    try:
        env_path = os.pathsep.join(path_dirs) if path_dirs else os.environ.get("PATH", "")
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=dict(os.environ, PATH=env_path))
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired as error: return -2, str(error)
    except OSError as error: return -1, str(error)
