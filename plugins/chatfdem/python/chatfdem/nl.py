from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PromptError(ValueError):
    pass


class LlmGenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeoGeneration:
    prompt: str
    provider: str
    model: str
    geo_text: str
    brief: dict[str, object]
    raw_text: str = ""


AGENT_MODE_MESSAGE = (
    "chatFDEM is in agent-skill mode. The local Python package cannot borrow the "
    "current Codex/Claude chat session to generate .geo text. In the text-to-cad-style "
    "workflow, ask the agent to author the .geo file directly, then run `python -m "
    "chatfdem mesh ...`. For local offline tests only, explicitly choose "
    "--llm-provider fixture; for a separately managed local model, choose "
    "--llm-provider command."
)
SYSTEM_PROMPT = """You generate Gmsh .geo source for FDEM numerical simulation meshes.
Return only a JSON object with keys "geo" and "brief".
The geo value must be raw Gmsh .geo text, not Markdown.
The brief value must summarize units, dimension, geometry, mesh intent, and physical groups.
Rules:
- Use explicit named parameters near the top.
- Include a units comment.
- For 2D FDEM, use Physical Surface for material domains and Physical Curve for boundaries.
- For 3D FDEM, use Physical Volume for material domains and Physical Surface for boundaries.
- Define stable physical names for material, boundaries, holes, cracks, interfaces, and loading regions.
- Prefer Gmsh Built-in kernel unless OpenCASCADE is needed.
- Ensure the geometry can be meshed by Gmsh without external files.
- Do not include explanatory prose outside the JSON object.
"""


def write_geo_from_prompt(
    prompt: str,
    output_path: str | Path,
    *,
    name: str = "model",
    provider: str | None = None,
    model: str | None = None,
) -> GeoGeneration:
    generation = generate_geo_from_prompt(prompt, name=name, provider=provider, model=model)
    path = Path(output_path).expanduser().resolve()
    if path.suffix.lower() != ".geo":
        raise ValueError(f"Prompt output must be a .geo file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generation.geo_text.rstrip() + "\n", encoding="utf-8")
    return generation


def generate_geo_from_prompt(
    prompt: str,
    *,
    name: str = "model",
    provider: str | None = None,
    model: str | None = None,
) -> GeoGeneration:
    clean_prompt = str(prompt or "").strip()
    if not clean_prompt:
        raise PromptError("Enter a geometry request before generating a mesh.")
    resolved_provider = normalize_provider(provider or os.environ.get("CHATFDEM_LLM_PROVIDER") or "agent")
    if resolved_provider == "agent":
        raise PromptError(AGENT_MODE_MESSAGE)
    if resolved_provider == "fixture":
        return fixture_generation(clean_prompt, name=name)
    if resolved_provider == "command":
        return generate_with_command(clean_prompt, model=model)
    raise PromptError(f"Unsupported LLM provider: {resolved_provider}")


def normalize_provider(value: str) -> str:
    provider = str(value or "").strip().lower()
    aliases = {
        "offline": "fixture",
        "test": "fixture",
        "mock": "fixture",
        "local-command": "command",
        "codex": "agent",
        "skill": "agent",
        "agent-skill": "agent",
    }
    return aliases.get(provider, provider)



def generate_with_command(prompt: str, *, model: str | None = None) -> GeoGeneration:
    command = os.environ.get("CHATFDEM_LLM_COMMAND")
    if not command:
        raise LlmGenerationError("CHATFDEM_LLM_COMMAND is not set for provider=command.")
    completed = subprocess.run(
        command,
        input=SYSTEM_PROMPT + "\n\nUSER PROMPT:\n" + prompt,
        text=True,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise LlmGenerationError(f"LLM command failed ({completed.returncode}): {completed.stderr.strip()}")
    return parse_llm_geo_payload(
        completed.stdout,
        prompt=prompt,
        provider="command",
        model=model or os.environ.get("CHATFDEM_LLM_MODEL") or "command",
    )


def extract_response_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    parts: list[str] = []
    for item in payload.get("output", []) if isinstance(payload.get("output"), list) else []:
        for content in item.get("content", []) if isinstance(item, dict) else []:
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    if parts:
        return "\n".join(parts)
    raise LlmGenerationError("LLM response did not contain output text.")


def parse_llm_geo_payload(raw_text: str, *, prompt: str, provider: str, model: str) -> GeoGeneration:
    text = strip_code_fence(raw_text.strip())
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LlmGenerationError("LLM did not return valid JSON with a geo field.") from exc
    if not isinstance(payload, dict):
        raise LlmGenerationError("LLM response JSON must be an object.")
    geo_text = strip_code_fence(str(payload.get("geo") or "").strip())
    validate_geo_text(geo_text)
    brief = payload.get("brief")
    if not isinstance(brief, dict):
        brief = {"summary": "LLM did not provide a structured brief."}
    return GeoGeneration(prompt=prompt.strip(), provider=provider, model=model, geo_text=geo_text, brief=brief, raw_text=raw_text)


def strip_code_fence(text: str) -> str:
    stripped = text.strip()
    match = re.fullmatch(r"```(?:json|geo|gmsh)?\s*([\s\S]*?)\s*```", stripped)
    return match.group(1).strip() if match else stripped


def validate_geo_text(geo_text: str) -> None:
    if not geo_text:
        raise LlmGenerationError("LLM returned an empty .geo file.")
    lowered = geo_text.lower()
    if "point(" not in lowered and "rectangle(" not in lowered and "box(" not in lowered and "disk(" not in lowered:
        raise LlmGenerationError("Generated .geo does not appear to define geometry entities.")
    if "physical " not in lowered:
        raise LlmGenerationError("Generated .geo must define Physical groups for FDEM handoff.")


def fixture_generation(prompt: str, *, name: str = "model") -> GeoGeneration:
    spec = fixture_rect_hole_spec(prompt, name=name)
    geo_text = render_fixture_rect_hole_geo(spec)
    return GeoGeneration(
        prompt=prompt.strip(),
        provider="fixture",
        model="fixture-rect-hole",
        geo_text=geo_text,
        brief=spec["brief"],
        raw_text=json.dumps({"geo": geo_text, "brief": spec["brief"]}),
    )


def fixture_rect_hole_spec(prompt: str, *, name: str = "model") -> dict[str, Any]:
    text = re.sub(r"\s+", " ", prompt.strip().lower())
    if not text:
        raise PromptError("Enter a geometry request before generating a mesh.")
    width, height = _parse_width_height(text)
    hole_diameter = _parse_hole_diameter(text)
    units = _detect_units(text)
    outer_mesh_size = max(min(width, height) / 10.0, hole_diameter / 2.0)
    hole_mesh_size = max(hole_diameter / 8.0, outer_mesh_size / 4.0)
    return {
        "prompt": prompt.strip(),
        "name": safe_name(name),
        "width": width,
        "height": height,
        "hole_diameter": hole_diameter,
        "hole_radius": hole_diameter / 2.0,
        "outer_mesh_size": outer_mesh_size,
        "hole_mesh_size": hole_mesh_size,
        "brief": {
            "kind": "rectangular_specimen_with_centered_circular_hole",
            "units": units,
            "width": width,
            "height": height,
            "hole_diameter": hole_diameter,
            "outer_mesh_size": outer_mesh_size,
            "hole_mesh_size": hole_mesh_size,
            "physical_groups": {"surfaces": ["matrix"], "curves": ["bottom", "right", "top", "left", "hole"]},
        },
    }


def render_fixture_rect_hole_geo(spec: dict[str, Any]) -> str:
    return f'''// chatFDEM fixture .geo generated for tests and offline demos.
// Prompt: {spec['prompt']}
// Units: {spec['brief']['units']}.
SetFactory("Built-in");

w = {spec['width']:.12g};
h = {spec['height']:.12g};
r = {spec['hole_radius']:.12g};
lc_outer = {spec['outer_mesh_size']:.12g};
lc_hole = {spec['hole_mesh_size']:.12g};

Point(1) = {{-w/2, -h/2, 0, lc_outer}};
Point(2) = {{ w/2, -h/2, 0, lc_outer}};
Point(3) = {{ w/2,  h/2, 0, lc_outer}};
Point(4) = {{-w/2,  h/2, 0, lc_outer}};
Point(5) = {{0, 0, 0, lc_hole}};
Point(6) = {{ r, 0, 0, lc_hole}};
Point(7) = {{0,  r, 0, lc_hole}};
Point(8) = {{-r, 0, 0, lc_hole}};
Point(9) = {{0, -r, 0, lc_hole}};

Line(1) = {{1, 2}};
Line(2) = {{2, 3}};
Line(3) = {{3, 4}};
Line(4) = {{4, 1}};
Circle(5) = {{6, 5, 7}};
Circle(6) = {{7, 5, 8}};
Circle(7) = {{8, 5, 9}};
Circle(8) = {{9, 5, 6}};

Curve Loop(1) = {{1, 2, 3, 4}};
Curve Loop(2) = {{5, 6, 7, 8}};
Plane Surface(1) = {{1, 2}};

Physical Curve("bottom") = {{1}};
Physical Curve("right") = {{2}};
Physical Curve("top") = {{3}};
Physical Curve("left") = {{4}};
Physical Curve("hole") = {{5, 6, 7, 8}};
Physical Surface("matrix") = {{1}};

Field[1] = Distance;
Field[1].CurvesList = {{5, 6, 7, 8}};
Field[1].Sampling = 100;
Field[2] = Threshold;
Field[2].InField = 1;
Field[2].SizeMin = lc_hole;
Field[2].SizeMax = lc_outer;
Field[2].DistMin = 2 * r / 5;
Field[2].DistMax = 3 * r;
Background Field = 2;
Mesh.Algorithm = 6;
Mesh.MshFileVersion = 4.1;
'''


def safe_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "model").strip()).strip("_")
    return name[:64] or "model"


def _detect_units(text: str) -> str:
    match = re.search(r"(?<![A-Za-z])(?P<unit>millimeters|millimeter|meters|meter|mm|m)(?![A-Za-z])", text)
    if not match:
        return "mm"
    unit = match.group("unit")
    return "m" if unit in {"m", "meter", "meters"} else "mm"


def _parse_width_height(text: str) -> tuple[float, float]:
    compact = re.search(r"(?P<width>\d+(?:\.\d+)?)\s*(?:x|by|×)\s*(?P<height>\d+(?:\.\d+)?)", text)
    if compact:
        return float(compact.group("width")), float(compact.group("height"))
    width_first = re.search(r"(?P<width>\d+(?:\.\d+)?)\s*(?:mm|millimeter|millimeters|m|meter|meters)?\s*(?:wide|width)\D{0,40}(?P<height>\d+(?:\.\d+)?)\s*(?:mm|millimeter|millimeters|m|meter|meters)?\s*(?:high|height|tall)", text)
    if width_first:
        return float(width_first.group("width")), float(width_first.group("height"))
    raise PromptError("Fixture provider could not find rectangle width and height.")


def _parse_hole_diameter(text: str) -> float:
    patterns = [
        r"(?P<diameter>\d+(?:\.\d+)?)\s*(?:mm|millimeter|millimeters|m|meter|meters)?\s*(?:diameter|dia\.?|ø)\s*(?:circular\s*)?(?:hole|bore|opening)",
        r"(?:hole|bore|opening)\D{0,24}(?P<diameter>\d+(?:\.\d+)?)\s*(?:mm|millimeter|millimeters|m|meter|meters)?\s*(?:diameter|dia\.?)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return float(match.group("diameter"))
    raise PromptError("Fixture provider could not find circular hole diameter.")
