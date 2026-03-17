"""
prompts.py — LLM Prompt Engineering Module.

Constructs the exact system_prompt and user_prompt strings sent to the LLM API.
The prompt strictly mandates JSON-only output that conforms to the schema defined
in config.RECIPE_JSON_SCHEMA.

Design principles:
  • All reasoning and ingredient names MUST be in English so the offline
    nutritional matcher (which queries an English CSV) does not break.
  • The LLM MUST respond with nothing but valid JSON — no preamble, no markdown.
  • Dynamic injection of user constraints, retrieved candidates, and mode flags.
"""

from __future__ import annotations

import json
from typing import Dict, List

from config import RECIPE_JSON_SCHEMA
from models import UserConstraints


# ─────────────────────────────────────────────────────────────────────────────
# System Prompt (static backbone — constraints and candidates are injected)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """\
You are a world-class culinary AI specializing in recipe creation, global cuisines, \
and beverage pairing.  You combine classical technique with data-driven precision.

═══════════════════════════════════════════════════════════════════════
ABSOLUTE RULES (violation = failure):
═══════════════════════════════════════════════════════════════════════
1. **Language mandate**: ALL reasoning, ALL ingredient names, and ALL output fields \
   MUST be in English.  Do NOT translate ingredient names — the downstream nutritional \
   engine relies on exact English matches against a CSV database.
2. **Output format**: Respond with NOTHING but a single valid JSON object.  No markdown \
   fences, no commentary, no explanation before or after the JSON.
3. **Ingredient precision**: Every ingredient MUST include a `quantity_grams` field with \
   the weight in grams (numeric, > 0).  Also include `original_measure` for human readability.
4. **Equipment honesty**: Only use equipment from the ALLOWED list below.
5. **Time bound**: The recipe's `estimated_time_minutes` MUST NOT exceed {max_total_minutes} minutes.
6. **Skill calibration**: Tailor complexity to the stated skill level: {skill_level}.
7. **Servings**: Recipe should yield exactly {servings} serving(s).
8. **Beverage pairing**: Always include a `beverage_pairing` object, even for beverage-only requests \
   (in that case, suggest a complementary snack instead and note it in the recipe).

═══════════════════════════════════════════════════════════════════════
REQUIRED JSON SCHEMA:
═══════════════════════════════════════════════════════════════════════
{json_schema}

═══════════════════════════════════════════════════════════════════════
USER CONSTRAINTS:
═══════════════════════════════════════════════════════════════════════
• Skill level       : {skill_level}
• Available equipment: {equipment}
• Available ingredients: {ingredients}
• Cuisine preference: {cuisine}
• Meal category     : {meal_category}
• Max prep time     : {max_prep_minutes} min
• Max total time    : {max_total_minutes} min
• Servings          : {servings}

{mode_section}

{candidates_section}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Mode Sections (absurd combos vs. normal retrieval)
# ─────────────────────────────────────────────────────────────────────────────

_NORMAL_MODE_SECTION = """\
═══════════════════════════════════════════════════════════════════════
MODE: STANDARD RETRIEVAL-AUGMENTED GENERATION
═══════════════════════════════════════════════════════════════════════
Use the CANDIDATE RECIPES below as strong inspiration.  You may combine, \
refine, or adapt them to best satisfy the constraints.  Add or substitute \
ingredients only when necessary; prefer using the user's available ingredients. \
Ensure the final recipe is coherent, well-balanced, and delicious."""

_ABSURD_MODE_SECTION = """\
═══════════════════════════════════════════════════════════════════════
MODE: ABSURD / AVANT-GARDE FUSION
═══════════════════════════════════════════════════════════════════════
IGNORE all candidate recipe references.  Instead, take the user's raw \
ingredient list — no matter how incompatible the items may seem — and \
invent a structurally sound, plausible, but WILDLY creative fusion recipe.
Think molecular gastronomy, deconstructed classics, unexpected flavor \
pairings.  The recipe must still be *physically cookable* and safe to eat, \
but push flavour boundaries aggressively.  Be inventive with technique."""


# ─────────────────────────────────────────────────────────────────────────────
# Builder Functions
# ─────────────────────────────────────────────────────────────────────────────

def _format_candidates(candidates: List[Dict]) -> str:
    """Format retrieved candidate recipes for injection into the prompt."""
    if not candidates:
        return (
            "No candidate recipes were found in the database for these constraints.\n"
            "Generate an original recipe from scratch using the available ingredients."
        )

    lines = ["═══════════════════════════════════════════════════════════════════════",
             "CANDIDATE RECIPES FROM DATABASE (use as inspiration):",
             "═══════════════════════════════════════════════════════════════════════"]
    for i, c in enumerate(candidates, 1):
        lines.append(f"\n--- Candidate {i}: {c.get('recipe_name', c.get('beverage_name', 'Unknown'))} ---")
        for key in ("cuisine", "meal_category", "skill_level", "total_time_min",
                     "equipment", "ingredients", "instructions", "type", "category"):
            if key in c and c[key]:
                lines.append(f"  {key}: {c[key]}")
    return "\n".join(lines)


def build_system_prompt(
    constraints: UserConstraints,
    candidates: List[Dict],
) -> str:
    """
    Assemble the complete system prompt with all dynamic injections.

    Args:
        constraints: Validated user constraints.
        candidates: Retrieved recipe/beverage candidates from the CSV pipeline.

    Returns:
        Fully formatted system prompt string.
    """
    mode_section = (
        _ABSURD_MODE_SECTION if constraints.absurd_combos
        else _NORMAL_MODE_SECTION
    )
    candidates_section = (
        "No candidate retrieval performed — absurd mode active."
        if constraints.absurd_combos
        else _format_candidates(candidates)
    )

    return SYSTEM_PROMPT_TEMPLATE.format(
        skill_level=constraints.skill_level.value,
        equipment=", ".join(constraints.available_equipment) or "Any",
        ingredients=", ".join(constraints.available_ingredients) or "Any",
        cuisine=constraints.cuisine_preference,
        meal_category=constraints.meal_category,
        max_prep_minutes=constraints.time_constraints.max_prep_minutes,
        max_total_minutes=constraints.time_constraints.max_total_minutes,
        servings=constraints.servings,
        json_schema=json.dumps(RECIPE_JSON_SCHEMA, indent=2),
        mode_section=mode_section,
        candidates_section=candidates_section,
    )


def build_user_prompt(constraints: UserConstraints) -> str:
    """
    Build the user-turn message.

    Kept simple — the system prompt carries most of the weight.
    """
    if constraints.absurd_combos:
        return (
            f"Create an avant-garde {constraints.meal_category.lower()} recipe "
            f"using these seemingly incompatible ingredients: "
            f"{', '.join(constraints.available_ingredients)}.  "
            f"Cuisine vibe: {constraints.cuisine_preference}.  "
            f"Make it surprising but edible.  Respond with JSON only."
        )

    return (
        f"Generate a {constraints.cuisine_preference} {constraints.meal_category.lower()} "
        f"recipe I can make in under {constraints.time_constraints.max_total_minutes} minutes "
        f"with these ingredients: {', '.join(constraints.available_ingredients)}.  "
        f"Respond with JSON only."
    )
