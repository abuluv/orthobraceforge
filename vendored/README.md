# Vendored Packages

Each subdirectory here is a placeholder `__init__.py` representing an external repository
that would be cloned and integrated at build time. The actual runtime logic lives in the
corresponding wrapper modules under `agents/`.

## Package Inventory

| Directory | Upstream Repo | PyPI Alternative | Agent Wrapper |
|-----------|--------------|------------------|---------------|
| `agentic3d/` | reetm09/agentic3d | None (Autogen-based) | `agents/agentic3d.py` |
| `forma_ai/` | andreyka/forma-ai-service | `build123d` (PyPI) | `agents/forma_ai.py` |
| `talkcad/` | outerreaches/talkcad | None | `agents/talkcad.py` |
| `cad_agent/` | Svetlana-DAO-LLC/cad-agent | `pyvista` (PyPI) | `agents/cad_render.py` |
| `llm_3d_print/` | BaratiLab/LLM-3D-Print | None (custom CNN) | `agents/print_defect.py` |
| `ortho_insoles/` | Green-AI-Hub/Training-Prediction-Toolbox | `trimesh` (PyPI) | `agents/ortho_insoles.py` |
| `octo_mcp/` | OctoEverywhere/mcp | `requests` + OctoPrint REST | `agents/octo_mcp.py` |
| `agentic_alloy/` | BaratiLab/Agentic-Additive-Manufacturing-Alloy | None | `agents/agentic_alloy.py` |
| `chat_to_stl/` | nchourrout/Chat-To-STL | None | `agents/chat_to_stl.py` |

## Dependency Status

- **forma_ai → build123d**: `build123d` is available on PyPI (`pip install build123d`).
  The vendored stub can be replaced by a direct PyPI dependency.

- **cad_agent → pyvista**: `pyvista` is available on PyPI and already listed in
  `requirements.txt`. The vendored stub is redundant.

- **ortho_insoles → trimesh**: `trimesh` is available on PyPI and already listed in
  `requirements.txt`. The vendored stub is redundant.

- **octo_mcp**: Functionality is implemented natively using Python's `urllib` standard
  library in `agents/octo_mcp.py`. No external package required.

- **agentic3d, talkcad, llm_3d_print, agentic_alloy, chat_to_stl**: No equivalent
  PyPI package. Stubs remain as integration points for future full integration.

## Integration Plan

For production deployment, each vendored stub should be replaced by:
1. A `git submodule` pointing to the upstream repo, or
2. A vendored copy of the upstream source under the stub directory, or
3. A PyPI package where available (see table above).

The agent wrappers in `agents/` are designed to call into these packages once populated.
