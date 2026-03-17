"""
database.py — RecipeDatabase: unified data access layer for Flavor Fusion AI.

Wraps all CSV dataset loading and exposes a high-level interface used by
the Streamlit UI for statistics, search previews, and constraint-aware
retrieval without requiring direct imports from retrieval.py.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd

from config import (
    BEVERAGES_CSV,
    GLOBAL_RECIPES_CSV,
    INDIAN_RECIPES_CSV,
    NUTRITION_DB_CSV,
)
from models import UserConstraints
from retrieval import (
    load_all_recipes,
    load_beverages,
    retrieve_beverage_pairing,
    retrieve_candidate_recipes,
)

logger = logging.getLogger(__name__)


class RecipeDatabase:
    """
    Unified data access object for all Flavor Fusion AI datasets.

    Provides:
      • Lazy-loaded, cached access to each CSV.
      • High-level statistics for the Streamlit dashboard.
      • Delegating retrieval calls to the retrieval pipeline.
    """

    def __init__(self) -> None:
        self._recipes: Optional[pd.DataFrame] = None
        self._beverages: Optional[pd.DataFrame] = None
        self._nutrition: Optional[pd.DataFrame] = None

    # ── Dataset loaders ──────────────────────────────────────────────────────

    @property
    def recipes(self) -> pd.DataFrame:
        """Combined Indian + Global recipes (lazy-loaded)."""
        if self._recipes is None:
            self._recipes = load_all_recipes()
        return self._recipes

    @property
    def beverages(self) -> pd.DataFrame:
        """Cocktails / beverages dataset (lazy-loaded)."""
        if self._beverages is None:
            self._beverages = load_beverages()
        return self._beverages

    @property
    def nutrition(self) -> pd.DataFrame:
        """Nutrition database (lazy-loaded)."""
        if self._nutrition is None:
            try:
                df = pd.read_csv(NUTRITION_DB_CSV, dtype=str).fillna("")
                self._nutrition = df
            except Exception as exc:
                logger.error("Cannot load nutrition DB: %s", exc)
                self._nutrition = pd.DataFrame()
        return self._nutrition

    # ── Statistics ───────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, int]:
        """Return row counts for each dataset — used in the UI dashboard."""
        return {
            "recipes": len(self.recipes),
            "beverages": len(self.beverages),
            "nutrition_entries": len(self.nutrition),
        }

    def get_available_cuisines(self) -> List[str]:
        """Return sorted unique cuisines present in the recipe datasets."""
        if self.recipes.empty or "cuisine" not in self.recipes.columns:
            return []
        return sorted(self.recipes["cuisine"].dropna().unique().tolist())

    def get_available_meal_categories(self) -> List[str]:
        """Return sorted unique meal categories across recipes + beverages."""
        cats: List[str] = []
        for df in (self.recipes, self.beverages):
            if "meal_category" in df.columns:
                cats.extend(df["meal_category"].dropna().unique().tolist())
        return sorted(set(cats))

    def sample_recipes(self, n: int = 5) -> List[Dict]:
        """Return n random recipe rows as dicts — for UI preview cards."""
        if self.recipes.empty:
            return []
        sample = self.recipes.sample(min(n, len(self.recipes)))
        return sample[
            [c for c in ("recipe_name", "cuisine", "meal_category", "total_time_min")
             if c in sample.columns]
        ].to_dict(orient="records")

    def sample_beverages(self, n: int = 3) -> List[Dict]:
        """Return n random beverage rows as dicts."""
        if self.beverages.empty:
            return []
        sample = self.beverages.sample(min(n, len(self.beverages)))
        return sample[
            [c for c in ("beverage_name", "type", "category")
             if c in sample.columns]
        ].to_dict(orient="records")

    # ── Retrieval delegation ─────────────────────────────────────────────────

    def find_recipes(self, constraints: UserConstraints) -> List[Dict]:
        """
        Delegate to the full retrieval pipeline.
        Returns the top-k candidates matching the given constraints.
        """
        return retrieve_candidate_recipes(constraints)

    def find_beverage_pairing(self, constraints: UserConstraints) -> List[Dict]:
        """
        Delegate to the beverage pairing retrieval pipeline.
        """
        return retrieve_beverage_pairing(constraints)

    # ── Nutrition lookup ─────────────────────────────────────────────────────

    def lookup_ingredient(self, name: str) -> Optional[Dict]:
        """
        Quick nutrition lookup for a single ingredient name.
        Returns the best matching row as a dict, or None.
        """
        from nutrition import _fuzzy_match_ingredient, _load_nutrition_db
        db = _load_nutrition_db()
        if db.empty:
            return None
        row, score = _fuzzy_match_ingredient(name, db)
        if row is None:
            return None
        result = row.to_dict()
        result["_match_score"] = score
        return result

    # ── Path info ────────────────────────────────────────────────────────────

    @staticmethod
    def get_data_paths() -> Dict[str, str]:
        """Return the absolute paths of all dataset files."""
        return {
            "indian_recipes": str(INDIAN_RECIPES_CSV),
            "global_recipes": str(GLOBAL_RECIPES_CSV),
            "beverages": str(BEVERAGES_CSV),
            "nutrition_database": str(NUTRITION_DB_CSV),
        }
