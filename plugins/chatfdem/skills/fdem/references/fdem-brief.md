# FDEM Brief

Before writing `.geo`, extract:

- units and whether the model is 2D or 3D;
- specimen/domain dimensions;
- holes, cracks, inclusions, layers, interfaces, and notches;
- material domains that need physical groups;
- boundary groups for loading, supports, measurement, or contacts;
- mesh density targets and local refinement zones;
- expected output paths for `.geo`, `.msh`, `.inp`, report, and preview.

If a required solver convention is unknown, proceed with explicit assumptions
unless the missing detail changes the topology or physical group naming.
