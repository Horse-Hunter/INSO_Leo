"""Production entry point: ``python -m src.gui.main``.

Use ``--mock`` only for GUI development and demonstrations.
"""

from __future__ import annotations

import argparse
import logging
import sys

from src.launcher import ProductionBackend

from .app import InsoDashboardApp
from .mock_backend import MockBackend


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    parser = argparse.ArgumentParser(description="INSO V1 production launcher")
    parser.add_argument(
        "--mock", action="store_true", help="run GUI demo backend instead of production"
    )
    args = parser.parse_args()
    backend = MockBackend(cycle_seconds=12.0) if args.mock else ProductionBackend()
    InsoDashboardApp(backend).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
