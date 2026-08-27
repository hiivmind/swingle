from __future__ import annotations

import ctypes
import errno
import hashlib
import os
import platform
import stat
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .errors import WorkspaceError

_HASH_CHUNK_BYTES = 1 << 20  # 1 MiB
_READ_ONLY_NOFOLLOW = os.O_RDONLY | os.O_NOFOLLOW
_DIR_NOFOLLOW = os.O_DIRECTORY | os.O_NOFOLLOW | os.O_RDONLY
_NEW_FILE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL
PUBLICATION_RACE_LIMIT = 8


@dataclass(frozen=True)
class FileFact:
    path: str
    size_bytes: int
    sha256: str
    device: int
    inode: int


@dataclass(frozen=True)
class TreeFact:
    path: str
    entry_type: Literal["directory", "file"]
    size_bytes: int
    sha256: str | None


def _io_error(operation: str, path: str, exc: OSError) -> WorkspaceError:
    detail = f"{operation}: {path}"
    if exc.errno is not None:
        detail += f" (errno {exc.errno})"
    return WorkspaceError("workspace_io_error", detail)


def _validate_declared_path(path: str) -> tuple[str, ...]:
    """Validate a declared (manifest or expected-tree) relative path.

    Any syntax that could misrepresent or escape containment within the
    declared root is a `path_escape`: this is the single vocabulary the
    package uses for untrusted relative-path strings, whether they come
    from a parsed manifest or a copy/deletion selection.
    """
    if not isinstance(path, str) or not path:
        raise WorkspaceError("path_escape", f"declared path must be a non-empty string: {path!r}")
    if "\x00" in path or "\\" in path:
        raise WorkspaceError("path_escape", f"declared path contains an illegal character: {path!r}")
    if path.startswith("/"):
        raise WorkspaceError("path_escape", f"declared path must be relative: {path!r}")
    segments = tuple(path.split("/"))
    for segment in segments:
        if segment in ("", ".", ".."):
            raise WorkspaceError("path_escape", f"declared path escapes its root: {path!r}")
    try:
        path.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise WorkspaceError("path_escape", f"declared path is not serializable: {path!r}") from exc
    return segments


def _sortable_bytes(name: str, *, operation: str) -> bytes:
    try:
        encoded = name.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise WorkspaceError(
            "path_not_serializable", f"{operation}: discovered name is not valid UTF-8: {name!r}"
        ) from exc
    if "\\" in name:
        raise WorkspaceError(
            "path_not_serializable", f"{operation}: discovered name contains a backslash: {name!r}"
        )
    return encoded


def _open_dir_no_follow_path(root: Path, *, operation: str) -> int:
    try:
        return os.open(str(root), _DIR_NOFOLLOW)
    except FileNotFoundError as exc:
        raise WorkspaceError("workspace_io_error", f"{operation}: missing directory: {root}") from exc
    except NotADirectoryError as exc:
        raise WorkspaceError("special_file_rejected", f"{operation}: not a directory: {root}") from exc
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise WorkspaceError("symlink_rejected", f"{operation}: symbolic link rejected: {root}") from exc
        raise _io_error(operation, str(root), exc) from exc


def _open_dir_no_follow(dir_fd: int, name: str, *, operation: str, path: str) -> int:
    try:
        return os.open(name, _DIR_NOFOLLOW, dir_fd=dir_fd)
    except FileNotFoundError as exc:
        raise WorkspaceError("file_missing", f"{operation}: missing directory: {path}") from exc
    except NotADirectoryError as exc:
        raise WorkspaceError("special_file_rejected", f"{operation}: not a directory: {path}") from exc
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise WorkspaceError("symlink_rejected", f"{operation}: symbolic link rejected: {path}") from exc
        raise _io_error(operation, path, exc) from exc


def _open_file_no_follow(dir_fd: int, name: str, *, operation: str, path: str) -> int:
    try:
        return os.open(name, _READ_ONLY_NOFOLLOW, dir_fd=dir_fd)
    except FileNotFoundError as exc:
        raise WorkspaceError("file_missing", f"{operation}: missing file: {path}") from exc
    except IsADirectoryError as exc:
        raise WorkspaceError("special_file_rejected", f"{operation}: not a regular file: {path}") from exc
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise WorkspaceError("symlink_rejected", f"{operation}: symbolic link rejected: {path}") from exc
        raise _io_error(operation, path, exc) from exc


def _lstat(dir_fd: int, name: str, *, operation: str, path: str) -> os.stat_result:
    try:
        return os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise WorkspaceError("file_missing", f"{operation}: missing entry: {path}") from exc
    except OSError as exc:
        raise _io_error(operation, path, exc) from exc


def _hash_from_fd(fd: int, *, operation: str, path: str, sink_fd: int | None = None) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        while True:
            chunk = os.read(fd, _HASH_CHUNK_BYTES)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
            if sink_fd is not None:
                os.write(sink_fd, chunk)
    except OSError as exc:
        raise _io_error(operation, path, exc) from exc
    return size, digest.hexdigest()


def _read_stable_regular_file(
    dir_fd: int, name: str, path: str, *, operation: str, sink_fd: int | None = None
) -> tuple[int, str, int, int]:
    """Read a regular file and confirm its identity never moved under us.

    Returns (size_bytes, sha256, device, inode). Raises the exact
    `WorkspaceError` for a disappeared, retyped, or replaced entry. When
    `sink_fd` is given, every read chunk is also written there, so a
    caller can copy and verify a file in one read pass.
    """
    fd = _open_file_no_follow(dir_fd, name, operation=operation, path=path)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise WorkspaceError("special_file_rejected", f"{operation}: not a regular file: {path}")
        size_bytes, sha256 = _hash_from_fd(fd, operation=operation, path=path, sink_fd=sink_fd)
        after = os.fstat(fd)
    finally:
        os.close(fd)

    current = _lstat(dir_fd, name, operation=operation, path=path)
    if stat.S_ISLNK(current.st_mode):
        raise WorkspaceError("symlink_rejected", f"{operation}: symbolic link rejected: {path}")
    if not stat.S_ISREG(current.st_mode):
        raise WorkspaceError("special_file_rejected", f"{operation}: not a regular file: {path}")
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_mode != after.st_mode
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
    ):
        raise WorkspaceError("file_identity_changed", f"{operation}: file changed during read: {path}")
    if current.st_dev != after.st_dev or current.st_ino != after.st_ino:
        raise WorkspaceError("file_identity_changed", f"{operation}: file replaced during read: {path}")

    return size_bytes, sha256, after.st_dev, after.st_ino


def _listdir_sorted(dir_fd: int, *, operation: str) -> list[str]:
    try:
        names = os.listdir(dir_fd)
    except OSError as exc:
        raise _io_error(operation, "<directory>", exc) from exc
    return sorted(names, key=lambda name: _sortable_bytes(name, operation=operation))


def _scan_directory(
    dir_fd: int,
    prefix: tuple[str, ...],
    facts: list[FileFact],
    excluded: frozenset[str],
    *,
    operation: str,
) -> None:
    for name in _listdir_sorted(dir_fd, operation=operation):
        path = "/".join((*prefix, name))
        entry_stat = _lstat(dir_fd, name, operation=operation, path=path)
        if stat.S_ISLNK(entry_stat.st_mode):
            raise WorkspaceError("symlink_rejected", f"{operation}: symbolic link rejected: {path}")
        if stat.S_ISDIR(entry_stat.st_mode):
            sub_fd = _open_dir_no_follow(dir_fd, name, operation=operation, path=path)
            try:
                _scan_directory(sub_fd, (*prefix, name), facts, excluded, operation=operation)
            finally:
                os.close(sub_fd)
            continue
        if not stat.S_ISREG(entry_stat.st_mode):
            raise WorkspaceError("special_file_rejected", f"{operation}: not a regular file or directory: {path}")
        if path in excluded:
            continue
        size_bytes, sha256, device, inode = _read_stable_regular_file(dir_fd, name, path, operation=operation)
        facts.append(FileFact(path=path, size_bytes=size_bytes, sha256=sha256, device=device, inode=inode))


def scan_regular_tree(
    root: Path,
    *,
    exclude_paths: Collection[str] = (),
) -> tuple[FileFact, ...]:
    """Discover every regular file below `root`, excluding `exclude_paths`.

    Rejects a symbolic link or special file anywhere in the tree. Returns
    facts sorted in unsigned UTF-8 byte order by path.
    """
    excluded = frozenset(exclude_paths)
    root_fd = _open_dir_no_follow_path(Path(root), operation="scan")
    try:
        facts: list[FileFact] = []
        _scan_directory(root_fd, (), facts, excluded, operation="scan")
    finally:
        os.close(root_fd)
    facts.sort(key=lambda fact: fact.path.encode("utf-8"))
    return tuple(facts)


def _verify_directory(
    dir_fd: int,
    prefix: tuple[str, ...],
    expected_by_path: dict[str, TreeFact],
    visited: dict[str, TreeFact],
    *,
    reject_unlisted_files: bool,
    reject_unlisted_directories: bool,
    operation: str,
) -> None:
    for name in _listdir_sorted(dir_fd, operation=operation):
        path = "/".join((*prefix, name))
        entry_stat = _lstat(dir_fd, name, operation=operation, path=path)
        expected_fact = expected_by_path.get(path)

        if stat.S_ISLNK(entry_stat.st_mode):
            raise WorkspaceError("symlink_rejected", f"{operation}: symbolic link rejected: {path}")

        if stat.S_ISDIR(entry_stat.st_mode):
            if expected_fact is not None and expected_fact.entry_type != "directory":
                raise WorkspaceError("file_identity_changed", f"{operation}: expected file, found directory: {path}")
            if expected_fact is None and reject_unlisted_directories:
                raise WorkspaceError("file_unlisted", f"{operation}: unlisted directory: {path}")
            visited[path] = TreeFact(path=path, entry_type="directory", size_bytes=0, sha256=None)
            sub_fd = _open_dir_no_follow(dir_fd, name, operation=operation, path=path)
            try:
                _verify_directory(
                    sub_fd,
                    (*prefix, name),
                    expected_by_path,
                    visited,
                    reject_unlisted_files=reject_unlisted_files,
                    reject_unlisted_directories=reject_unlisted_directories,
                    operation=operation,
                )
            finally:
                os.close(sub_fd)
            continue

        if not stat.S_ISREG(entry_stat.st_mode):
            raise WorkspaceError("special_file_rejected", f"{operation}: not a regular file or directory: {path}")

        if expected_fact is not None and expected_fact.entry_type != "file":
            raise WorkspaceError("file_identity_changed", f"{operation}: expected directory, found file: {path}")
        if expected_fact is None and reject_unlisted_files:
            raise WorkspaceError("file_unlisted", f"{operation}: unlisted file: {path}")

        size_bytes, sha256, _device, _inode = _read_stable_regular_file(dir_fd, name, path, operation=operation)
        if expected_fact is not None and (
            size_bytes != expected_fact.size_bytes or sha256 != expected_fact.sha256
        ):
            raise WorkspaceError("hash_mismatch", f"{operation}: content mismatch: {path}")
        visited[path] = TreeFact(path=path, entry_type="file", size_bytes=size_bytes, sha256=sha256)


def verify_regular_tree_at(
    root_fd: int,
    expected: Sequence[TreeFact],
    *,
    reject_unlisted_files: bool = True,
    reject_unlisted_directories: bool = False,
) -> tuple[TreeFact, ...]:
    """Verify `root_fd` against `expected`, raising the exact failure.

    Indexes `expected` by path, walks the open directory, and applies both
    rejection flags. Returns every visited entry in unsigned UTF-8 order.
    """
    expected_by_path: dict[str, TreeFact] = {}
    for item in expected:
        _validate_declared_path(item.path)
        expected_by_path[item.path] = item

    visited: dict[str, TreeFact] = {}
    _verify_directory(
        root_fd,
        (),
        expected_by_path,
        visited,
        reject_unlisted_files=reject_unlisted_files,
        reject_unlisted_directories=reject_unlisted_directories,
        operation="verify",
    )

    missing = [path for path in expected_by_path if path not in visited]
    if missing:
        missing.sort(key=lambda path: path.encode("utf-8"))
        raise WorkspaceError("file_missing", f"verify: missing entry: {missing[0]}")

    return tuple(sorted(visited.values(), key=lambda fact: fact.path.encode("utf-8")))


def verify_regular_tree(
    root: Path,
    expected: Sequence[TreeFact],
    *,
    reject_unlisted_files: bool = True,
    reject_unlisted_directories: bool = False,
) -> tuple[TreeFact, ...]:
    """Open `root` once and delegate to `verify_regular_tree_at`."""
    root_fd = _open_dir_no_follow_path(Path(root), operation="verify")
    try:
        return verify_regular_tree_at(
            root_fd,
            expected,
            reject_unlisted_files=reject_unlisted_files,
            reject_unlisted_directories=reject_unlisted_directories,
        )
    finally:
        os.close(root_fd)


def read_file_fact(root: Path, relative_path: str) -> FileFact:
    """Open, hash, and confirm one regular file's stable identity.

    Walks `relative_path` relative to `root` through descriptor-relative,
    no-follow opens at every component, then reads a stable `FileFact`
    (including device and inode) from the final open descriptor. Used to
    capture a fresh, TOCTOU-safe identity for one selected file at the
    moment of selection, distinct from an earlier tree-verification pass.
    """
    segments = _validate_declared_path(relative_path)
    root_fd = _open_dir_no_follow_path(Path(root), operation="select")
    try:
        fd = root_fd
        opened: list[int] = []
        try:
            for segment in segments[:-1]:
                fd = _open_dir_no_follow(fd, segment, operation="select", path=relative_path)
                opened.append(fd)
            size_bytes, sha256, device, inode = _read_stable_regular_file(
                fd, segments[-1], relative_path, operation="select"
            )
        finally:
            for handle in reversed(opened):
                os.close(handle)
    finally:
        os.close(root_fd)
    return FileFact(path=relative_path, size_bytes=size_bytes, sha256=sha256, device=device, inode=inode)


def ensure_directory_at(root_fd: int, relative_path: str) -> None:
    """Create every missing directory component of `relative_path`.

    Relative to `root_fd`, without following symbolic links anywhere.
    Idempotent: an already-existing directory component is left alone.
    """
    segments = _validate_declared_path(relative_path)
    fd = root_fd
    opened: list[int] = []
    try:
        for segment in segments:
            try:
                os.mkdir(segment, 0o700, dir_fd=fd)
            except FileExistsError:
                pass
            except OSError as exc:
                raise _io_error("stage", relative_path, exc) from exc
            next_fd = _open_dir_no_follow(fd, segment, operation="stage", path=relative_path)
            opened.append(next_fd)
            fd = next_fd
    finally:
        for handle in reversed(opened):
            os.close(handle)


def write_new_file_at(root_fd: int, relative_path: str, content: bytes) -> None:
    """Write `content` to a freshly created file at `relative_path`.

    Relative to `root_fd`. Creates any missing parent directory. The
    file itself must not already exist. Flushes the file and its parent
    directory before returning.
    """
    segments = _validate_declared_path(relative_path)
    if len(segments) > 1:
        ensure_directory_at(root_fd, "/".join(segments[:-1]))
    fd = root_fd
    opened: list[int] = []
    try:
        for segment in segments[:-1]:
            fd = _open_dir_no_follow(fd, segment, operation="stage", path=relative_path)
            opened.append(fd)
        try:
            file_fd = os.open(segments[-1], _NEW_FILE_FLAGS, 0o600, dir_fd=fd)
        except OSError as exc:
            raise _io_error("stage", relative_path, exc) from exc
        try:
            os.write(file_fd, content)
            os.fsync(file_fd)
        finally:
            os.close(file_fd)
        os.fsync(fd)
    finally:
        for handle in reversed(opened):
            os.close(handle)


def copy_regular_file_at(
    *,
    source_root_fd: int,
    source_path: str,
    destination_root_fd: int,
    destination_path: str,
    expected_size: int,
    expected_sha256: str,
) -> FileFact:
    """Copy one regular file, verifying its size and digest as it streams.

    Reads `source_path` (relative to `source_root_fd`) exactly once,
    simultaneously writing every byte to a freshly created
    `destination_path` (relative to `destination_root_fd`) and confirming
    the source never moved during the read. Destination parent
    directories must already exist; the destination name must not.
    """
    source_segments = _validate_declared_path(source_path)
    destination_segments = _validate_declared_path(destination_path)

    source_dir_fd = source_root_fd
    opened_source: list[int] = []
    destination_dir_fd = destination_root_fd
    opened_destination: list[int] = []
    try:
        for segment in source_segments[:-1]:
            source_dir_fd = _open_dir_no_follow(source_dir_fd, segment, operation="copy", path=source_path)
            opened_source.append(source_dir_fd)
        for segment in destination_segments[:-1]:
            destination_dir_fd = _open_dir_no_follow(
                destination_dir_fd, segment, operation="copy", path=destination_path
            )
            opened_destination.append(destination_dir_fd)

        try:
            write_fd = os.open(destination_segments[-1], _NEW_FILE_FLAGS, 0o600, dir_fd=destination_dir_fd)
        except OSError as exc:
            raise _io_error("copy", destination_path, exc) from exc

        try:
            size_bytes, sha256, device, inode = _read_stable_regular_file(
                source_dir_fd, source_segments[-1], source_path, operation="copy", sink_fd=write_fd
            )
            if size_bytes != expected_size or sha256 != expected_sha256:
                raise WorkspaceError("hash_mismatch", f"copy: source changed before copy: {source_path}")
            os.fsync(write_fd)
        except BaseException:
            os.close(write_fd)
            try:
                os.unlink(destination_segments[-1], dir_fd=destination_dir_fd)
            except OSError:
                pass
            raise
        else:
            os.close(write_fd)
        os.fsync(destination_dir_fd)
    finally:
        for handle in reversed(opened_destination):
            os.close(handle)
        for handle in reversed(opened_source):
            os.close(handle)

    return FileFact(path=destination_path, size_bytes=size_bytes, sha256=sha256, device=device, inode=inode)


def regular_tree_matches_at(root_fd: int, expected: Sequence[TreeFact]) -> bool:
    """Compare `root_fd`'s complete tree against `expected`.

    Returns `False` for a missing, extra, mistyped, resized, or changed
    entry. Raises safety and I/O errors instead of treating them as
    inequality.
    """
    try:
        verify_regular_tree_at(
            root_fd, expected, reject_unlisted_files=True, reject_unlisted_directories=True
        )
    except WorkspaceError as exc:
        if exc.code in ("file_missing", "file_unlisted", "hash_mismatch", "file_identity_changed"):
            return False
        raise
    return True


def delete_tree_at(parent_fd: int, name: str) -> None:
    """Recursively delete the directory tree at `name`.

    Relative to `parent_fd`, without following symbolic links anywhere
    in the tree. A missing entry is a no-op.
    """
    try:
        entry_stat = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise _io_error("delete", name, exc) from exc
    if stat.S_ISLNK(entry_stat.st_mode):
        raise WorkspaceError("symlink_rejected", f"delete: symbolic link rejected: {name}")
    if stat.S_ISDIR(entry_stat.st_mode):
        dir_fd = _open_dir_no_follow(parent_fd, name, operation="delete", path=name)
        try:
            for child in _listdir_sorted(dir_fd, operation="delete"):
                delete_tree_at(dir_fd, child)
        finally:
            os.close(dir_fd)
        try:
            os.rmdir(name, dir_fd=parent_fd)
        except OSError as exc:
            raise _io_error("delete", name, exc) from exc
    else:
        try:
            os.unlink(name, dir_fd=parent_fd)
        except OSError as exc:
            raise _io_error("delete", name, exc) from exc


def _renameat_config() -> tuple[str, int] | None:
    system = platform.system()
    if system == "Darwin":
        return "renameatx_np", 0x00000004  # RENAME_EXCL
    if system == "Linux":
        return "renameat2", 0x00000001  # RENAME_NOREPLACE
    return None


def _renameat_func():
    config = _renameat_config()
    if config is None:
        return None, 0
    name, flag = config
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        func = getattr(libc, name)
    except AttributeError:
        return None, 0
    func.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    func.restype = ctypes.c_int
    return func, flag


def rename_directory_noreplace_at(parent_fd: int, source_name: str, destination_name: str) -> bool:
    """Publish `source_name` as `destination_name` with an exclusive rename.

    Both names are relative to `parent_fd`. Returns `True` only when it
    publishes the stage. Returns `False` only for `EEXIST`. Raises
    `workspace_io_error` if the platform or filesystem lacks exclusive
    no-replace rename support; never falls back to an overwrite-capable
    rename.
    """
    func, flag = _renameat_func()
    if func is None:
        raise WorkspaceError(
            "workspace_io_error", "copy: exclusive no-replace rename is unavailable on this platform"
        )
    ctypes.set_errno(0)
    result = func(
        parent_fd, os.fsencode(source_name), parent_fd, os.fsencode(destination_name), flag
    )
    if result == 0:
        return True
    err = ctypes.get_errno()
    if err == errno.EEXIST:
        return False
    unsupported = {errno.EINVAL, errno.ENOSYS, getattr(errno, "EOPNOTSUPP", errno.EINVAL), errno.ENOTTY}
    if err in unsupported:
        raise WorkspaceError(
            "workspace_io_error", "copy: exclusive no-replace rename is unsupported by this filesystem"
        )
    raise WorkspaceError("workspace_io_error", f"copy: rename failed (errno {err})")


def open_verified_parent_at(destination_path: str) -> tuple[int, str, tuple[str, ...]]:
    """Verify and open every parent directory of `destination_path`.

    `destination_path` must already be an absolute, lexically normalized
    path. Opens (creating as needed) each parent component from the
    filesystem root down, without ever following a symbolic link, and
    rejects a non-directory component. Returns the open parent
    descriptor, the destination's final path component, and every
    directory this call created (oldest first), for rollback if
    publication ultimately fails.
    """
    parent_path, destination_name = os.path.split(destination_path)
    if not destination_name:
        raise WorkspaceError("path_escape", f"copy: destination has no final component: {destination_path}")
    components = [component for component in parent_path.split(os.sep) if component]

    fd = os.open("/", _DIR_NOFOLLOW)
    created: list[str] = []
    walked = "/"
    try:
        for component in components:
            walked = os.path.join(walked, component)
            try:
                entry_stat = os.stat(component, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                try:
                    os.mkdir(component, 0o700, dir_fd=fd)
                    created.append(walked)
                except FileExistsError:
                    pass
                except OSError as exc:
                    raise _io_error("copy", walked, exc) from exc
                entry_stat = os.stat(component, dir_fd=fd, follow_symlinks=False)
            except OSError as exc:
                raise _io_error("copy", walked, exc) from exc
            if stat.S_ISLNK(entry_stat.st_mode):
                raise WorkspaceError("symlink_rejected", f"copy: symbolic link in destination path: {walked}")
            if not stat.S_ISDIR(entry_stat.st_mode):
                raise WorkspaceError("copy_conflict", f"copy: not a directory: {walked}")
            next_fd = _open_dir_no_follow(fd, component, operation="copy", path=walked)
            os.close(fd)
            fd = next_fd
    except BaseException:
        os.close(fd)
        raise
    return fd, destination_name, tuple(created)
