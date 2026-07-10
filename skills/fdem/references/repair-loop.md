# Repair Loop

When meshing or inspection fails:

1. Read the Gmsh error or inspection warning.
2. Change the smallest responsible `.geo` section.
3. Regenerate `.msh` and `.inp`.
4. Reinspect and recreate the preview.

Common repairs:

- missing physical groups: add `Physical Curve`, `Physical Surface`, or
  `Physical Volume` declarations;
- empty physical group: verify entity IDs after boolean operations;
- poor local resolution: lower mesh size near the feature or add a field;
- wrong hole/crack location: verify point coordinates and curve loops;
- unexpected open surface: check loop orientation and surface definitions.
