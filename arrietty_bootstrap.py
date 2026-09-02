"""UPBGE text-block entry point for the external Arrietty-UP package."""

import sys
from pathlib import Path

import bge


project_directory = str(Path(bge.logic.expandPath("//")).resolve())
runtime_directory = Path(project_directory) / ".runtime"
current_dependencies = runtime_directory / "current.txt"
if current_dependencies.is_file():
    dependency_directory = (
        runtime_directory
        / "site-packages"
        / current_dependencies.read_text(encoding="ascii").strip()
    )
    if dependency_directory.is_dir() and str(dependency_directory) not in sys.path:
        sys.path.insert(0, str(dependency_directory))
if project_directory not in sys.path:
    sys.path.insert(0, project_directory)

from arrietty_up import runtime

runtime.shutdown()
runtime.reset()


def tick(controller):
    runtime.tick(controller)
