# chatFDEM

chatFDEM is an agent workflow for creating FDEM-ready meshes from natural
language.

> **Development and use notice:** This is unpublished work that is being
> actively developed and tested. Anyone wishing to use chatFDEM for research,
> commercial, educational, or any other work must first obtain written
> permission from both Mei Li and Giovanni Grasselli at the University of
> Toronto. We welcome collaboration inquiries.
>
> Contact: Mei Li (meili.li@mail.utoronto.ca) & Giovanni Grasselli (giovanni.grasselli@utoronto.ca)


## Demo videos

Watch these short demonstrations for an overview of the chatFDEM workflow:

- [2D demo](https://utoronto-my.sharepoint.com/:v:/g/personal/meili_li_mail_utoronto_ca/IQC2mr7jNcnQTatbgx96e7X-AR_5K2ndvDRBZCuyM-7S4jk?e=jaNI8K)
- [3D demo](https://utoronto-my.sharepoint.com/:v:/g/personal/meili_li_mail_utoronto_ca/IQAZYKxRjmXwQ6HO4rx6dxNDAS1-7QOA6m7bsPBntOBgW9Y?e=OmYp0y)

Open a link in your browser and use the SharePoint video player. If prompted,
sign in with an UofT account. After
watching, follow the Codex or Claude Code installation instructions below to
try the demonstrated workflow.

## Install for Codex

These steps install Codex, chatFDEM, and the bundled `$fdem` skill on a
computer that does not already have Codex.

### 1. Install the prerequisites

Install:

- [Python 3.11 or newer](https://www.python.org/downloads/)
- [Gmsh](https://gmsh.info/) and ensure the `gmsh` command is on `PATH`
- [Git](https://git-scm.com/downloads/)
- Internet access and a ChatGPT account that can use Codex

Verify the commands in a terminal:

```bash
python3 --version
gmsh --version
git --version
```

On Windows, use `python --version` if `python3` is unavailable. When
installing Python or Gmsh on Windows, enable the option that adds the program to
`PATH`.

### 2. Install Codex CLI

On macOS or Linux:

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

On Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
```

Open a new terminal and verify the installation:

```bash
codex --version
```

These are the installation commands distributed with the official
`@openai/codex` package. Additional options are available in the
[Codex documentation](https://developers.openai.com/codex).



### 3. Sign in to Codex

Run:

```bash
codex
```

Select **Sign in with ChatGPT** and complete authentication. Exit that first
session after sign-in if you are not yet in the folder where you want to create
meshes.

### 4. Install chatFDEM

The marketplace command downloads the repository from GitHub. To install chatFDEM 
in Claud, replace 'codex' in the command below to 'claude'.

```bash
codex plugin marketplace add nclimei/chatFDEM
codex plugin add chatfdem@chatFDEM
```

The plugin installs the `$fdem` skill and the chatFDEM Python module together
inside the current user's Codex plugin cache. Python and Gmsh remain system
prerequisites.

Update an installed chatFDEM
```bash
codex plugin marketplace upgrade chatFDEM
```

### 5. Start Codex in the working folder

Create or open a folder where Codex may write the generated mesh files, then
start a new Codex session from that folder:

```bash
mkdir my-fdem-project
cd my-fdem-project
codex
```

Example request:

```text
Create a 2D rectangular rock specimen 100 mm wide and 50 mm high
with a centered 10 mm diameter hole.
```

The skill generates the Irazu ready mesh file `.inp`, inspection report, and HTML
preview in the requested working folder. A folder outside the active Codex
workspace may require a sandbox permission approval. Change Codex's permission
settings if you regularly need to write to another location.



