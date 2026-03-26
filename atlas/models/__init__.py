"""Models package for ATLAS.

Exports :func:`get_llm` which returns the configured LangChain chat model.
"""

from atlas.models.factory import get_llm

__all__ = ["get_llm"]
