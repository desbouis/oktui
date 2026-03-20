# OKtui

**`OKtui` v0.0.1 - OpenStack TUI for final users, built in Python with [Textual](https://textual.textualize.io/).**

⚠️ *This project is young and in heavy development!*

## ✨ Features

- [x] Authentication with token (your OpenStack password is only used to get the token at `OKtui` startup)
- [x] Allow to setup several OpenStack regions in a custom environment variable
- [x] Automatically list instances of the regions at startup (`server list`)
- [x] Filter instances with a simple pattern
- [x] Display a visual status beside instance name
- [x] Display instance information (`server show`)
- [x] Display instance console logs (`console log show`)
- [x] Display instance events (`server event list`)
- [x] Display the last update of commands outputs
- [x] Cache the commands outputs by instance
- [x] Toggle light/dark theme
- [x] Refresh all data
- [x] Refresh the current command output
- [x] Maximize the main content
- [x] Copy executed command with its output

## 🚀 Use OKtui

#### Installation

For now, there is no package of `OKtui`, so to use it, you have to git-clone the project.
Install [`direnv`](https://direnv.net/) and [`uv`](https://docs.astral.sh/uv/) required tools.
Then, you install dependencies:

```bash
cd oktui
direnv allow
make install
```

#### Configuration

Export environment variables:

- `OS_CLIENT_CONFIG_FILE` (optional): the path to your OpenStack configuration file if not in default locations, see [documentation](https://docs.openstack.org/python-openstackclient/2025.2/configuration/index.html)
- `OS_CLOUD` (required): the name of your cloud configuration setup in `clouds.yaml`
- `OKTUI_REGIONS` (required): one or more OpenStack regions

#### Run

**In normal mode:**

```bash
OS_CLIENT_CONFIG_FILE="<path_to_your>/clouds.yaml" OS_CLOUD="<connection_name>" OKTUI_REGIONS="GRA11 SBG5" python main.py
```

**In dev mode:**

To see logs and traces execute:
```bash
textual console
```

then execute in a an other terminal:
```bash
OS_CLIENT_CONFIG_FILE="<path_to_your>/clouds.yaml" OS_CLOUD="<connection_name>" OKTUI_REGIONS="GRA11 SBG5" textual run --dev main.py
```
