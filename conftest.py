"""Put the vendored swingle package on sys.path for direct-import tests.

Subprocess tests invoke scripts/* which bootstrap lib/ themselves; this is only for
in-process `import swingle.*` tests. Absolute resolved path at index 0 so an installed
third-party `swingle` cannot shadow the vendored one during tests.
"""

import sys
from pathlib import Path

sys.path.insert(0, str((Path(__file__).resolve().parent / "lib")))
