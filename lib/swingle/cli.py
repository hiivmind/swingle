"""validate-packs combined CLI: argparse + dispatch across the swingle modules.

Preserves the exact argument surface, stdout, and exit codes of the former
scripts/validate-packs main().
"""

import argparse
import sys
from pathlib import Path

from . import report
from . import packs
from . import config as config_mod
from . import resolve as resolve_mod
from . import environment
from . import step0 as step0_mod
from .audit import repo as audit_repo


def validate_packs_main():
    report.reset()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--resolve", nargs=2, metavar=("ROLE", "PROVIDER"))
    ap.add_argument("--exclude", action="append", default=[])
    ap.add_argument("--check-config")
    ap.add_argument("--step0", action="store_true")
    ap.add_argument("--health", action="store_true")
    ap.add_argument("--provider", action="append", default=[])
    ap.add_argument("--config")
    ap.add_argument("--path-dir", action="append", default=[])
    ap.add_argument("--lever")
    ap.add_argument("--task-provider")
    ap.add_argument("--role")
    ap.add_argument("--project")
    a = ap.parse_args()
    root, excluded = Path(a.root), {}
    for exclusion in a.exclude:
        provider, _, model = exclusion.partition(":")
        excluded.setdefault(provider, set()).add(model)
    manifests, rows_by_id, packs_found = packs.load_packs(root)
    if a.check_config:
        config_mod.load_config(a.check_config, set(manifests))
    if not (a.check_config or a.step0 or a.health or a.resolve):
        audit_repo.check_repo_docs(root, manifests)
    if a.health:
        environment.run_health(
            manifests, a.path_dir, root, a.project, a.provider, a.config
        )
    elif a.step0:
        rc = step0_mod.run_step0(
            manifests,
            root,
            a.path_dir,
            a.lever,
            a.task_provider,
            a.config,
            a.role,
            a.project,
            excluded,
        )
        if rc is not None:
            return rc
    elif a.resolve:
        resolve_mod.run_resolve(
            root, rows_by_id, a.resolve[0], a.resolve[1], a.project, excluded
        )
    for finding in report.findings:
        print(finding)
    return 1 if report.findings else 0
