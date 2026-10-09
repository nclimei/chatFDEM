# chatFDEM

chatFDEM is an MVP agent workflow for creating FDEM-ready meshes from natural
language.

## Install for Codex

- Python 3.11+
- `gmsh` executable on `PATH`
- Codex CLI with plugin support

The plugin bundles both the `$fdem` skill and the chatFDEM Python runtime. It
does not install anything into the user's Python environment.

Install directly from GitHub:

```bash
codex plugin marketplace add nclimei/chatFDEM
codex plugin add chatfdem@chatFDEM
```

Start a new Codex chat after installation so the skill is loaded. Gmsh remains
a system prerequisite because it is a native application, not a Python
dependency.

For a local checkout, the same setup is available as one cross-platform command:

```bash
python3 install.py
```

The installer registers this checkout as the `chatFDEM` marketplace, installs
the plugin, and checks whether Gmsh is available.


## How to use
In a Codex/Claude interface, example request:

```text
Create a 2D rectangular rock specimen 100 mm wide and 50 mm high with a centered 10 mm diameter hole.
```
