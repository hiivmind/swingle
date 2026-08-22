from pathlib import Path

from swingle.check import check_repository


def write_note(root: Path, body: str) -> Path:
    path = root / "providers" / "alpha" / "pack.md"
    path.parent.mkdir(parents=True)
    path.write_text(body)
    return path


def test_free_form_note_has_no_findings(tmp_path):
    write_note(tmp_path, """# Alpha provider notes

Whatever shape the author chooses: prose, one table, several tables under
different headings. Nothing here parses the content back out.
""")

    assert check_repository(tmp_path) == []


def test_missing_provider_note_is_a_finding(tmp_path):
    (tmp_path / "providers" / "alpha").mkdir(parents=True)

    findings = check_repository(tmp_path)

    assert any("missing provider note" in finding for finding in findings)


def test_provider_directory_rejects_certification_assets(tmp_path):
    write_note(tmp_path, "# Alpha provider notes\n")
    (tmp_path / "providers" / "alpha" / "models.yaml").write_text("models: []\n")

    findings = check_repository(tmp_path)

    assert any("unexpected provider asset" in finding for finding in findings)
