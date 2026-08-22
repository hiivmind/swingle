from swingle.providers import discover_provider_ids


def test_discover_provider_ids_lists_provider_subdirectories(tmp_path):
    providers = tmp_path / "providers"
    for name in ("codex", "grok"):
        (providers / name).mkdir(parents=True)
    (providers / "not-a-dir.txt").write_text("")

    assert discover_provider_ids(tmp_path) == {"codex", "grok"}


def test_discover_provider_ids_rejects_malformed_directory_names(tmp_path):
    providers = tmp_path / "providers"
    (providers / "codex").mkdir(parents=True)
    (providers / "Bad_Name").mkdir()

    assert discover_provider_ids(tmp_path) == {"codex"}
