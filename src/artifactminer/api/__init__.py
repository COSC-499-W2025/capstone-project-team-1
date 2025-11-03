"""FastAPI application package for Artifact Miner."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Import only for type checkers; avoids importing submodule at runtime.
    from .app import app  # noqa: F401

__all__ = []
