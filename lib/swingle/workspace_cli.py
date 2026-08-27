from __future__ import annotations

from pathlib import Path
from typing import Any

from .workspace import apply_delete, copy_workspace, preview_delete, show_workspace, verify_workspace


def add_workspace_parser(commands: Any, parser_class: Any) -> None:
    workspace = commands.add_parser("workspace")
    workspace_commands = workspace.add_subparsers(dest="workspace_command", required=True, parser_class=parser_class)

    show = workspace_commands.add_parser("show")
    show.add_argument("--run", required=True)
    show.add_argument("--job")
    show.add_argument("--file", action="append", default=[])
    show.add_argument("--to")
    show.add_argument("--json", action="store_true")

    verify = workspace_commands.add_parser("verify")
    verify.add_argument("--run", required=True)
    verify.add_argument("--job")
    verify.add_argument("--json", action="store_true")

    copy = workspace_commands.add_parser("copy")
    copy.add_argument("--run", required=True)
    copy.add_argument("--job")
    copy.add_argument("--file", action="append", default=[])
    copy.add_argument("--to", required=True)
    copy.add_argument("--json", action="store_true")

    delete = workspace_commands.add_parser("delete")
    delete.add_argument("--run", required=True)
    delete.add_argument("--job")
    delete.add_argument("--expect-selection-sha256")
    delete.add_argument("--apply", action="store_true")
    delete.add_argument("--json", action="store_true")


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
    if result["destination"] is not None:
        lines.append(f"destination {result['destination']} state={result['destination_state']}")
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


def _render_copy_text(result: dict[str, Any]) -> str:
    lines = [
        f"run {result['run_id']} status={result['status']}",
        f"destination {result['destination']}",
        f"file_count={result['file_count']} byte_count={result['byte_count']}",
        f"tree_sha256={result['tree_sha256']}",
    ]
    return "\n".join(lines) + "\n"


def _render_delete_text(result: dict[str, Any]) -> str:
    if result["applied"]:
        lines = [
            f"run {result['run_id']} job {result['job_id']} applied=true",
            f"deleted_path={result['deleted_path']}",
            f"deleted_files={result['deleted_files']} deleted_bytes={result['deleted_bytes']}",
        ]
        return "\n".join(lines) + "\n"
    lines = [
        f"run {result['run_id']} job {result['job_id']} applied=false",
        f"selection_sha256={result['selection_sha256']}",
        f"byte_count={result['byte_count']}",
    ]
    lines.extend(f"dir {path}" for path in result["directories"])
    lines.extend(f"file {item['path']} ({item['size_bytes']}B)" for item in result["files"])
    return "\n".join(lines) + "\n"


def handle_workspace(args: Any, *, cwd: Path) -> dict[str, Any] | str:
    if args.workspace_command == "show":
        result = show_workspace(
            run_id=args.run, job_id=args.job, file_paths=tuple(args.file), destination=args.to, cwd=cwd
        )
        return result if args.json else _render_show_text(result)
    if args.workspace_command == "verify":
        result = verify_workspace(run_id=args.run, job_id=args.job, cwd=cwd)
        return result if args.json else _render_verify_text(result)
    if args.workspace_command == "copy":
        result = copy_workspace(
            run_id=args.run, job_id=args.job, file_paths=tuple(args.file), destination=args.to, cwd=cwd
        )
        return result if args.json else _render_copy_text(result)
    if args.workspace_command == "delete":
        if args.apply and args.expect_selection_sha256 is None:
            raise ValueError("--apply requires --expect-selection-sha256")
        if args.expect_selection_sha256 is not None and not args.apply:
            raise ValueError("--expect-selection-sha256 requires --apply")
        if args.apply:
            result = apply_delete(
                run_id=args.run, job_id=args.job,
                expected_selection_sha256=args.expect_selection_sha256, cwd=cwd,
            )
        else:
            result = preview_delete(run_id=args.run, job_id=args.job, cwd=cwd)
        return result if args.json else _render_delete_text(result)
    raise ValueError(f"unsupported workspace command: {args.workspace_command}")
