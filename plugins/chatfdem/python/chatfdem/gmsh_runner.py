from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class GmshError(RuntimeError):
    """Raised when the Gmsh executable cannot complete a requested operation."""


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class MeshResult:
    geo_path: Path
    msh_path: Path
    inp_path: Path | None
    mesh_command: CommandResult
    inp_command: CommandResult | None
    appended_node_sets: dict[str, int]


def resolve_gmsh(gmsh: str = "gmsh") -> str:
    resolved = shutil.which(gmsh)
    if not resolved:
        raise GmshError(f"Gmsh executable not found on PATH: {gmsh}")
    return resolved


def gmsh_version(gmsh: str = "gmsh") -> str:
    result = run_gmsh([resolve_gmsh(gmsh), "--version"])
    return result.stdout.strip()


def run_gmsh(command: list[str], *, cwd: Path | None = None) -> CommandResult:
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    result = CommandResult(
        command=tuple(command),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    if completed.returncode != 0:
        command_text = " ".join(command)
        details = (completed.stderr or completed.stdout).strip()
        raise GmshError(f"Gmsh command failed ({completed.returncode}): {command_text}\n{details}")
    return result


def mesh_geo(
    geo_path: str | Path,
    *,
    dim: int = 2,
    msh_path: str | Path | None = None,
    inp_path: str | Path | None = None,
    export_inp: bool = True,
    gmsh: str = "gmsh",
    verbosity: int = 2,
) -> MeshResult:
    if dim not in {1, 2, 3}:
        raise ValueError("dim must be 1, 2, or 3")

    geo = Path(geo_path).expanduser().resolve()
    if geo.suffix.lower() != ".geo":
        raise ValueError(f"Expected a .geo file, got: {geo}")
    if not geo.is_file():
        raise FileNotFoundError(f".geo file not found: {geo}")

    msh = Path(msh_path).expanduser().resolve() if msh_path is not None else geo.with_suffix(".msh")
    inp = None
    if export_inp:
        inp = Path(inp_path).expanduser().resolve() if inp_path is not None else geo.with_suffix(".inp")
    if msh.suffix.lower() != ".msh":
        raise ValueError(f"MSH output must end in .msh: {msh}")
    if inp is not None and inp.suffix.lower() != ".inp":
        raise ValueError(f"INP output must end in .inp: {inp}")

    msh.parent.mkdir(parents=True, exist_ok=True)
    if inp is not None:
        inp.parent.mkdir(parents=True, exist_ok=True)

    gmsh_bin = resolve_gmsh(gmsh)
    mesh_command = run_gmsh(
        [
            gmsh_bin,
            str(geo),
            f"-{dim}",
            "-format",
            "msh4",
            "-setnumber",
            "Mesh.Binary",
            "0",
            "-o",
            str(msh),
            "-v",
            str(verbosity),
        ]
    )
    if not msh.is_file() or msh.stat().st_size == 0:
        raise GmshError(f"Gmsh did not create a non-empty .msh file: {msh}")

    inp_command = None
    appended_node_sets: dict[str, int] = {}
    if inp is not None:
        inp_command = run_gmsh(
            [
                gmsh_bin,
                str(msh),
                "-format",
                "inp",
                "-o",
                str(inp),
                "-save",
                "-v",
                str(verbosity),
            ]
        )
        if not inp.is_file() or inp.stat().st_size == 0:
            raise GmshError(f"Gmsh did not create a non-empty .inp file: {inp}")
        from .inp import append_node_sets
        from .msh import read_msh

        appended_node_sets = append_node_sets(inp, read_msh(msh).boundary_node_sets())

    return MeshResult(
        geo_path=geo,
        msh_path=msh,
        inp_path=inp,
        mesh_command=mesh_command,
        inp_command=inp_command,
        appended_node_sets=appended_node_sets,
    )
