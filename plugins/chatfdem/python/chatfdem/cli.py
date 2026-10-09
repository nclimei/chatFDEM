from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .gmsh_runner import GmshError, gmsh_version, mesh_geo
from .inp import read_inp
from .msh import read_msh
from .preview import write_html_preview
from .workflow import run_prompt_workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chatfdem",
        description="MVP helpers for direct .geo to FDEM mesh workflows.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local tool availability.")
    doctor.add_argument("--gmsh", default="gmsh", help="Gmsh executable name or path.")

    mesh = subparsers.add_parser("mesh", help="Generate .msh and .inp outputs from a .geo file.")
    mesh.add_argument("geo", help="Input .geo file.")
    mesh.add_argument("--dim", type=int, choices=(1, 2, 3), default=2, help="Mesh dimension to generate.")
    mesh.add_argument("--msh", help="Output .msh path. Defaults beside the .geo file.")
    mesh.add_argument("--inp", help="Output .inp path. Defaults beside the .geo file.")
    mesh.add_argument("--no-inp", action="store_true", help="Only write the .msh output.")
    mesh.add_argument("--report", help="Optional JSON mesh inspection report path.")
    mesh.add_argument("--gmsh", default="gmsh", help="Gmsh executable name or path.")
    mesh.add_argument("--verbosity", type=int, default=2, help="Gmsh verbosity level.")

    inspect = subparsers.add_parser("inspect", help="Inspect a generated .msh or .inp file.")
    inspect.add_argument("target", help="Mesh file to inspect.")
    inspect.add_argument("--json", action="store_true", help="Print JSON output.")

    preview = subparsers.add_parser("preview", help="Create a standalone HTML preview from a .msh file.")
    preview.add_argument("msh", help="Input .msh file.")
    preview.add_argument("--output", help="Output .html path. Defaults beside the .msh file.")

    prompt = subparsers.add_parser("from-prompt", help="Optional standalone prompt-to-.geo workflow; agent-skill mode authors .geo directly.")
    prompt.add_argument("prompt", nargs="?", help="Natural-language geometry request.")
    prompt.add_argument("--prompt-file", help="Read the natural-language request from a text file.")
    prompt.add_argument("--runs-root", default="runs", help="Directory for generated prompt runs.")
    prompt.add_argument("--name", help="Optional run/model name.")
    prompt.add_argument("--gmsh", default="gmsh", help="Gmsh executable name or path.")
    prompt.add_argument("--llm-provider", help="Standalone local provider: command or fixture. Omit for agent-skill mode.")
    prompt.add_argument("--model", help="Standalone local provider model name when --llm-provider is used.")
    prompt.add_argument("--json", action="store_true", help="Print JSON output.")

    serve = subparsers.add_parser("serve", help="Start the local natural-language chatFDEM web interface.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--runs-root", default="runs")
    serve.add_argument("--quiet", action="store_true")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "doctor":
            return _doctor(args)
        if args.command == "mesh":
            return _mesh(args)
        if args.command == "inspect":
            return _inspect(args)
        if args.command == "preview":
            return _preview(args)
        if args.command == "from-prompt":
            return _from_prompt(args)
        if args.command == "serve":
            return _serve(args)
    except (GmshError, OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"chatfdem: error: {exc}\n")
    return 0


def _doctor(args: argparse.Namespace) -> int:
    version = gmsh_version(args.gmsh)
    print(f"gmsh: {version}")
    return 0


def _mesh(args: argparse.Namespace) -> int:
    result = mesh_geo(
        args.geo,
        dim=args.dim,
        msh_path=args.msh,
        inp_path=args.inp,
        export_inp=not args.no_inp,
        gmsh=args.gmsh,
        verbosity=args.verbosity,
    )
    mesh = read_msh(result.msh_path)
    summary = mesh.summary()
    if args.report:
        report_path = Path(args.report).expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"report: {report_path}")
    print(f"geo: {result.geo_path}")
    print(f"msh: {result.msh_path}")
    if result.inp_path is not None:
        print(f"inp: {result.inp_path}")
    if result.appended_node_sets:
        joined = ", ".join(f"{name}={count}" for name, count in sorted(result.appended_node_sets.items()))
        print(f"node_sets: {joined}")
    print(f"nodes: {summary['nodes']}")
    print(f"elements: {summary['elements']}")
    if summary["warnings"]:
        print(f"warnings: {summary['warnings']}")
    return 0


def _inspect(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()
    suffix = target.suffix.lower()
    if suffix == ".msh":
        summary = read_msh(target).summary()
    elif suffix == ".inp":
        summary = read_inp(target).summary()
    else:
        raise ValueError("inspect target must end in .msh or .inp")

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        for key, value in summary.items():
            print(f"{key}: {value}")
    return 0


def _preview(args: argparse.Namespace) -> int:
    output = write_html_preview(args.msh, args.output)
    print(f"preview: {output}")
    return 0


def _from_prompt(args: argparse.Namespace) -> int:
    prompt = str(args.prompt or "").strip()
    if args.prompt_file:
        prompt = Path(args.prompt_file).expanduser().read_text(encoding="utf-8").strip()
    run = run_prompt_workflow(
        prompt,
        runs_root=args.runs_root,
        name=args.name,
        gmsh=args.gmsh,
        llm_provider=args.llm_provider,
        llm_model=args.model,
    )
    summary = run.summary()
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    print(f"run: {run.run_dir}")
    print(f"geo: {run.geo_path}")
    print(f"msh: {run.msh_path}")
    print(f"inp: {run.inp_path}")
    print(f"preview: {run.preview_path}")
    print(f"report: {run.report_path}")
    print(f"llm: {run.generation.provider}/{run.generation.model}")
    print(f"nodes: {run.mesh_summary['nodes']}")
    print(f"elements: {run.mesh_summary['elements']}")
    if run.appended_node_sets:
        joined = ", ".join(f"{name}={count}" for name, count in sorted(run.appended_node_sets.items()))
        print(f"node_sets: {joined}")
    return 0


def _serve(args: argparse.Namespace) -> int:
    from .web import serve

    serve(args.host, args.port, runs_root=args.runs_root, quiet=args.quiet)
    return 0
