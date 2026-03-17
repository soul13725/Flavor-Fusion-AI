"""
translation.py — Multilingual Decoupling Layer.

All core LLM reasoning and ingredient JSON is produced in English (mandatory
for the nutritional matcher).  This module provides an asynchronous helper
that translates *only the display strings* — recipe title, step-by-step
instructions, and beverage instructions — into the user's target language.

Architecture:
  • Uses a lightweight LLM call (gpt-4o-mini by default) for translation.
  • Runs asynchronously so the main pipeline can fire-and-forget.
  • Falls back gracefully to English on any error.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from config import OPENAI_API_KEY, TRANSLATION_MODEL, LLM_MAX_TOKENS
from models import GeneratedRecipe

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Async OpenAI Client (lazy init)
# ─────────────────────────────────────────────────────────────────────────────

_async_client: Optional[AsyncOpenAI] = None


def _get_async_client() -> AsyncOpenAI:
    global _async_client
    if _async_client is None:
        _async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _async_client


# ─────────────────────────────────────────────────────────────────────────────
# Language Code → Display Name Mapping
# ─────────────────────────────────────────────────────────────────────────────

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "ru": "Russian",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "ur": "Urdu",
    "th": "Thai",
    "vi": "Vietnamese",
    "tr": "Turkish",
    "nl": "Dutch",
    "pl": "Polish",
    "sv": "Swedish",
}


# ─────────────────────────────────────────────────────────────────────────────
# Translation Prompt
# ─────────────────────────────────────────────────────────────────────────────

_TRANSLATION_SYSTEM_PROMPT = """\
You are a professional culinary translator.  Translate the following JSON \
fields into {target_language}.

RULES:
1. Translate ONLY the values — never change JSON keys.
2. Do NOT translate ingredient names — leave them in English.
3. Translate: recipe_name, step_by_step_instructions, beverage_pairing.name, \
   beverage_pairing.instructions.
4. Keep all numeric values and units unchanged.
5. Respond with ONLY the translated JSON object — no markdown, no commentary.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Core Async Translation Function
# ─────────────────────────────────────────────────────────────────────────────

async def translate_display_strings(
    recipe: GeneratedRecipe,
    target_language: str,
) -> GeneratedRecipe:
    """
    Translate user-facing display strings in a GeneratedRecipe to the target
    language while preserving English ingredient names.

    Args:
        recipe: The fully validated GeneratedRecipe (English).
        target_language: ISO 639-1 language code (e.g. 'hi', 'es', 'fr').

    Returns:
        A new GeneratedRecipe with translated display fields.
        Falls back to the original English recipe on any error.
    """
    # No-op for English
    if target_language.lower() in ("en", "eng", "english"):
        return recipe

    lang_name = LANGUAGE_NAMES.get(
        target_language.lower(), target_language,
    )

    # Build a minimal payload of only translatable fields
    translatable = {
        "recipe_name": recipe.recipe_name,
        "step_by_step_instructions": recipe.step_by_step_instructions,
    }
    if recipe.beverage_pairing:
        translatable["beverage_pairing"] = {
            "name": recipe.beverage_pairing.name,
            "instructions": recipe.beverage_pairing.instructions,
        }

    system_msg = _TRANSLATION_SYSTEM_PROMPT.format(target_language=lang_name)

    try:
        client = _get_async_client()
        response = await client.chat.completions.create(
            model=TRANSLATION_MODEL,
            temperature=0.3,  # low creativity for translation
            max_tokens=LLM_MAX_TOKENS,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": json.dumps(translatable, ensure_ascii=False)},
            ],
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if the model wraps them
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        translated = json.loads(raw)

        # Merge translated fields back into a copy of the recipe
        recipe_dict = recipe.model_dump()
        recipe_dict["recipe_name"] = translated.get(
            "recipe_name", recipe.recipe_name,
        )
        recipe_dict["step_by_step_instructions"] = translated.get(
            "step_by_step_instructions", recipe.step_by_step_instructions,
        )

        if recipe.beverage_pairing and "beverage_pairing" in translated:
            bp = translated["beverage_pairing"]
            recipe_dict["beverage_pairing"]["name"] = bp.get(
                "name", recipe.beverage_pairing.name,
            )
            recipe_dict["beverage_pairing"]["instructions"] = bp.get(
                "instructions", recipe.beverage_pairing.instructions,
            )

        return GeneratedRecipe.model_validate(recipe_dict)

    except json.JSONDecodeError as exc:
        logger.error("Translation JSON parse failed: %s", exc)
        return recipe
    except Exception as exc:
        logger.error("Translation API call failed: %s", exc)
        return recipe


# ─────────────────────────────────────────────────────────────────────────────
# Synchronous Convenience Wrapper
# ─────────────────────────────────────────────────────────────────────────────

def translate_display_strings_sync(
    recipe: GeneratedRecipe,
    target_language: str,
) -> GeneratedRecipe:
    """
    Blocking wrapper around the async translation function,
    safe to call from non-async contexts.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already inside an event loop (e.g. Jupyter) — schedule as task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(
                asyncio.run,
                translate_display_strings(recipe, target_language),
            ).result()
    else:
        return asyncio.run(
            translate_display_strings(recipe, target_language),
        )
