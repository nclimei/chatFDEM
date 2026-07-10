# Visualization

Create a standalone HTML preview from the `.msh` sidecar:

```bash
python -m chatfdem preview model.msh --output model_preview.html
```

For the MVP, the preview is a 2D XY projection. Use it to verify the apparent
geometry, physical group colors, boundary tags, hole/crack placement, and mesh
refinement. Repair `.geo` if the preview disagrees with the brief.
