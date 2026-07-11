# Copyright 2026 Enactic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Resolve short dataset base names to versioned folder names.

Naming rules
------------
- ``NAME`` is a short base (e.g. ``dataset``), not a task title or episode count.
- Create (default): write to ``{base}_v{N}`` with the next free N (from 0).
- Resume: append to the latest existing ``{base}_v{N}`` (or legacy unversioned
  ``{base}`` if that is all that exists).

If ``NAME`` is already versioned (``*_v{digits}``), it is treated as an exact
folder name (typically pre-resolved by the run script).
"""

from __future__ import annotations

import re
from pathlib import Path

_VERSIONED_NAME = re.compile(r"^(?P<base>.+)_v(?P<index>\d+)$")


def is_versioned_name(name: str) -> bool:
    """Return True when name already looks like ``{base}_v{N}``."""
    return _VERSIONED_NAME.fullmatch(name) is not None


def list_version_indices(directory: Path, base: str) -> list[int]:
    """Return sorted version indices for ``{base}_v*`` directories under directory."""
    if not directory.is_dir():
        return []
    pattern = re.compile(rf"^{re.escape(base)}_v(\d+)$")
    indices: list[int] = []
    for path in directory.iterdir():
        if not path.is_dir():
            continue
        match = pattern.fullmatch(path.name)
        if match:
            indices.append(int(match.group(1)))
    return sorted(indices)


def resolve_dataset_name(
    directory: Path | str,
    name: str,
    *,
    resume: bool = False,
) -> str:
    """Resolve a dataset folder name under ``directory``.

    Parameters
    ----------
    directory:
        Parent output directory (``DIRECTORY``).
    name:
        Short base name, or an already-versioned exact name.
    resume:
        When True, select the latest existing version for the base.
        When False, allocate the next free ``{base}_v{N}``.
    """
    directory = Path(directory)
    name = str(name).strip()
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError(f"Invalid dataset name: {name!r}")

    exact = _VERSIONED_NAME.fullmatch(name)
    if exact:
        target = directory / name
        if resume:
            if not target.is_dir():
                raise ValueError(
                    f"Cannot resume: dataset folder does not exist: {target}"
                )
            return name
        if target.exists():
            raise ValueError(
                f"Dataset folder already exists: {target}. "
                "Use --resume to append, or omit the version suffix to auto-allocate."
            )
        return name

    base = name
    indices = list_version_indices(directory, base)
    legacy = directory / base

    if resume:
        if indices:
            return f"{base}_v{max(indices)}"
        if legacy.is_dir():
            return base
        raise ValueError(
            f"Cannot resume: no dataset found for base {base!r} under {directory}"
        )

    next_index = max(indices, default=-1) + 1
    return f"{base}_v{next_index}"


def parse_resume_flag(value: str | bool | None) -> bool:
    """Parse CLI/env resume flag (1/true/yes/on)."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
