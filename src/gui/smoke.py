"""Manual smoke script: build the GUI, let it render for 2 s, then close.

Run with a display:

    python -m src.gui.smoke
"""

from __future__ import annotations

import logging
import sys

from .app import InsoDashboardApp
from .mock_backend import MockBackend


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    backend = MockBackend(cycle_seconds=60.0)
    app = InsoDashboardApp(backend)

    # Render briefly then close so the developer can confirm the window opens.
    app._root.after(2000, app._on_close)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
