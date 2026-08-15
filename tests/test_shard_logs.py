import pytest

import swingle.audit.logs as sl


def test_parse_and_render_preserve_payloads_and_report_provider_preamble():
    data = (
        b"# boilerplate\n\nProvider-specific instruction.\n\n---\n\n"
        b"## 2026-08-02 -- second\nbody two\n\n### addendum\nkept\n---\ninside payload\n\n---\n\n"
        b"## 2026-07-01 -- first\nfirst body\n\n---\n\n"
        b"## 2026-08-02 -- third\nthird body\n"
    )
    preamble, entries = sl.parse_log(data)
    assert b"Provider-specific instruction." in preamble
    assert [entry.date for entry in entries] == [
        "2026-08-02",
        "2026-07-01",
        "2026-08-02",
    ]
    assert b"### addendum\nkept\n---\ninside payload" in entries[0].payload
    assert not entries[0].payload.endswith(b"\n\n---\n\n")
    grouped = {}
    for entry in sorted(entries, key=lambda item: (item.date, item.ordinal)):
        grouped.setdefault(entry.date[:7], []).append(entry)
    july = sl.render_shard("test", "2026-07", grouped["2026-07"])
    august = sl.render_shard("test", "2026-08", grouped["2026-08"])
    _, july_entries = sl.parse_log(july)
    _, august_entries = sl.parse_log(august)
    assert july_entries[0].payload == entries[1].payload
    assert [entry.payload for entry in august_entries] == [
        entries[0].payload,
        entries[2].payload,
    ]
    assert b"../../../core/verification-protocol.md" in july


def test_grok_provider_preamble_is_relocated_not_dropped(tmp_path):
    for provider in sl.PROVIDERS:
        directory = tmp_path / "providers" / provider
        directory.mkdir(parents=True)
        preamble = (
            f"# SDD Dispatch Verification Log — {provider}\n\n"
            "Append-only. Never rewrite prior entries — a later contradiction dates a behavior change.\n\n"
            "Format per [verification-protocol.md](../../../core/verification-protocol.md).\n\n"
        ).encode()
        if provider == "grok":
            preamble += sl.REVERIFY + b"\n"
            version = directory / "versions" / "0.2.117.md"
            version.parent.mkdir()
            version.write_text("# current registry\n")
        (directory / "verification-log.md").write_bytes(
            preamble + b"---\n\n## 2026-07-01 -- entry\npayload\n"
        )
    old, new, relocation, mappings = sl.migrate_provider(tmp_path, "grok", write=True)
    assert len(old) == len(new) == 1
    assert mappings[0].old.ordinal == mappings[0].new.ordinal == 0
    mapped_report = sl.report_provider("grok", old, new, relocation, mappings)
    assert "source ordinal=0 heading='## 2026-07-01 -- entry'" in mapped_report
    assert (
        "-> log/2026-07.md ordinal=0 heading='## 2026-07-01 -- entry'" in mapped_report
    )
    assert relocation and "Primary docs for re-verify" in relocation
    assert sl.REVERIFY in (tmp_path / "providers/grok/versions/0.2.117.md").read_bytes()
    assert (
        tmp_path / "providers/grok/verification-log.md"
    ).read_text() == sl.index_text("grok")


def test_original_claude_preamble_is_known_boilerplate():
    """Fixture copied from 7ac6c8e:providers/claude/verification-log.md."""
    preamble = (
        "# SDD Dispatch Verification Log — claude\n\n"
        "Append-only. Never rewrite prior entries — a later contradiction dates a behavior change.\n"
        "Format per [verification-protocol.md](../../core/verification-protocol.md).\n\n"
        "---\n\n"
    ).encode()
    assert sl.unexpected_preamble_paragraphs("claude", preamble) == []
    generic = preamble.replace(" — claude".encode(), b"").replace(
        b"../../", b"../../../"
    )
    assert sl.unexpected_preamble_paragraphs("claude", generic) == []


def test_unexpected_provider_preamble_is_reported_for_relocation(tmp_path):
    directory = tmp_path / "providers" / "alpha"
    directory.mkdir(parents=True)
    directory.joinpath("verification-log.md").write_text(
        "# SDD Dispatch Verification Log — alpha\n\n"
        "Provider-specific operational restriction.\n\n---\n\n"
        "## 2026-07-01 -- entry\npayload\n"
    )
    with pytest.raises(ValueError, match="preamble requires relocation"):
        sl.migrate_provider(tmp_path, "alpha", write=False)


def test_pairwise_mapping_rejects_a_same_day_payload_swap():
    first = sl.Entry("2026-07-01", 0, b"## 2026-07-01 -- first\nfirst\n")
    second = sl.Entry("2026-07-01", 1, b"## 2026-07-01 -- second\nsecond\n")
    with pytest.raises(ValueError, match="source entry 0"):
        sl.map_entries("test", [first, second], {"2026-07": [second, first]})
