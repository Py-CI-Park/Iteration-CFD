# Blender research adapter outbound notice

Following the repository's existing `tools/promo/LICENSE-NOTICE.md` classification, these independently authored scripts that import Blender's bpy API are distributed under GPL-2.0-or-later as separate Blender programs:

- `research/a321-shell/export_reference.py`
- `research/a321-shell/blender_shell.py`
- `research/a321-shell/reopen_shell.py`
- inherited `research/a321-preflight/inventory.py`, `prepare_surface.py`, `extract_wing.py`, `reopen_candidate.py`

They are not linked into the Rust/CUDA solver. No GPL implementation was copied or consulted. This adapter classification does not relicense the solver or assert rights in OEM geometry. The repository root licensing applies to other research scripts as otherwise documented. See https://www.gnu.org/licenses/old-licenses/gpl-2.0.html for the licence text and the existing promo notice for this project's policy.
