from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .gmsh_runner import mesh_geo
from .inp import read_inp
from .msh import read_msh
from .nl import GeoGeneration, safe_name, write_geo_from_prompt
from .preview import write_html_preview


@dataclass(frozen=True)
class PromptRun:
    prompt: str
    name: str
    run_dir: Path
    geo_path: Path
    msh_path: Path
    inp_path: Path
    preview_path: Path
    report_path: Path
    generation: GeoGeneration
    mesh_summary: dict[str, object]
    inp_summary: dict[str, object]
    appended_node_sets: dict[str, int]

    def summary(self, *, base_dir: Path | None = None) -> dict[str, object]:
        def display(path: Path) -> str:
            if base_dir is None:
                return str(path)
            try:
                return path.resolve().relative_to(base_dir.resolve()).as_posix()
            except ValueError:
                return str(path)

        return {
            "prompt": self.prompt,
            "name": self.name,
            "brief": self.generation.brief,
            "llm": {
                "provider": self.generation.provider,
                "model": self.generation.model,
            },
            "paths": {
                "run_dir": display(self.run_dir),
                "geo": display(self.geo_path),
                "msh": display(self.msh_path),
                "inp": display(self.inp_path),
                "preview": display(self.preview_path),
                "report": display(self.report_path),
            },
            "mesh": self.mesh_summary,
            "inp": self.inp_summary,
            "appended_node_sets": self.appended_node_sets,
        }


def run_prompt_workflow(
    prompt: str,
    *,
    runs_root: str | Path = "runs",
    name: str | None = None,
    gmsh: str = "gmsh",
    llm_provider: str | None = None,
    llm_model: str | None = None,
) -> PromptRun:
    run_name = safe_name(name or _name_from_prompt(prompt))
    run_dir = _unique_run_dir(Path(runs_root).expanduser().resolve(), run_name)
    geo_path = run_dir / f"{run_name}.geo"
    msh_path = run_dir / f"{run_name}.msh"
    inp_path = run_dir / f"{run_name}.inp"
    preview_path = run_dir / f"{run_name}_preview.html"
    report_path = run_dir / f"{run_name}_report.json"

    generation = write_geo_from_prompt(prompt, geo_path, name=run_name, provider=llm_provider, model=llm_model)
    mesh_result = mesh_geo(geo_path, msh_path=msh_path, inp_path=inp_path, gmsh=gmsh)
    mesh_summary = read_msh(mesh_result.msh_path).summary()
    inp_summary = read_inp(mesh_result.inp_path).summary()
    write_html_preview(mesh_result.msh_path, preview_path)

    run = PromptRun(
        prompt=prompt.strip(),
        name=run_name,
        run_dir=run_dir,
        geo_path=geo_path,
        msh_path=msh_path,
        inp_path=inp_path,
        preview_path=preview_path,
        report_path=report_path,
        generation=generation,
        mesh_summary=mesh_summary,
        inp_summary=inp_summary,
        appended_node_sets=mesh_result.appended_node_sets,
    )
    report_path.write_text(json.dumps(run.summary(base_dir=run_dir), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return run


def _name_from_prompt(prompt: str) -> str:
    text = safe_name(prompt.lower())
    words = [word for word in text.split("_") if word]
    return "_".join(words[:6]) or "prompt_model"


def _unique_run_dir(root: Path, name: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = root / f"{timestamp}_{name}"
    candidate = base
    suffix = 2
    while candidate.exists():
        candidate = root / f"{base.name}_{suffix}"
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate
