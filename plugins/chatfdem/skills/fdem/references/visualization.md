# Visualization

Create a standalone HTML preview from the `.msh` sidecar:

```bash
"<python>" "<plugin-root>/scripts/chatfdem.py" preview model.msh --output model_preview.html
```

The preview renders 2D meshes as an XY SVG and 3D meshes with an interactive
canvas orbit view. Use it to verify the apparent geometry, physical group
colors, boundary tags, hole/crack placement, layer/contact surfaces, and mesh
refinement. Repair `.geo` if the preview disagrees with the brief.
