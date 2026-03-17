"""
engine.py — CulinaryEngine: the top-level orchestrator.

This class is the single entry point for the entire backend.  It:
  1. Validates and ingests user constraints.
  2. Runs the Pandas-based RAG retrieval pipeline.
  3. Constructs the engineered LLM prompt.
  4. Calls the OpenAI API (with absurd-mode temperature override).
  5. Parses and validates the JSON response via Pydantic.
  6. Computes offline nutritional values.
  7. Optionally translates display strings to the target language.

Usage:
    engine = CulinaryEngine()
    result = engine.generate(UserConstraints(...))
    # or async:
    result = await engine.agenerate(UserConstraints(...))
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI, OpenAI

from config import (
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_TEMPERATURE_HIGH,
    OPENAI_API_KEY,
)
from models import (
    GeneratedRecipe,
    RecipeNutritionReport,
    UserConstraints,
)
from nutrition import calculate_recipe_nutrition
from prompts import build_system_prompt, build_user_prompt
from retrieval import retrieve_beverage_pairing, retrieve_candidate_recipes
from translation import translate_display_strings, translate_display_strings_sync

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Result Container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GenerationResult:
    """Bundles all outputs from a single generation run."""
    recipe: GeneratedRecipe
    nutrition: RecipeNutritionReport
    translated_recipe: Optional[GeneratedRecipe] = None
    candidates_used: List[Dict] = field(default_factory=list)
    raw_llm_response: str = ""
    system_prompt: str = ""
    user_prompt: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the entire result to a JSON-safe dictionary."""
        return {
            "recipe": self.recipe.model_dump(),
            "nutrition": self.nutrition.model_dump(),
            "translated_recipe": (
                self.translated_recipe.model_dump()
                if self.translated_recipe else None
            ),
            "candidates_used_count": len(self.candidates_used),
            "system_prompt_preview": self.system_prompt[:300] + "…",
        }


# ─────────────────────────────────────────────────────────────────────────────
# JSON Parsing with Fallback
# ─────────────────────────────────────────────────────────────────────────────

def _extract_json(raw: str) -> Dict[str, Any]:
    """
    Extract a JSON object from the LLM's raw text output.

    Handles common edge cases:
      • Markdown code fences (```json ... ```)
      • Leading/trailing commentary
      • Multiple JSON blocks (takes the first valid one)
    """
    # Strip markdown fences
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    # Attempt direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: find the first { … } block
    brace_depth = 0
    start = None
    for i, ch in enumerate(cleaned):
        if ch == "{":
            if brace_depth == 0:
                start = i
            brace_depth += 1
        elif ch == "}":
            brace_depth -= 1
            if brace_depth == 0 and start is not None:
                candidate = cleaned[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    start = None  # try next block

    raise ValueError(
        f"Could not extract valid JSON from LLM response. "
        f"Raw output (first 500 chars): {raw[:500]}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CulinaryEngine
# ─────────────────────────────────────────────────────────────────────────────

class CulinaryEngine:
    """
    Production-grade culinary generation engine.

    Attributes:
        model: OpenAI model name for generation.
        api_key: OpenAI API key.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or LLM_MODEL

        if not self.api_key:
            logger.warning(
                "No OPENAI_API_KEY set. LLM calls will fail. "
                "Set it via env var or pass api_key= to CulinaryEngine()."
            )

        self._sync_client: Optional[OpenAI] = None
        self._async_client: Optional[AsyncOpenAI] = None

    # ── Lazy client init ─────────────────────────────────────────────────

    def _get_sync_client(self) -> OpenAI:
        if self._sync_client is None:
            self._sync_client = OpenAI(api_key=self.api_key)
        return self._sync_client

    def _get_async_client(self) -> AsyncOpenAI:
        if self._async_client is None:
            self._async_client = AsyncOpenAI(api_key=self.api_key)
        return self._async_client

    # ── Step 1: Retrieval ────────────────────────────────────────────────

    def _retrieve(self, constraints: UserConstraints) -> List[Dict]:
        """
        Run Pandas retrieval pipeline.
        Returns [] when absurd_combos is True (bypass mode).
        """
        if constraints.absurd_combos:
            logger.info("Absurd combos mode — bypassing CSV retrieval entirely.")
            return []

        candidates = retrieve_candidate_recipes(constraints)

        # Also retrieve beverage pairing candidates if not a beverage request
        if constraints.meal_category not in {
            "Cocktail", "Mocktail", "Coffee", "Tea", "Smoothie",
        }:
            bev_candidates = retrieve_beverage_pairing(constraints)
            # Attach as supplementary info to first candidate
            if bev_candidates and candidates:
                candidates[0]["_beverage_candidates"] = bev_candidates

        return candidates

    # ── Step 2: Prompt Construction ──────────────────────────────────────

    def _build_prompts(
        self, constraints: UserConstraints, candidates: List[Dict],
    ) -> tuple[str, str]:
        """Build system and user prompts."""
        system_prompt = build_system_prompt(constraints, candidates)
        user_prompt = build_user_prompt(constraints)
        return system_prompt, user_prompt

    # ── Step 3: LLM Call ─────────────────────────────────────────────────

    def _call_llm_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> str:
        """Synchronous OpenAI chat completion call."""
        client = self._get_sync_client()
        response = client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=LLM_MAX_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()

    async def _call_llm_async(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> str:
        """Asynchronous OpenAI chat completion call."""
        client = self._get_async_client()
        response = await client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=LLM_MAX_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()

    # ── Step 4: Parse & Validate ─────────────────────────────────────────

    @staticmethod
    def _parse_recipe(raw_json: str) -> GeneratedRecipe:
        """Parse raw LLM output into a validated GeneratedRecipe."""
        data = _extract_json(raw_json)
        return GeneratedRecipe.model_validate(data)

    # ── Step 5: Temperature Selection ────────────────────────────────────

    @staticmethod
    def _select_temperature(constraints: UserConstraints) -> float:
        """High temperature for absurd combos, normal otherwise."""
        return (
            LLM_TEMPERATURE_HIGH
            if constraints.absurd_combos
            else LLM_TEMPERATURE
        )

    # ── Main Synchronous Pipeline ────────────────────────────────────────

    def generate(self, constraints: UserConstraints) -> GenerationResult:
        """
        Full synchronous generation pipeline.

        Args:
            constraints: Validated UserConstraints object.

        Returns:
            GenerationResult with recipe, nutrition, and optional translation.

        Raises:
            ValueError: If LLM output cannot be parsed into valid JSON.
            openai.APIError: If the LLM API call fails.
        """
        logger.info("Starting generation pipeline (sync)")
        logger.info("Constraints: %s", constraints.model_dump_json(indent=2))

        # 1. Retrieval
        candidates = self._retrieve(constraints)
        logger.info("Retrieved %d candidate(s)", len(candidates))

        # 2. Prompt construction
        system_prompt, user_prompt = self._build_prompts(constraints, candidates)

        # 3. LLM call
        temperature = self._select_temperature(constraints)
        raw_response = self._call_llm_sync(system_prompt, user_prompt, temperature)
        logger.info("LLM response received (%d chars)", len(raw_response))

        # 4. Parse & validate
        recipe = self._parse_recipe(raw_response)
        logger.info("Parsed recipe: %s", recipe.recipe_name)

        # 5. Nutritional calculation (strictly offline)
        nutrition = calculate_recipe_nutrition(recipe)
        logger.info(
            "Nutrition calculated: %.0f kcal/serving",
            nutrition.per_serving.calories_kcal,
        )

        # 6. Translation (if needed)
        translated = None
        if constraints.target_language.lower() not in ("en", "eng", "english"):
            translated = translate_display_strings_sync(
                recipe, constraints.target_language,
            )
            logger.info("Translated to %s", constraints.target_language)

        return GenerationResult(
            recipe=recipe,
            nutrition=nutrition,
            translated_recipe=translated,
            candidates_used=candidates,
            raw_llm_response=raw_response,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    # ── Main Asynchronous Pipeline ───────────────────────────────────────

    async def agenerate(self, constraints: UserConstraints) -> GenerationResult:
        """
        Full asynchronous generation pipeline.

        Identical logic to generate() but uses async LLM calls and
        async translation.
        """
        logger.info("Starting generation pipeline (async)")

        # 1. Retrieval (CPU-bound Pandas work — runs in thread pool)
        loop = asyncio.get_running_loop()
        candidates = await loop.run_in_executor(
            None, self._retrieve, constraints,
        )

        # 2. Prompt construction
        system_prompt, user_prompt = self._build_prompts(constraints, candidates)

        # 3. LLM call
        temperature = self._select_temperature(constraints)
        raw_response = await self._call_llm_async(
            system_prompt, user_prompt, temperature,
        )

        # 4. Parse & validate
        recipe = self._parse_recipe(raw_response)

        # 5. Nutritional calculation
        nutrition = await loop.run_in_executor(
            None, calculate_recipe_nutrition, recipe,
        )

        # 6. Translation (async)
        translated = None
        if constraints.target_language.lower() not in ("en", "eng", "english"):
            translated = await translate_display_strings(
                recipe, constraints.target_language,
            )

        return GenerationResult(
            recipe=recipe,
            nutrition=nutrition,
            translated_recipe=translated,
            candidates_used=candidates,
            raw_llm_response=raw_response,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    # ── Nutrition-Only Mode (no LLM) ────────────────────────────────────

    @staticmethod
    def calculate_nutrition_only(
        recipe_json: Dict[str, Any],
    ) -> RecipeNutritionReport:
        """
        Calculate nutrition for an arbitrary recipe JSON dict
        without calling the LLM.  Useful for re-processing saved recipes.
        """
        recipe = GeneratedRecipe.model_validate(recipe_json)
        return calculate_recipe_nutrition(recipe)


class FlavorEngine(CulinaryEngine):
    """Backward-compatible alias matching the Flavor Fusion AI spec."""
