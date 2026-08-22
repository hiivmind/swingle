from __future__ import annotations

from pathlib import Path
import re

PROVIDER_ID_RE = re.compile(r"^[a-z0-9-]+$")


def discover_provider_ids(root: Path) -> set[str]:
    return {
        path.name
        for path in (root / "providers").iterdir()
        if path.is_dir() and PROVIDER_ID_RE.fullmatch(path.name)
    }
