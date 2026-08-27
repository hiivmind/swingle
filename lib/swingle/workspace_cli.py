from __future__ import annotations

from pathlib import Path
from typing import Any

from .workspace import show_workspace, verify_workspace


def add_workspace_parser(commands: Any, parser_class: Any) -> None:
    workspace = commands.add_parser("workspace")
    workspace_commands = workspace.add_subparsers(dest="workspace_command", required=True, parser_class=parser_class)

    show = workspace_commands.add_parser("show")
    show.add_argument("--run", required=True)
    show.add_argument("--job")
    show.add_argument("--file", action="append", default=[])
    show.add_argument("--json", action="store_true")

    verify = workspace_commands.add_parser("verify")
    verify.add_argument("--run", required=True)
    verify.add_argument("--job")
    verify.add_argument("--json", action="store_true")


def _render_show_text(result: dict[str, Any]) -> str:
    lines = [f"run {result['run_id']} status={result['run_status']}"]
    for job in result["jobs"]:
        lines.append(
            f"  job {job['job_id']} status={job['terminal_status']} manifest={job['manifest_state']} "
            f"files={len(job['selected_files'])} bytes={job['selected_bytes']}"
        )
    lines.append(f"selected_paths={len(result['selected_paths'])} byte_count={result['byte_count']}")
    if result["orphan_artifact_directories"]:
        lines.append("orphan artifact directories:")
        lines.extend(f"  {path}" for path in result["orphan_artifact_directories"])
    return "\n".join(lines) + "\n"


def _render_verify_text(result: dict[str, Any]) -> str:
    lines = [
        f"run {result['run_id']} status={result['run_status']} valid={result['valid']}",
        f"verified_files={result['verified_files']} verified_bytes={result['verified_bytes']}",
    ]
    for job_id, state in result["manifest_states"].items():
        lines.append(f"  job {job_id} manifest={state}")
    if result["active_job_ids"]:
        lines.append(f"active job_ids: {', '.join(result['active_job_ids'])}")
    return "\n".join(lines) + "\n"


def handle_workspace(args: Any, *, cwd: Path) -> dict[str, Any] | str:
    if args.workspace_command == "show":
        result = show_workspace(run_id=args.run, job_id=args.job, file_paths=tuple(args.file), cwd=cwd)
        return result if args.json else _render_show_text(result)
    if args.workspace_command == "verify":
        result = verify_workspace(run_id=args.run, job_id=args.job, cwd=cwd)
        return result if args.json else _render_verify_text(result)
    raise ValueError(f"unsupported workspace command: {args.workspace_command}")
