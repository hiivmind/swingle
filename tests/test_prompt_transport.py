from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


FIXTURE = Path(__file__).parent / "fixtures" / "capture_provider.py"
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
