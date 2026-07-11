# chatFDEM

chatFDEM is an MVP agent workflow for creating FDEM-ready meshes from natural
language. Like `text-to-cad`, the project itself does not need its own LLM credential in
the default workflow: the surrounding agent session interprets the user's
request, authors a Gmsh `.geo` file, and then uses local deterministic tools to
mesh, inspect, and preview the result.

The current MVP deliberately keeps `.geo` as the source of truth:

```text
natural language request in the agent chat
  -> agent-authored .geo
  -> Gmsh .msh sidecar
  -> Gmsh/Abaqus .inp export
  -> boundary NSET augmentation from .msh physical groups
  -> mesh inspection report
  -> HTML preview for visual verification
```

## Requirements

- Python 3.11+
- `gmsh` executable on `PATH`

The Python `gmsh` module is not required for the MVP. The generated `.inp` is
first exported by Gmsh, then chatFDEM appends a marked `*NSET` block for
lower-dimensional physical groups such as named boundaries.

Check the local setup:

```bash
python -m chatfdem doctor
```

## Python Module Setup

Run chatFDEM from this project checkout. The Codex plugin supplies the `$fdem`
skill instructions, while the Python module lives in `/home/mei/Documents/chatFDEM`.

```bash
cd /home/mei/Documents/chatFDEM
python -m chatfdem doctor
```

From another directory, use:

```bash
PYTHONPATH=/home/mei/Documents/chatFDEM python -m chatfdem doctor
```

## Agent Workflow

Use chatFDEM the same way `text-to-cad` is used: ask the agent to use the skill.
The chat interface belongs to Codex/Claude/the agent host; chatFDEM supplies the
local tools and preview artifacts.

Example request:

```text
Use $fdem to create a 2D rectangular rock specimen 100 mm wide and 50 mm high
with a centered 10 mm diameter hole. Tag left, right, top, bottom, and hole
boundaries, generate the .inp mesh, and preview it.
```

The agent should:

1. Write a short FDEM geometry brief.
2. Author a `.geo` file directly from the request.
3. Run Gmsh through chatFDEM to create `.msh` and `.inp` artifacts.
4. Inspect `.msh` and `.inp` outputs.
5. Generate an HTML preview, start the local web viewer, and return the preview URL plus artifact paths.

## Direct `.geo` Workflow

You can still generate a mesh and Abaqus `.inp` file from a direct `.geo` file:

```bash
python -m chatfdem mesh examples/geo/rect_hole.geo \
  --msh outputs/rect_hole.msh \
  --inp outputs/rect_hole.inp \
  --report outputs/rect_hole_report.json
```

Inspect the generated mesh:

```bash
python -m chatfdem inspect outputs/rect_hole.msh --json
python -m chatfdem inspect outputs/rect_hole.inp --json
```

Create a standalone HTML preview:

```bash
python -m chatfdem preview outputs/rect_hole.msh \
  --output outputs/rect_hole_preview.html
```

Open `outputs/rect_hole_preview.html` directly, or start the local web viewer
and return a URL served from the artifact root. Two-dimensional meshes render as
SVG previews; three-dimensional meshes render with an interactive canvas orbit
viewer for rotate, zoom, and pan inspection.

## Local Viewer

The local web interface is for reviewing generated artifacts. It is not the
agent host and it should not be treated as the owner of LLM permissions in the
text-to-cad-style workflow. After the preview HTML is created, the agent should
start the viewer and return a direct URL.

```bash
python -m chatfdem serve --host 127.0.0.1 --runs-root runs
```

If the default port is busy, chatFDEM uses the next available port; you can also
choose one explicitly with `python -m chatfdem serve --port 8770`. A preview at
`runs/case/case_preview.html` is served as:

```text
http://127.0.0.1:<printed-port>/runs/case/case_preview.html
```

## Agent Plugin

This repository includes local agent plugin manifests:

```bash
# Codex-style local marketplace
codex plugin marketplace add nclimei/chatFDEM
codex plugin add chatfdem@chatFDEM
```

The plugin entry is under `plugins/chatfdem`, and the bundled skill is under
`plugins/chatfdem/skills/fdem`. No project LLM credential is required for the default
agent-skill workflow; the installed agent runtime supplies the language model
session, and chatFDEM supplies local mesh/preview tools.

## MVP Agent Contract

For now, the agent converts natural-language requests into direct Gmsh `.geo`
files. Each authored `.geo` should:

- use explicit dimensions and units in comments;
- define named `Physical Surface` or `Physical Volume` groups for material
  domains;
- define named `Physical Curve` or `Physical Surface` groups for boundaries;
- set mesh-size controls near holes, cracks, interfaces, or loading regions;
- generate a `.msh` sidecar and `.inp` export through `chatfdem mesh`;
- preserve lower-dimensional physical groups as boundary `NSET`s in `.inp`;
- run `chatfdem inspect` and `chatfdem preview` before handing artifacts to an
  FDEM executable.

See [skills/fdem/SKILL.md](skills/fdem/SKILL.md) for the agent workflow.
