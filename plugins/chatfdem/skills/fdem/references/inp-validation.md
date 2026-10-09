# Mesh Validation

Run both:

```bash
"<python>" "<plugin-root>/scripts/chatfdem.py" inspect model.msh --json
"<python>" "<plugin-root>/scripts/chatfdem.py" inspect model.inp --json
```

Minimum checks:

- nonzero nodes and elements;
- expected bounding box;
- named physical groups are present;
- material domains have elements;
- boundary groups have elements;
- `.inp` contains nodes, elements, and element sets;
- expected boundary physical groups appear as `.inp` node sets.

These checks do not prove simulation correctness. They only verify that the
mesh handoff artifacts are structurally plausible.
