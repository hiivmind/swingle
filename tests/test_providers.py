from pathlib import Path

from swingle.check import check_repository
from swingle.providers import load_provider_note


def write_note(root: Path, body: str) -> Path:
    path = root / "providers" / "alpha" / "pack.md"
    path.parent.mkdir(parents=True)
    path.write_text(body)
    return path


def test_parse_provider_note(tmp_path):
    path = write_note(tmp_path, """# Alpha gotchas

CLI: `alpha`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| exits 0 with no file | requested write is missing | inspect current permission help and retry | issue #1 |
""")

    note = load_provider_note(path)

    assert note.provider_id == "alpha"
    assert note.cli == "alpha"
    assert note.gotchas[0].signature == "exits 0 with no file"


def test_empty_gotcha_table_is_valid(tmp_path):
    write_note(tmp_path, """# Alpha gotchas

CLI: `alpha`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
""")

    assert check_repository(tmp_path) == []


def test_note_rejects_wrong_columns(tmp_path):
    write_note(tmp_path, """# Alpha gotchas

CLI: `alpha`

| Command | Models |
| --- | --- |
""")

    findings = check_repository(tmp_path)

    assert any("gotcha-table columns" in finding for finding in findings)


def test_note_rejects_missing_evidence(tmp_path):
    write_note(tmp_path, """# Alpha gotchas

CLI: `alpha`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| silent success | requested file is missing | inspect current help and retry | |
""")

    findings = check_repository(tmp_path)

    assert any("invalid gotcha row" in finding for finding in findings)


def test_provider_directory_rejects_certification_assets(tmp_path):
    write_note(tmp_path, """# Alpha gotchas

CLI: `alpha`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
""")
    (tmp_path / "providers" / "alpha" / "models.yaml").write_text("models: []\n")

    findings = check_repository(tmp_path)

    assert any("unexpected provider asset" in finding for finding in findings)
