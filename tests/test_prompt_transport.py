from __future__ import annotations

import subprocess
import os
import re
import sys
from pathlib import Path

import pytest


FIXTURE = Path(__file__).parent / "fixtures" / "capture_provider.py"
CLI_FIXTURE = Path(__file__).parent / "fixtures" / "capture_cli.py"
PACK_ROOT = Path(__file__).resolve().parents[1] / "providers"
BRIEFINGS = (
    "plain read-only request\n",
    """```python
quoted = 'single' + \"double\"
blank = \"\"
```\n
""",
    """$HOME `backticks` $(command substitution) ; && | * ? < > [ ]
'quotes' \"quotes\" \\\ntrailing newline follows
""",
)


@pytest.mark.parametrize("mode", ("stdin", "prompt-file", "positional"))
@pytest.mark.parametrize("briefing", BRIEFINGS)
def test_transport_preserves_complete_authored_briefing(tmp_path, mode, briefing):
    expected = briefing.encode("utf-8")
    capture = tmp_path / "capture.bin"
    command = [
        sys.executable,
        str(FIXTURE),
        "--capture",
        str(capture),
        "--mode",
        mode,
    ]
    input_bytes = None
    if mode == "stdin":
        input_bytes = expected
    elif mode == "prompt-file":
        prompt_file = tmp_path / "briefing.txt"
        prompt_file.write_bytes(expected)
        command.extend(("--prompt-file", str(prompt_file)))
    else:
        command.append(briefing)

    subprocess.run(command, input=input_bytes, check=True)

    assert capture.read_bytes() == expected


def _dispatch_commands(provider: str) -> tuple[str, ...]:
    text = (PACK_ROOT / provider / "pack.md").read_text(encoding="utf-8")
    dispatch = text.split("## Dispatch guidance", 1)[1]
    return tuple(re.findall(r"```bash\n(.*?)\n```", dispatch, flags=re.DOTALL))


@pytest.mark.parametrize("provider", ("agy", "copilot", "cursor-agent", "opencode"))
@pytest.mark.parametrize("briefing", BRIEFINGS)
def test_shipped_provider_commands_preserve_complete_authored_briefing(
    tmp_path,
    provider,
    briefing,
):
    prompt = tmp_path / "briefing.txt"
    prompt.write_bytes(briefing.encode("utf-8"))
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / provider).symlink_to(CLI_FIXTURE)
    commands = _dispatch_commands(provider)
    assert commands

    for index, command in enumerate(commands):
        artifact = tmp_path / f"{provider}-{index}.bin"
        env = dict(
            os.environ,
            PATH=f"{fake_bin}:{os.environ['PATH']}",
            PROMPT=str(prompt),
            REPO_ROOT=str(tmp_path),
            MODEL="provider/model",
            EFFORT="low",
            ARTIFACT=str(artifact),
        )
        subprocess.run(["/bin/bash", "-c", command], check=True, env=env)
        assert artifact.read_bytes() == briefing.encode("utf-8")
