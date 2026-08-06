"""Repository/pack-tree self-validation (the default-mode trust gate).

`check_repo_docs` is the single orchestration façade: it runs its sections in the exact
legacy order — version-sync, per-pack structural, hygiene, purity, one global
path-sorted link scan — moved verbatim from the former scripts/validate-packs. The
runtime/authoring distinction is documentary (see the design spec); execution is NOT
re-sequenced and the single link traversal is never split.
"""
import datetime
import json
import re

from ..report import find
from ..packs import (
    registry_path_for, version_key, version_cmp_key,
    VERSION_FILE_RE, VER_RE, HEADER_RE, SHARD_FILE_RE, ENTRY_DATE_RE,
)


def check_repo_docs(root, manifests):
    plugin, readme = root / ".claude-plugin" / "plugin.json", root / "README.md"
    codex_plugin = root / ".codex-plugin" / "plugin.json"
    plugin_version = json.loads(plugin.read_text()).get("version") if plugin.exists() else None
    codex_version = json.loads(codex_plugin.read_text()).get("version") if codex_plugin.exists() else None
    match = re.search(r"\*\*Version:\*\*\s*([0-9.]+)", readme.read_text()) if readme.exists() else None
    if plugin_version and match and plugin_version != match.group(1): find(f"version mismatch: plugin.json {plugin_version} != README {match.group(1)}")
    if plugin_version and codex_version and plugin_version != codex_version: find(f"version mismatch: .claude-plugin {plugin_version} != .codex-plugin {codex_version}")
    for pack in sorted((root / "providers").glob("*/")) if (root / "providers").exists() else []:
        manifest, pack_path = manifests[pack.name], pack / "pack.md"
        pack_lines = pack_path.read_text().splitlines()
        closing = next((i for i, line in enumerate(pack_lines[1:], 1) if line == "---"), None)
        if closing is not None and any(line.strip() for line in pack_lines[closing + 1:]):
            find(f"{pack_path}: pack.md must be manifest-only")

        verified_version = manifest.get("verified-version")
        current = registry_path_for(pack, verified_version)
        if current is not None and not current.exists():
            find(f"{current}: current registry file missing")
        vdir = pack / "versions"
        if vdir.is_dir():
            for entry in sorted(vdir.iterdir()):
                if not VERSION_FILE_RE.fullmatch(entry.name):
                    find(f"{entry}: versions/ entries must be <dotted-numeric-version>.md")
                    continue
                if not entry.is_file() or entry.is_symlink():
                    find(f"{entry}: registry file must be a regular file")
                    continue
                if isinstance(verified_version, str) and VER_RE.fullmatch(verified_version):
                    width = max(len(version_key(entry.stem)), len(version_key(verified_version)))
                    if version_cmp_key(entry.stem, width) > version_cmp_key(verified_version, width):
                        find(f"{entry}: registry key must not exceed manifest verified-version {verified_version}")
                try:
                    lines = entry.read_text().splitlines()
                except (OSError, UnicodeError):
                    lines = []
                first = lines[0] if lines else ""
                header = HEADER_RE.fullmatch(first)
                if not header:
                    find(f"{entry}: registry file must open with a class header")
                    continue
                header_version = header.group("vver") or header.group("dver")
                if header_version != entry.stem:
                    find(f"{entry}: header version must equal filename")
                if current == entry and (header.group("vcli") != manifest.get("cli") or header.group("vver") != verified_version):
                    find(f"{entry}: current registry file must carry a Verified header naming the manifest cli and version")
        log_dir = pack / "log"
        if log_dir.is_symlink():
            find(f"{log_dir}: log/ must not be a symlink")
            entries = []
        else:
            entries = sorted(log_dir.iterdir()) if log_dir.is_dir() else []
        shards = []
        for e in entries:
            if e.is_file() and not e.is_symlink() and SHARD_FILE_RE.fullmatch(e.name): shards.append(e)
            else: find(f"{e}: log/ entries must be YYYY-MM.md regular files")
        if not shards:
            find(f"{pack}: log/ must exist with at least one YYYY-MM.md shard")
        for shard in shards:
            month, prev = shard.stem, None
            for n, line in enumerate(shard.read_text().splitlines(), 1):
                if not line.startswith("## "): continue
                m = ENTRY_DATE_RE.match(line)
                if not m:
                    find(f"{shard}:{n}: shard entry heading must open with its date (## YYYY-MM-DD …)"); continue
                d = m.group(1)
                try: datetime.date.fromisoformat(d)
                except ValueError: find(f"{shard}:{n}: {d} is not a real calendar date"); continue
                if not d.startswith(month): find(f"{shard}:{n}: entry date {d} outside the shard's month")
                if prev and d < prev: find(f"{shard}:{n}: shard entries must be nondecreasing by date ({d} after {prev})")
                prev = d
    hygiene = [("~~", "strikethrough"), ("(from archive", "provenance stamp")]
    ver_claim = re.compile(r"verified v[0-9]")
    for pack in sorted((root / "providers").glob("*/")) if (root / "providers").exists() else []:
        targets = []
        if (pack / "pack.md").exists():
            text = (pack / "pack.md").read_text().splitlines()
            end = next((i for i, l in enumerate(text[1:], 1) if l == "---"), 0)
            targets.append((pack / "pack.md", text[end + 1:], end + 2))
        if (pack / "models.md").exists():
            targets.append((pack / "models.md", (pack / "models.md").read_text().splitlines(), 1))
        vdir = pack / "versions"
        if vdir.is_dir():
            for path in sorted(vdir.glob("*.md")):
                if not path.is_file() or path.is_symlink():
                    continue
                try:
                    targets.append((path, path.read_text().splitlines()[1:], 2))
                except (OSError, UnicodeError):
                    continue
        for path, lines, start in targets:
            for n, line in enumerate(lines, start):
                for needle, label in hygiene:
                    if needle in line: find(f"{path}:{n}: pack-hygiene: {label}: {line.strip()[:60]}")
                if ver_claim.search(line): find(f"{path}:{n}: pack-hygiene: body version claim: {line.strip()[:60]}")
    banned = re.compile(r"gpt-5\.6|gemini-3|opencode-go/|deepseek|minimax|qwen|glm-5|Agent tool|TodoWrite|CLAUDE_PLUGIN_ROOT|spawn_agent")
    for directory in ("core", "contracts"):
        for path in sorted((root / directory).glob("*.md")) if (root / directory).exists() else []:
            for n, line in enumerate(path.read_text().splitlines(), 1):
                if banned.search(line) and "routing" not in line and "precedence" not in line: find(f"{path}:{n}: purity violation: {line.strip()[:70]}")
    link_re = re.compile(r"\]\(([^)]+)\)")
    def heading_slugs(text):
        slugs = set()
        for line in text.splitlines():
            m = re.match(r"#{1,6}\s+(.*)", line)
            if m: slugs.add(re.sub(r"[^\w\s-]", "", m.group(1).strip().lower()).replace(" ", "-"))
        return slugs
    slug_cache = {}
    def slugs_for(p):
        if p not in slug_cache: slug_cache[p] = heading_slugs(p.read_text()) if p.exists() else None
        return slug_cache[p]
    def scanned(p):
        # Git-ignored agent scratch (sdd/delegate workspaces) and archive snapshots are
        # agent-authored or historical artifacts full of illustrative links — never repo content.
        rel = str(p.relative_to(root))
        return not ("archive/" in rel or re.match(r"providers/[^/]+/versions/", rel)
                    or ".git" in p.parts or ".superpowers" in p.parts
                    or ".swingle" in p.parts or ".sdd-dispatch" in p.parts)
    for path in sorted(root.rglob("*.md")):
        if not scanned(path): continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            for target in link_re.findall(line):
                if target.startswith(("http://", "https://", "/", "mailto:")): continue
                pathpart, _, anchor = target.partition("#")
                dest = path if pathpart == "" else (path.parent / pathpart)
                if pathpart and not dest.exists(): find(f"{path}:{n}: broken link {target}"); continue
                # Anchor check: the fragment must resolve to a heading in the target md file.
                if anchor and dest.suffix == ".md" and scanned(dest):
                    known = slugs_for(dest)
                    if known is not None and anchor not in known: find(f"{path}:{n}: broken anchor #{anchor} → {pathpart or path.name}")
