---
name: fdem
description: Create, mesh, inspect, and preview FDEM-ready geometry from natural-language simulation requests by authoring Gmsh `.geo` files, exporting `.msh` and `.inp` meshes, preserving boundary node sets, and producing local HTML previews for verification.
---

# FDEM Mesh Generation

Use this skill when the user asks for natural-language geometry creation for an
FDEM simulation, Gmsh `.geo` files, `.inp` mesh exports, physical group tagging,
mesh-size control, boundary tags, cracks, holes, inclusions, layers, specimens,
tunnels, boreholes, or mesh previews for simulation verification.

## Architecture

Follow the `text-to-cad` pattern: the agent session owns natural-language
reasoning, and chatFDEM owns deterministic local tooling. Do not require a
project LLM credential for the default skill workflow. The user's chat request
is the natural-language input; use the agent model to author the `.geo` source
file directly, then run local chatFDEM/Gmsh commands to generate and verify
artifacts.

Keep `.geo` as the source of truth:

```text
natural-language request in agent chat
  -> FDEM geometry brief
  -> agent-authored .geo
  -> Gmsh .msh sidecar
  -> Gmsh/Abaqus .inp export
  -> boundary NSET augmentation from .msh physical groups
  -> mesh inspection report
  -> HTML preview
  -> local web viewer URL
```

Do not generate `.inp` directly. Always generate `.inp` through Gmsh from the
authored `.geo` workflow. The MVP may append deterministic boundary `*NSET`
blocks after Gmsh export; those node sets must be derived from `.msh` physical
groups, not invented separately.

Use SI units or millimeters according to the target solver convention. Record
the chosen units in a `.geo` comment.

## Tool Setup

The plugin bundles the chatFDEM Python runtime. Resolve `<plugin-root>` to the
installed directory containing `.codex-plugin/`, `skills/`, `scripts/`, and
`python/`. Resolve `<python>` to an available Python 3.11+ interpreter; check
`python3` first, then versioned commands such as `python3.13`, `python3.12`, or
`python3.11`. Run the bundled launcher by absolute path; do not assume that the
source repository exists or modify the user's Python environment.

Before running mesh or viewer commands, verify Python and Gmsh:

```bash
"<python>" "<plugin-root>/scripts/chatfdem.py" doctor
```

Use this launcher for `mesh`, `inspect`, `preview`, and `serve`. All model and
artifact paths may remain relative to the user's current working directory.

## Required Workflow

1. Start from the user's natural-language request in the agent chat, not from a
   project-owned LLM API or browser-embedded model session.
2. Write a short FDEM geometry brief from the request: units, dimension,
   geometry, material domains, boundaries, holes/cracks, mesh-size intent, and
   output paths. Read `references/fdem-brief.md` when details are nontrivial.
3. Author a direct Gmsh `.geo` file. Prefer named parameters near the top and
   stable physical names for material domains, boundaries, holes, cracks,
   interfaces, and loading regions. Read `references/geo-generation.md` before
   complex geometry.
4. Define physical groups:
   - material domains: `Physical Surface` for 2D or `Physical Volume` for 3D
   - boundary groups: `Physical Curve` for 2D or `Physical Surface` for 3D
   - special features such as holes, cracks, interfaces, loading regions
5. Generate `.msh` and `.inp`. This also appends boundary node sets derived from
   lower-dimensional physical groups:

   ```bash
   "<python>" "<plugin-root>/scripts/chatfdem.py" mesh path/to/model.geo \
     --msh path/to/model.msh \
     --inp path/to/model.inp \
     --report path/to/model_report.json
   ```

6. Inspect both mesh artifacts:

   ```bash
   "<python>" "<plugin-root>/scripts/chatfdem.py" inspect path/to/model.msh --json
   "<python>" "<plugin-root>/scripts/chatfdem.py" inspect path/to/model.inp --json
   ```

7. Confirm expected `.inp` node sets exist for loading/support boundaries, then
   create a visual verification preview:

   ```bash
   "<python>" "<plugin-root>/scripts/chatfdem.py" preview path/to/model.msh \
     --output path/to/model_preview.html
   ```

8. Start the local chatFDEM web viewer after the preview HTML exists. Use a
   runs/artifact root that contains the preview file, normally the task run
   directory's parent or the repository `runs/` directory:

   ```bash
   "<python>" "<plugin-root>/scripts/chatfdem.py" serve --host 127.0.0.1 --runs-root path/to/runs
   ```

   The command prints the selected base URL and chooses the next available port
   if the requested port is busy. Keep the viewer running for user review.

9. Return a direct browser URL to the preview HTML. Build it as:

   ```text
   http://127.0.0.1:<printed-port>/runs/<preview-path-relative-to-runs-root>
   ```

   Example: if `--runs-root runs` and the preview is
   `runs/case/case_preview.html`, return
   `http://127.0.0.1:<port>/runs/case/case_preview.html`. Also include links to
   `.geo`, `.msh`, `.inp`, and report artifacts when available.

10. If generation, inspection, preview, or viewer startup shows a problem, repair
   the `.geo` source or report the viewer startup failure. Do not edit generated
   `.msh` or `.inp` files by hand.

## Viewer Handoff

Always start or reuse the local chatFDEM web viewer after writing the preview
HTML, then return the direct preview URL. The viewer is an artifact review
surface, not the owner of LLM permissions. If local binding fails due to
sandboxing or permissions, rerun the same serve command with the needed
escalation and report any remaining failure.

## Report Back

Return the local preview URL plus the `.geo`, `.msh`, `.inp`, report JSON, and preview HTML paths. Include
the physical groups found, boundary node sets found, node/element counts,
assumptions, and checks that actually ran. Do not claim simulation correctness
or numerical validity until the target FDEM executable has accepted and run the
mesh.

## References

- `references/fdem-brief.md` - converting prose into an FDEM mesh brief
- `references/geo-generation.md` - direct `.geo` authoring rules
- `references/gmsh-meshing.md` - Gmsh CLI workflow
- `references/inp-validation.md` - `.msh` and `.inp` inspection expectations
- `references/visualization.md` - HTML preview workflow
- `references/repair-loop.md` - repairing failed geometry or mesh generation
