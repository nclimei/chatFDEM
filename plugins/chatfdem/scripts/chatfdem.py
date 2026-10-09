"""Run the chatFDEM CLI bundled with the installed plugin."""

from __future__ import annotations

import sys
from pathlib import Path


MINIMUM_PYTHON = (3, 11)


def main() -> int:
    if sys.version_info < MINIMUM_PYTHON:
        required = ".".join(str(part) for part in MINIMUM_PYTHON)
        current = ".".join(str(part) for part in sys.version_info[:3])
        raise SystemExit(f"chatFDEM requires Python {required}+; found {current}")

    sys.dont_write_bytecode = True
    plugin_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(plugin_root / "python"))
    from chatfdem.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
