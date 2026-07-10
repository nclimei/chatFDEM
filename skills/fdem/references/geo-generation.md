# Direct Geo Generation

The MVP allows direct Gmsh `.geo` authoring.

Rules:

- use named parameters for dimensions and mesh sizes;
- put units and intent in comments;
- prefer simple, inspectable topology over clever generated geometry;
- use stable physical names such as `matrix`, `left`, `right`, `top`,
  `bottom`, `hole`, `crack`, `interface_1`;
- for 2D FDEM, define material domains with `Physical Surface` and boundaries
  with `Physical Curve`;
- for 3D FDEM, define material domains with `Physical Volume` and boundaries
  with `Physical Surface`;
- add local mesh-size fields near holes, cracks, notches, and contact/loading
  boundaries.

Generated `.msh` and `.inp` files are derived artifacts. Repair `.geo`, then
regenerate.
