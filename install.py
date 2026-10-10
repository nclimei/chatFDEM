"""Install the local chatFDEM Codex plugin in one command."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, NoReturn


REPO_ROOT = Path(__file__).resolve().parent
MARKETPLACE_FILE = REPO_ROOT / ".codex-plugin" / "marketplace.json"
MINIMUM_PYTHON = (3, 11)


def fail(message: str) -> NoReturn:
    raise SystemExit(f"chatFDEM installer: {message}")


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), flush=True)
    return subprocess.run(
        command,
        check=True,
        text=True,
        capture_output=capture,
    )


def load_marketplace() -> tuple[str, str]:
    try:
        payload: dict[str, Any] = json.loads(MARKETPLACE_FILE.read_text(encoding="utf-8"))
        marketplace = str(payload["name"])
        plugin = str(payload["plugins"][0]["name"])
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        fail(f"cannot read {MARKETPLACE_FILE}: {exc}")
    return marketplace, plugin


def configured_marketplaces(codex: str) -> dict[str, Path]:
    result = run([codex, "plugin", "marketplace", "list", "--json"], capture=True)
    try:
        payload = json.loads(result.stdout)
        return {
            str(item["name"]): Path(item["root"]).resolve()
            for item in payload.get("marketplaces", [])
        }
    except (ValueError, KeyError, TypeError) as exc:
        fail(f"cannot parse Codex marketplace list: {exc}")


def find_runtime_python() -> str:
    candidates = [
        sys.executable,
        *(shutil.which(name) for name in ("python3.13", "python3.12", "python3.11", "python")),
    ]
    seen: set[str] = set()
    for candidate in candidates:
        if candidate is None or candidate in seen:
            continue
        seen.add(candidate)
        result = subprocess.run(
            [candidate, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            continue
        major, minor = (int(part) for part in result.stdout.strip().split(".", 1))
        if (major, minor) >= MINIMUM_PYTHON:
            return candidate
    fail("Python 3.11 or newer is required but was not found")


def main() -> int:
    codex = shutil.which("codex")
    if codex is None:
        fail("the `codex` command is not available on PATH")
    runtime_python = find_runtime_python()

    marketplace, plugin = load_marketplace()
    configured = configured_marketplaces(codex)
    configured_root = configured.get(marketplace)
    if configured_root is None:
        run([codex, "plugin", "marketplace", "add", str(REPO_ROOT)])
    elif configured_root != REPO_ROOT:
        fail(
            f"marketplace {marketplace!r} already points to {configured_root}; "
            f"remove or rename that marketplace before installing {REPO_ROOT}"
        )
    else:
        print(f"Marketplace {marketplace!r} already points to this checkout.")

    run([codex, "plugin", "add", f"{plugin}@{marketplace}"])

    gmsh = shutil.which("gmsh")
    if gmsh is None:
        print("WARNING: plugin installed, but Gmsh is not on PATH.", file=sys.stderr)
        print("Install Gmsh before generating meshes: https://gmsh.info/", file=sys.stderr)
    else:
        launcher = REPO_ROOT / "plugins" / plugin / "scripts" / "chatfdem.py"
        run([runtime_python, str(launcher), "doctor"])

    print("chatFDEM is installed. Start a new Codex chat to load the skill.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
