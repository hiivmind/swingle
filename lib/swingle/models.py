"""Layered models.yaml helper: seed and inspect override layers.

Resolution is imported from swingle.resolve — the single implementation of the layered
walk (spec 2026-07-24). This module adds no precedence logic of its own. Moved from the
former scripts/swingle-models; the SourceFileLoader hack is gone.
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

from . import report
from .resolve import resolve_models
from .packs import parse_front_matter


def main(default_root):
    report.reset()
    ap = argparse.ArgumentParser(prog="swingle-models")
    sub = ap.add_subparsers(dest="command", required=True)
    which = sub.add_parser("which"); which.add_argument("provider", nargs="?")
    init = sub.add_parser("init"); init.add_argument("provider", nargs="?")
    dest = init.add_mutually_exclusive_group(required=True)
    dest.add_argument("--project"); dest.add_argument("--user", action="store_true")
    init.add_argument("--force", action="store_true")
    for p in (which, init):
        p.add_argument("--root", default=str(default_root))
        if p is which: p.add_argument("--project")
    a = ap.parse_args()
    root = Path(a.root)
    providers = sorted(d.name for d in (root / "providers").glob("*/") if (d / "pack.md").exists())
    targets = [a.provider] if a.provider else providers
    for provider in targets:
        if provider not in providers:
            print(f"unknown provider: {provider}", file=sys.stderr); return 1
    if a.command == "which":
        for provider in targets:
            layer, path, _ = resolve_models(provider, root, a.project)
            if report.findings:
                for f in report.findings: print(f, file=sys.stderr)
                return 1
            print(f"{provider}: layer={layer} path={path.resolve()}")
        return 0
    # init — no provider argument seeds every shipped provider
    for provider in targets:
        layer, source, _ = resolve_models(provider, root, getattr(a, "project", None))
        if report.findings:
            for f in report.findings: print(f, file=sys.stderr)
            return 1
        if a.user:
            xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
            dest_path = Path(xdg) / "swingle" / "models" / f"{provider}.yaml"
        else:
            dest_path = Path(a.project) / ".swingle" / "models" / f"{provider}.yaml"
        if dest_path.exists() and not a.force:
            print(f"{dest_path} exists — pass --force to overwrite", file=sys.stderr); return 1
        if source.resolve() == dest_path.resolve():
            print(f"{dest_path} already current (layer={layer})")
            continue
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest_path)
        print(f"seeded {dest_path} from layer={layer} ({source})")
        manifest = parse_front_matter(root / "providers" / provider / "pack.md")
        argv = manifest.get("list-models-argv")
        if argv:
            print(f"open catalog: align rows with the live list — run: {' '.join(argv)}")
    return 0
