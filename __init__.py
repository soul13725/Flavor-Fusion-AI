"""
AI Recipe Generator — Backend Package.

Modules:
  config.py       Central configuration and constants
  models.py       Pydantic data models
  retrieval.py    Pandas-based RAG retrieval engine
  nutrition.py    Offline nutritional calculation engine
  prompts.py      LLM prompt engineering
  translation.py  Multilingual display string translation
  engine.py       CulinaryEngine orchestrator
  main.py         CLI entry point
"""

from engine import CulinaryEngine, GenerationResult
from models import UserConstraints, TimeConstraints, GeneratedRecipe

__all__ = [
    "CulinaryEngine",
    "GenerationResult",
    "UserConstraints",
    "TimeConstraints",
    "GeneratedRecipe",
]
