# Gmsh Meshing

Use the local `chatfdem` CLI:

```bash
python -m chatfdem mesh model.geo --msh model.msh --inp model.inp --report model_report.json
```

The CLI first writes an ASCII Gmsh 4.x `.msh` sidecar, then converts that mesh
to Abaqus `.inp`. After the Gmsh export, chatFDEM appends boundary `*NSET`
blocks for lower-dimensional physical groups such as 2D `Physical Curve`
boundaries. Keep the `.msh` because it preserves metadata used by the MVP
inspector, node-set augmentation, and HTML preview.

Use `--dim 2` for plane FDEM geometry and `--dim 3` for volume meshes. Use
`--no-inp` only when an intermediate `.msh` is needed without an Abaqus export.
