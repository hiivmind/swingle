"""Dispatch configuration parsing/gating and config-layer resolution.

Extracted verbatim from the former scripts/validate-packs (stdlib only).
"""
import json
import os
import re
import sys
from pathlib import Path

from .report import find
from .packs import NAME_RE

CONFIG_KEYS = {"disable": list, "default_provider": str, "providers_by_lane": dict, "require-verified-version": bool, "note": str, "superpowers": dict}
PROBED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def check_superpowers_block(path, block, provider_ids=None):
    """Setup-recorded environment facts (worktree-dispatch spec §4): per-provider
    superpowers availability. Malformed is a STOP finding, never a silent drop."""
    ok = True
    for provider, rec in block.items():
        if not NAME_RE.match(str(provider)): find(f"{path}: superpowers: bad provider id {provider}"); ok = False; continue
        if provider_ids is not None and provider not in provider_ids:
            find(f"{path}: superpowers names unknown provider {provider}"); ok = False; continue  # matching the other provider-bearing keys
        if not isinstance(rec, dict): find(f"{path}: superpowers[{provider}] must be an object"); ok = False; continue
        for key in rec:
            if key not in {"installed", "version", "probed"}: find(f"{path}: superpowers[{provider}]: unknown key {key}"); ok = False
        if not isinstance(rec.get("installed"), bool): find(f"{path}: superpowers[{provider}].installed must be a boolean"); ok = False
        if not (rec.get("version") is None or isinstance(rec.get("version"), str)): find(f"{path}: superpowers[{provider}].version must be a string or null"); ok = False
        if not (isinstance(rec.get("probed"), str) and PROBED_RE.match(rec["probed"])): find(f"{path}: superpowers[{provider}].probed must be YYYY-MM-DD"); ok = False
    return ok


def load_config(path, provider_ids=None):
    if path is None: return {}
    try: cfg = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as error: find(f"{path}: unreadable/malformed ({error})"); return None
    if not isinstance(cfg, dict): find(f"{path}: config root must be an object"); return None
    for key, value in list(cfg.items()):
        if key not in CONFIG_KEYS: print(f"warn: unknown key {key}", file=sys.stderr); cfg.pop(key); continue
        if not isinstance(value, CONFIG_KEYS[key]): find(f"{path}: {key} has wrong type"); return None
    if not all(isinstance(value, str) for value in cfg.get("disable", [])): find(f"{path}: disable entries must be strings"); return None
    for lane, provider in cfg.get("providers_by_lane", {}).items():
        if lane not in {"implement", "review"}: find(f"{path}: providers_by_lane bad lane {lane}")
        if not isinstance(provider, str): find(f"{path}: providers_by_lane values must be strings")
    if "superpowers" in cfg and not check_superpowers_block(path, cfg["superpowers"], provider_ids): return None
    if provider_ids is not None:

        for provider in cfg.get("disable", []):
            if provider not in provider_ids: find(f"{path}: disable names unknown provider {provider}")
        default = cfg.get("default_provider")
        if default is not None and default not in provider_ids: find(f"{path}: default_provider names unknown provider {default}")
        for lane, provider in cfg.get("providers_by_lane", {}).items():
            if isinstance(provider, str) and provider not in provider_ids: find(f"{path}: providers_by_lane[{lane}] names unknown provider {provider}")
    disabled = set(cfg.get("disable", []))
    if cfg.get("default_provider") in disabled: find(f"{path}: default_provider is disabled")
    for lane, provider in cfg.get("providers_by_lane", {}).items():
        if provider in disabled: find(f"{path}: providers_by_lane[{lane}] names disabled provider {provider}")
    return cfg


def resolve_config_layer(config_arg, project_dir):
    env_config = config_arg or os.environ.get("SWINGLE_CONFIG")
    if env_config:
        p = Path(env_config)
        if p.is_file() and os.access(p, os.R_OK): return "env"
        return "env-unreadable"
    if project_dir:
        p = Path(project_dir) / ".swingle.json"
        if p.is_file() and os.access(p, os.R_OK): return "project"
    xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    p = Path(xdg) / "swingle" / "config.json"
    if p.is_file() and os.access(p, os.R_OK): return "user"
    return "none"
