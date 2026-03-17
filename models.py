"""
models.py — Pydantic data models for the Culinary Engine.

Defines strict schemas for user constraints, LLM output, and nutritional reports.
"""

from __future__ import annotations

import enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from config import VALID_SKILL_LEVELS, VALID_CUISINES, VALID_MEAL_CATEGORIES


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class SkillLevel(str, enum.Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    PRO = "Pro"


# ─────────────────────────────────────────────────────────────────────────────
# User Input Models
# ─────────────────────────────────────────────────────────────────────────────

class TimeConstraints(BaseModel):
    """Maximum prep and total cooking time the user can spend."""
    max_prep_minutes: int = Field(ge=0, default=60)
    max_total_minutes: int = Field(ge=0, default=120)


class UserConstraints(BaseModel):
    """
    Full set of multidimensional parameters the user can provide
    to the CulinaryEngine.
    """
    skill_level: SkillLevel = SkillLevel.INTERMEDIATE
    available_equipment: List[str] = Field(default_factory=list)
    available_ingredients: List[str] = Field(default_factory=list)
    cuisine_preference: str = "Global"
    time_constraints: TimeConstraints = Field(default_factory=TimeConstraints)
    meal_category: str = "Dinner"
    absurd_combos: bool = False
    target_language: str = "en"  # ISO 639-1 code
    servings: int = Field(ge=1, default=2)

    @field_validator("cuisine_preference")
    @classmethod
    def validate_cuisine(cls, v: str) -> str:
        if v not in VALID_CUISINES:
            raise ValueError(
                f"Unknown cuisine '{v}'. Choose from: {sorted(VALID_CUISINES)}"
            )
        return v

    @field_validator("meal_category")
    @classmethod
    def validate_meal_category(cls, v: str) -> str:
        if v not in VALID_MEAL_CATEGORIES:
            raise ValueError(
                f"Unknown meal category '{v}'. Choose from: {sorted(VALID_MEAL_CATEGORIES)}"
            )
        return v


# ─────────────────────────────────────────────────────────────────────────────
# LLM Output Models (mirrors the JSON schema the LLM must produce)
# ─────────────────────────────────────────────────────────────────────────────

class IngredientItem(BaseModel):
    """A single ingredient line from the LLM output."""
    name: str
    quantity_grams: float
    original_measure: str = ""
    preparation_note: str = ""


class BeveragePairing(BaseModel):
    """Beverage pairing attached to the main recipe."""
    name: str
    type: str  # Cocktail | Mocktail | Coffee | Tea | Smoothie
    ingredients: List[IngredientItem] = Field(default_factory=list)
    instructions: List[str] = Field(default_factory=list)


class GeneratedRecipe(BaseModel):
    """
    Strict schema for the JSON object the LLM *must* return.
    Parsed and validated before any downstream processing.
    """
    recipe_name: str
    cuisine_type: str
    estimated_time_minutes: int
    equipment_used: List[str] = Field(default_factory=list)
    servings: int = 2
    ingredients: List[IngredientItem] = Field(default_factory=list)
    step_by_step_instructions: List[str] = Field(default_factory=list)
    beverage_pairing: Optional[BeveragePairing] = None


# ─────────────────────────────────────────────────────────────────────────────
# Nutritional Report Model
# ─────────────────────────────────────────────────────────────────────────────

class NutrientProfile(BaseModel):
    """Per-serving macronutrient breakdown."""
    calories_kcal: float = 0.0
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbs_g: float = 0.0
    fiber_g: float = 0.0
    sugar_g: float = 0.0
    sodium_mg: float = 0.0


class IngredientNutrition(BaseModel):
    """Nutrition contribution of a single ingredient."""
    ingredient_name: str
    matched_db_name: str
    match_confidence: int  # fuzzy score 0-100
    quantity_grams: float
    nutrients: NutrientProfile


class RecipeNutritionReport(BaseModel):
    """Aggregated nutritional report for a full recipe."""
    recipe_name: str
    servings: int
    per_serving: NutrientProfile
    total: NutrientProfile
    ingredient_breakdown: List[IngredientNutrition] = Field(default_factory=list)
    unmatched_ingredients: List[str] = Field(default_factory=list)
