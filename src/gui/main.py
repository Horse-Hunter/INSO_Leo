"""Entry point: `python -m src.gui.main`."""

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
    backend = MockBackend(cycle_seconds=12.0)
    app = InsoDashboardApp(backend)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
