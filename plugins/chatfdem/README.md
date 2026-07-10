# chatFDEM Plugin

This plugin packages the `fdem` skill for Codex/agent installs. The root
`skills/` directory is the development source of truth; `plugins/chatfdem/skills/`
is the bundled install shape.

The default workflow follows `text-to-cad`: the agent runtime supplies the LLM
session, authors the `.geo` file, and calls local chatFDEM/Gmsh tools for mesh
generation, inspection, and preview. The plugin itself does not require a
project LLM credential.

Install from the repository marketplace, then start a new Codex chat so the
skill is loaded:

```bash
codex plugin marketplace add ./
codex plugin add chatfdem@chatFDEM
```

Then ask Codex with a request such as:

```text
Use $fdem to create a 2D rectangular rock specimen 100 mm wide and 50 mm high
with a centered 10 mm diameter hole. Generate the .geo, mesh it to .inp, and
preview it locally.
```

## Python package setup

The plugin does not bundle or install the `chatfdem` Python package. Run tools
from the project checkout:

```bash
cd /home/mei/Documents/chatFDEM
python -m chatfdem doctor
```

From another directory, prefix commands with:

```bash
PYTHONPATH=/home/mei/Documents/chatFDEM python -m chatfdem doctor
```
