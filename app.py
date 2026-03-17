"""
app.py — Streamlit frontend for Flavor Fusion AI.

Layout:
  • Sidebar  : theme toggle, language, API key, all user constraints
  • Main     : ingredient input, generate button, recipe / nutrition / beverage tabs

Dark mode is implemented by injecting custom CSS overrides via st.markdown and
caching the preference in st.session_state so it persists across reruns.

Multilingual support: all UI labels are served from UI_STRINGS; the LLM
always reasons in English (ingredient names stay English for the nutrition
engine), but display strings are translated to the chosen language.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

# ── Ensure project root is importable (handles stlite and direct `streamlit run`)
sys.path.insert(0, str(Path(__file__).parent))

from config import VALID_EQUIPMENT, VALID_CUISINES, VALID_MEAL_CATEGORIES
from database import RecipeDatabase
from engine import CulinaryEngine
from models import TimeConstraints, UserConstraints

# ─────────────────────────────────────────────────────────────────────────────
# UI Label Translations
# ─────────────────────────────────────────────────────────────────────────────

UI_STRINGS: dict = {
    "en": {
        "title": "🍽️ Flavor Fusion AI",
        "subtitle": "Your AI-powered culinary & mixology assistant",
        "api_key_label": "OpenAI API Key",
        "api_key_help": "Used only for this session. Never stored.",
        "language_label": "Output Language",
        "skill_label": "Skill Level",
        "equipment_label": "Available Equipment",
        "cuisine_label": "Cuisine Preference",
        "meal_label": "Meal Category",
        "prep_time_label": "Max Prep Time (min)",
        "total_time_label": "Max Total Time (min)",
        "servings_label": "Servings",
        "absurd_label": "🎲 Absurd Mode",
        "absurd_help": "Invent a wildly creative fusion dish — logic optional.",
        "ingredients_label": "🥦 Your Pantry Ingredients",
        "ingredients_placeholder": "chicken breast\nonion\ngarlic\ntomato\nyogurt\ncream\nrice",
        "ingredients_help": "One ingredient per line. Be specific for better results.",
        "generate_btn": "✨ Generate Recipe",
        "generating": "🔥 Cooking up something amazing…",
        "no_ingredients": "⚠️ Please add at least one ingredient.",
        "no_api_key": "🔑 Please enter your OpenAI API Key in the sidebar.",
        "recipe_tab": "🍽️ Recipe",
        "nutrition_tab": "📊 Nutrition",
        "beverage_tab": "🥂 Beverage Pairing",
        "debug_tab": "🔍 Debug",
        "ingredients_header": "Ingredients",
        "instructions_header": "Instructions",
        "per_serving": "Per Serving",
        "total_header": "Total",
        "calories": "Calories (kcal)",
        "protein": "Protein (g)",
        "fat": "Fat (g)",
        "carbs": "Carbs (g)",
        "fiber": "Fiber (g)",
        "sugar": "Sugar (g)",
        "sodium": "Sodium (mg)",
        "unmatched": "⚠️ Unmatched ingredients (excluded from totals)",
        "dark_mode": "🌙 Dark Mode",
        "db_stats": "📂 Database",
        "recipes_in_db": "recipes in DB",
        "beverages_in_db": "beverages in DB",
        "nutrition_entries": "nutrition entries",
        "error_prefix": "❌ Generation failed",
        "cuisine_badge": "🌍 {c}",
        "time_badge": "⏱️ {min} min",
        "servings_badge": "👥 {n} serving(s)",
        "equipment_badge": "🔧 {eq}",
        "candidates_used": "Candidates retrieved from DB",
        "raw_prompt_preview": "System prompt preview",
    },
    "hi": {
        "title": "🍽️ फ्लेवर फ्यूज़न AI",
        "subtitle": "आपका AI-संचालित पाक और मिक्सोलॉजी सहायक",
        "api_key_label": "OpenAI API कुंजी",
        "api_key_help": "केवल इस सत्र के लिए उपयोग की जाती है।",
        "language_label": "आउटपुट भाषा",
        "skill_label": "कौशल स्तर",
        "equipment_label": "उपलब्ध उपकरण",
        "cuisine_label": "व्यंजन प्राथमिकता",
        "meal_label": "भोजन श्रेणी",
        "prep_time_label": "अधिकतम तैयारी समय (मिनट)",
        "total_time_label": "अधिकतम कुल समय (मिनट)",
        "servings_label": "सर्विंग्स",
        "absurd_label": "🎲 बेतुका मोड",
        "absurd_help": "सभी तर्क को नजरअंदाज करते हुए एक जंगली फ्यूजन डिश।",
        "ingredients_label": "🥦 आपकी पैंट्री सामग्री",
        "ingredients_placeholder": "चिकन ब्रेस्ट\nप्याज\nलहसुन\nटमाटर\nदही",
        "ingredients_help": "प्रति पंक्ति एक सामग्री।",
        "generate_btn": "✨ रेसिपी बनाएं",
        "generating": "🔥 कुछ अद्भुत पका रहे हैं…",
        "no_ingredients": "⚠️ कृपया कम से कम एक सामग्री जोड़ें।",
        "no_api_key": "🔑 कृपया साइडबार में OpenAI API कुंजी दर्ज करें।",
        "recipe_tab": "🍽️ रेसिपी",
        "nutrition_tab": "📊 पोषण",
        "beverage_tab": "🥂 पेय पदार्थ",
        "debug_tab": "🔍 डीबग",
        "ingredients_header": "सामग्री",
        "instructions_header": "निर्देश",
        "per_serving": "प्रति सर्विंग",
        "total_header": "कुल",
        "calories": "कैलोरी (kcal)",
        "protein": "प्रोटीन (g)",
        "fat": "वसा (g)",
        "carbs": "कार्ब्स (g)",
        "fiber": "फाइबर (g)",
        "sugar": "चीनी (g)",
        "sodium": "सोडियम (mg)",
        "unmatched": "⚠️ असंबद्ध सामग्री (कुल से बाहर)",
        "dark_mode": "🌙 डार्क मोड",
        "db_stats": "📂 डेटाबेस",
        "recipes_in_db": "रेसिपी डेटाबेस में",
        "beverages_in_db": "पेय डेटाबेस में",
        "nutrition_entries": "पोषण प्रविष्टियाँ",
        "error_prefix": "❌ जनरेशन विफल",
        "cuisine_badge": "🌍 {c}",
        "time_badge": "⏱️ {min} मिनट",
        "servings_badge": "👥 {n} सर्विंग्स",
        "equipment_badge": "🔧 {eq}",
        "candidates_used": "DB से पुनर्प्राप्त उम्मीदवार",
        "raw_prompt_preview": "सिस्टम प्रॉम्प्ट पूर्वावलोकन",
    },
    "it": {
        "title": "🍽️ Flavor Fusion AI",
        "subtitle": "Il tuo assistente culinario e mixologico alimentato dall'AI",
        "api_key_label": "Chiave API OpenAI",
        "api_key_help": "Usata solo per questa sessione.",
        "language_label": "Lingua di output",
        "skill_label": "Livello di abilità",
        "equipment_label": "Attrezzatura disponibile",
        "cuisine_label": "Preferenza culinaria",
        "meal_label": "Categoria del pasto",
        "prep_time_label": "Tempo max di preparazione (min)",
        "total_time_label": "Tempo totale massimo (min)",
        "servings_label": "Porzioni",
        "absurd_label": "🎲 Modalità Assurda",
        "absurd_help": "Inventa un piatto fusion selvaggiamente creativo.",
        "ingredients_label": "🥦 Ingredienti nella tua dispensa",
        "ingredients_placeholder": "petto di pollo\ncipolla\naglio\npomodoro\nyogurt",
        "ingredients_help": "Un ingrediente per riga.",
        "generate_btn": "✨ Genera Ricetta",
        "generating": "🔥 Preparando qualcosa di straordinario…",
        "no_ingredients": "⚠️ Aggiungi almeno un ingrediente.",
        "no_api_key": "🔑 Inserisci la chiave API OpenAI nella barra laterale.",
        "recipe_tab": "🍽️ Ricetta",
        "nutrition_tab": "📊 Nutrizione",
        "beverage_tab": "🥂 Abbinamento bevanda",
        "debug_tab": "🔍 Debug",
        "ingredients_header": "Ingredienti",
        "instructions_header": "Istruzioni",
        "per_serving": "Per porzione",
        "total_header": "Totale",
        "calories": "Calorie (kcal)",
        "protein": "Proteine (g)",
        "fat": "Grassi (g)",
        "carbs": "Carboidrati (g)",
        "fiber": "Fibre (g)",
        "sugar": "Zucchero (g)",
        "sodium": "Sodio (mg)",
        "unmatched": "⚠️ Ingredienti non trovati (esclusi dai totali)",
        "dark_mode": "🌙 Modalità scura",
        "db_stats": "📂 Database",
        "recipes_in_db": "ricette nel DB",
        "beverages_in_db": "bevande nel DB",
        "nutrition_entries": "voci nutrizionali",
        "error_prefix": "❌ Generazione fallita",
        "cuisine_badge": "🌍 {c}",
        "time_badge": "⏱️ {min} min",
        "servings_badge": "👥 {n} porzione/i",
        "equipment_badge": "🔧 {eq}",
        "candidates_used": "Candidati recuperati dal DB",
        "raw_prompt_preview": "Anteprima del prompt di sistema",
    },
    "zh": {
        "title": "🍽️ 风味融合 AI",
        "subtitle": "您的 AI 驱动烹饪和调酒助手",
        "api_key_label": "OpenAI API 密钥",
        "api_key_help": "仅在本次会话中使用，不会被存储。",
        "language_label": "输出语言",
        "skill_label": "技能等级",
        "equipment_label": "可用设备",
        "cuisine_label": "菜系偏好",
        "meal_label": "餐点类别",
        "prep_time_label": "最长准备时间（分钟）",
        "total_time_label": "最长总时间（分钟）",
        "servings_label": "份数",
        "absurd_label": "🎲 荒诞模式",
        "absurd_help": "无视所有逻辑，发明一道极具创意的融合菜。",
        "ingredients_label": "🥦 您的食材清单",
        "ingredients_placeholder": "鸡胸肉\n洋葱\n大蒜\n番茄\n酸奶",
        "ingredients_help": "每行一种食材。",
        "generate_btn": "✨ 生成食谱",
        "generating": "🔥 正在烹饪美味…",
        "no_ingredients": "⚠️ 请至少添加一种食材。",
        "no_api_key": "🔑 请在侧边栏输入 OpenAI API 密钥。",
        "recipe_tab": "🍽️ 食谱",
        "nutrition_tab": "📊 营养信息",
        "beverage_tab": "🥂 饮品搭配",
        "debug_tab": "🔍 调试",
        "ingredients_header": "食材",
        "instructions_header": "烹饪步骤",
        "per_serving": "每份",
        "total_header": "总计",
        "calories": "卡路里 (kcal)",
        "protein": "蛋白质 (g)",
        "fat": "脂肪 (g)",
        "carbs": "碳水化合物 (g)",
        "fiber": "膳食纤维 (g)",
        "sugar": "糖 (g)",
        "sodium": "钠 (mg)",
        "unmatched": "⚠️ 未匹配食材（不计入总量）",
        "dark_mode": "🌙 深色模式",
        "db_stats": "📂 数据库",
        "recipes_in_db": "条食谱",
        "beverages_in_db": "条饮品",
        "nutrition_entries": "条营养数据",
        "error_prefix": "❌ 生成失败",
        "cuisine_badge": "🌍 {c}",
        "time_badge": "⏱️ {min} 分钟",
        "servings_badge": "👥 {n} 份",
        "equipment_badge": "🔧 {eq}",
        "candidates_used": "从数据库检索到的候选数",
        "raw_prompt_preview": "系统提示预览",
    },
}

LANGUAGE_OPTIONS: dict = {
    "English": "en",
    "हिन्दी (Hindi)": "hi",
    "Italiano (Italian)": "it",
    "中文 (Mandarin)": "zh",
}

# ─────────────────────────────────────────────────────────────────────────────
# Theme CSS Injection
# ─────────────────────────────────────────────────────────────────────────────

_DARK_CSS = """
<style>
/* ── Dark Mode Overrides ── */
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
[data-testid="stSidebar"] {
    background-color: #0f0f23 !important;
    color: #e2e2f0 !important;
}
[data-testid="stSidebar"] {
    background-color: #16213e !important;
}
.stMarkdown, .stText, label, p, h1, h2, h3, h4 {
    color: #e2e2f0 !important;
}
.stTextArea textarea, .stTextInput input, .stSelectbox select {
    background-color: #1a1a3e !important;
    color: #e2e2f0 !important;
    border-color: #4a4a7a !important;
}
.stButton > button {
    background: linear-gradient(135deg, #6c63ff, #e040fb) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #5a52e0, #c832e8) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(108, 99, 255, 0.4) !important;
}
[data-testid="metric-container"] {
    background-color: #1a1a3e !important;
    border: 1px solid #4a4a7a !important;
    border-radius: 8px !important;
    padding: 12px !important;
}
.stTabs [data-baseweb="tab-list"] {
    background-color: #16213e !important;
}
.stTabs [data-baseweb="tab"] {
    color: #a0a0d0 !important;
}
.stTabs [aria-selected="true"] {
    color: #e2e2f0 !important;
    border-bottom-color: #6c63ff !important;
}
.recipe-card {
    background-color: #1a1a3e !important;
    border: 1px solid #4a4a7a !important;
}
</style>
"""

_LIGHT_CSS = """
<style>
/* ── Light Mode Overrides ── */
[data-testid="stAppViewContainer"] {
    background-color: #fafafa !important;
}
[data-testid="stSidebar"] {
    background-color: #f0f2f6 !important;
}
.stButton > button {
    background: linear-gradient(135deg, #6c63ff, #e040fb) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(108, 99, 255, 0.3) !important;
}
[data-testid="metric-container"] {
    border-radius: 8px !important;
    border: 1px solid #e0e0e0 !important;
}
</style>
"""

_BASE_CSS = """
<style>
/* ── Shared Styles ── */
.recipe-card {
    border-radius: 12px;
    padding: 1.2rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-right: 6px;
    background: rgba(108, 99, 255, 0.15);
    color: #6c63ff;
    border: 1px solid rgba(108, 99, 255, 0.3);
}
.ingredient-row {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    border-bottom: 1px solid rgba(128,128,128,0.1);
}
.step-number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: linear-gradient(135deg, #6c63ff, #e040fb);
    color: white;
    font-size: 0.8rem;
    font-weight: 700;
    flex-shrink: 0;
    margin-right: 10px;
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Session State Initialisation
# ─────────────────────────────────────────────────────────────────────────────

def _init_session_state() -> None:
    defaults = {
        "dark_mode": False,
        "language": "en",
        "api_key": "",
        "last_result": None,
        "last_constraints": None,
        "pantry_text": (
            "chicken breast\nonion\ngarlic\ntomato\nyogurt\ncream\nrice\ncilantro"
        ),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _t(key: str) -> str:
    """Look up a UI string in the active language."""
    lang = st.session_state.get("language", "en")
    return UI_STRINGS.get(lang, UI_STRINGS["en"]).get(
        key, UI_STRINGS["en"].get(key, key)
    )


def _apply_theme() -> None:
    """Inject theme CSS and attempt to set the Streamlit config option."""
    st.markdown(_BASE_CSS, unsafe_allow_html=True)
    if st.session_state.dark_mode:
        st.markdown(_DARK_CSS, unsafe_allow_html=True)
        try:
            st._config.set_option("theme.base", "dark")
            st._config.set_option("theme.backgroundColor", "#0f0f23")
            st._config.set_option("theme.secondaryBackgroundColor", "#16213e")
            st._config.set_option("theme.textColor", "#e2e2f0")
        except Exception:
            pass  # Internal API may not be available in all versions
    else:
        st.markdown(_LIGHT_CSS, unsafe_allow_html=True)
        try:
            st._config.set_option("theme.base", "light")
        except Exception:
            pass


def _parse_ingredients(raw: str) -> list[str]:
    """Split textarea input into a clean list of ingredient strings."""
    return [
        line.strip()
        for line in raw.splitlines()
        if line.strip()
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

def _render_sidebar() -> dict:
    """
    Render the sidebar and return a dict of all user-selected constraint values.
    """
    with st.sidebar:
        # ── Theme toggle ───────────────────────────────────────────────────
        dark = st.toggle(_t("dark_mode"), value=st.session_state.dark_mode)
        if dark != st.session_state.dark_mode:
            st.session_state.dark_mode = dark
            st.rerun()

        st.divider()

        # ── Language selector ──────────────────────────────────────────────
        lang_label = st.selectbox(
            _t("language_label"),
            options=list(LANGUAGE_OPTIONS.keys()),
            index=list(LANGUAGE_OPTIONS.values()).index(
                st.session_state.language
            ),
        )
        new_lang = LANGUAGE_OPTIONS[lang_label]
        if new_lang != st.session_state.language:
            st.session_state.language = new_lang
            st.rerun()

        st.divider()

        # ── API key ────────────────────────────────────────────────────────
        api_key = st.text_input(
            _t("api_key_label"),
            type="password",
            value=st.session_state.api_key,
            help=_t("api_key_help"),
        )
        st.session_state.api_key = api_key

        st.divider()

        # ── Skill level ────────────────────────────────────────────────────
        skill = st.selectbox(
            _t("skill_label"),
            options=["Beginner", "Intermediate", "Pro"],
            index=1,
        )

        # ── Equipment ─────────────────────────────────────────────────────
        equipment = st.multiselect(
            _t("equipment_label"),
            options=sorted(VALID_EQUIPMENT),
            default=["Stove", "Oven", "Blender"],
        )

        # ── Cuisine ────────────────────────────────────────────────────────
        cuisine = st.selectbox(
            _t("cuisine_label"),
            options=sorted(VALID_CUISINES),
            index=sorted(VALID_CUISINES).index("Indian"),
        )

        # ── Meal category ──────────────────────────────────────────────────
        meal_cat = st.selectbox(
            _t("meal_label"),
            options=sorted(VALID_MEAL_CATEGORIES),
            index=sorted(VALID_MEAL_CATEGORIES).index("Dinner"),
        )

        # ── Time constraints ───────────────────────────────────────────────
        max_prep = st.slider(_t("prep_time_label"), 5, 120, 30, step=5)
        max_total = st.slider(_t("total_time_label"), 10, 240, 60, step=10)

        # ── Servings ───────────────────────────────────────────────────────
        servings = st.number_input(
            _t("servings_label"), min_value=1, max_value=12, value=2
        )

        # ── Absurd mode ────────────────────────────────────────────────────
        absurd = st.toggle(_t("absurd_label"), help=_t("absurd_help"))

        st.divider()

        # ── DB statistics ──────────────────────────────────────────────────
        with st.expander(_t("db_stats"), expanded=False):
            try:
                db = RecipeDatabase()
                stats = db.get_stats()
                st.metric(_t("recipes_in_db"), f"{stats['recipes']:,}")
                st.metric(_t("beverages_in_db"), f"{stats['beverages']:,}")
                st.metric(_t("nutrition_entries"), f"{stats['nutrition_entries']:,}")
            except Exception as exc:
                st.caption(f"DB unavailable: {exc}")

    return {
        "skill": skill,
        "equipment": equipment,
        "cuisine": cuisine,
        "meal_category": meal_cat,
        "max_prep": max_prep,
        "max_total": max_total,
        "servings": servings,
        "absurd": absurd,
        "api_key": api_key,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Recipe Card Renderer
# ─────────────────────────────────────────────────────────────────────────────

def _render_recipe_tab(recipe, lang: str) -> None:
    """Render the recipe information inside the Recipe tab."""
    # Display the translated recipe if available, otherwise the English one
    display = recipe

    # Header badges
    badges = "".join([
        f'<span class="badge">{_t("time_badge").format(min=display.estimated_time_minutes)}</span>',
        f'<span class="badge">{_t("servings_badge").format(n=display.servings)}</span>',
        f'<span class="badge">{_t("cuisine_badge").format(c=display.cuisine_type)}</span>',
    ])
    if display.equipment_used:
        badges += f'<span class="badge">{_t("equipment_badge").format(eq=", ".join(display.equipment_used))}</span>'
    st.markdown(badges, unsafe_allow_html=True)
    st.markdown("")

    # Ingredients
    st.markdown(f"### {_t('ingredients_header')}")
    for ing in display.ingredients:
        note = f" *({ing.preparation_note})*" if ing.preparation_note else ""
        cols = st.columns([3, 2, 2])
        cols[0].markdown(f"**{ing.name}**{note}")
        cols[1].markdown(f"`{ing.quantity_grams}g`")
        cols[2].markdown(f"_{ing.original_measure}_")

    st.divider()

    # Instructions
    st.markdown(f"### {_t('instructions_header')}")
    for i, step in enumerate(display.step_by_step_instructions, 1):
        st.markdown(
            f'<div style="display:flex;align-items:flex-start;margin-bottom:10px;">'
            f'<span class="step-number">{i}</span>'
            f'<span style="padding-top:4px">{step}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_nutrition_tab(nutrition) -> None:
    """Render the nutritional breakdown inside the Nutrition tab."""
    ps = nutrition.per_serving
    total = nutrition.total

    st.markdown(f"#### {_t('per_serving')}")
    cols = st.columns(4)
    cols[0].metric(_t("calories"), f"{ps.calories_kcal:.0f}")
    cols[1].metric(_t("protein"), f"{ps.protein_g:.1f}")
    cols[2].metric(_t("fat"), f"{ps.fat_g:.1f}")
    cols[3].metric(_t("carbs"), f"{ps.carbs_g:.1f}")

    cols2 = st.columns(3)
    cols2[0].metric(_t("fiber"), f"{ps.fiber_g:.1f}")
    cols2[1].metric(_t("sugar"), f"{ps.sugar_g:.1f}")
    cols2[2].metric(_t("sodium"), f"{ps.sodium_mg:.0f} mg")

    st.divider()
    st.markdown(f"#### {_t('total_header')} ({nutrition.servings} servings)")
    cols3 = st.columns(4)
    cols3[0].metric(_t("calories"), f"{total.calories_kcal:.0f}")
    cols3[1].metric(_t("protein"), f"{total.protein_g:.1f}")
    cols3[2].metric(_t("fat"), f"{total.fat_g:.1f}")
    cols3[3].metric(_t("carbs"), f"{total.carbs_g:.1f}")

    if nutrition.ingredient_breakdown:
        st.divider()
        st.markdown("#### Ingredient Breakdown")
        import pandas as pd
        rows = [
            {
                "Ingredient": ib.ingredient_name,
                "DB Match": ib.matched_db_name,
                "Confidence": f"{ib.match_confidence}%",
                "Grams": ib.quantity_grams,
                "kcal": ib.nutrients.calories_kcal,
                "Protein g": ib.nutrients.protein_g,
                "Fat g": ib.nutrients.fat_g,
                "Carbs g": ib.nutrients.carbs_g,
            }
            for ib in nutrition.ingredient_breakdown
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    if nutrition.unmatched_ingredients:
        st.warning(
            _t("unmatched") + ": " + ", ".join(nutrition.unmatched_ingredients)
        )


def _render_beverage_tab(recipe) -> None:
    """Render beverage pairing inside the Beverage tab."""
    display = recipe
    bp = display.beverage_pairing
    if not bp:
        st.info("No beverage pairing was generated.")
        return

    st.markdown(f"## {bp.name}")
    st.caption(f"Type: **{bp.type}**")
    st.divider()

    st.markdown(f"### {_t('ingredients_header')}")
    for ing in bp.ingredients:
        cols = st.columns([3, 2, 2])
        cols[0].markdown(f"**{ing.name}**")
        cols[1].markdown(f"`{ing.quantity_grams}g`")
        cols[2].markdown(f"_{ing.original_measure}_")

    st.divider()
    st.markdown(f"### {_t('instructions_header')}")
    for i, step in enumerate(bp.instructions, 1):
        st.markdown(
            f'<div style="display:flex;align-items:flex-start;margin-bottom:10px;">'
            f'<span class="step-number">{i}</span>'
            f'<span style="padding-top:4px">{step}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_debug_tab(result) -> None:
    """Render debug information for developers."""
    st.metric(_t("candidates_used"), len(result.candidates_used))
    with st.expander(_t("raw_prompt_preview")):
        st.code(result.system_prompt[:600] + "\n…", language="text")
    with st.expander("Raw LLM Response"):
        st.code(result.raw_llm_response[:800], language="json")
    with st.expander("Full Result JSON"):
        st.json(result.to_dict())


# ─────────────────────────────────────────────────────────────────────────────
# Generation Logic
# ─────────────────────────────────────────────────────────────────────────────

def _run_generation(ingredients: list[str], sidebar_vals: dict) -> None:
    """Build constraints, call CulinaryEngine.generate(), store in session state."""
    constraints = UserConstraints(
        skill_level=sidebar_vals["skill"],
        available_equipment=sidebar_vals["equipment"],
        available_ingredients=ingredients,
        cuisine_preference=sidebar_vals["cuisine"],
        time_constraints=TimeConstraints(
            max_prep_minutes=sidebar_vals["max_prep"],
            max_total_minutes=sidebar_vals["max_total"],
        ),
        meal_category=sidebar_vals["meal_category"],
        absurd_combos=sidebar_vals["absurd"],
        target_language=st.session_state.language,
        servings=sidebar_vals["servings"],
    )

    engine = CulinaryEngine(api_key=sidebar_vals["api_key"])

    with st.spinner(_t("generating")):
        result = engine.generate(constraints)

    st.session_state.last_result = result
    st.session_state.last_constraints = constraints


# ─────────────────────────────────────────────────────────────────────────────
# Main App
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Flavor Fusion AI",
        page_icon="🍽️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _init_session_state()
    _apply_theme()

    # ── Sidebar ──────────────────────────────────────────────────────────────
    sidebar_vals = _render_sidebar()

    # ── Main header ──────────────────────────────────────────────────────────
    st.title(_t("title"))
    st.caption(_t("subtitle"))
    st.divider()

    # ── Ingredient input ─────────────────────────────────────────────────────
    col_input, col_generate = st.columns([3, 1], gap="large")

    with col_input:
        pantry_raw = st.text_area(
            _t("ingredients_label"),
            value=st.session_state.pantry_text,
            height=180,
            placeholder=_t("ingredients_placeholder"),
            help=_t("ingredients_help"),
        )
        st.session_state.pantry_text = pantry_raw

    with col_generate:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

        if sidebar_vals["absurd"]:
            st.info("🎲 Absurd Mode ON — expect the unexpected!")

        generate_clicked = st.button(
            _t("generate_btn"),
            use_container_width=True,
            type="primary",
        )

    # ── Validation ───────────────────────────────────────────────────────────
    if generate_clicked:
        ingredients = _parse_ingredients(pantry_raw)
        if not ingredients:
            st.warning(_t("no_ingredients"))
        elif not sidebar_vals["api_key"]:
            st.warning(_t("no_api_key"))
        else:
            try:
                _run_generation(ingredients, sidebar_vals)
            except Exception as exc:
                st.error(f"{_t('error_prefix')}: {exc}")

    # ── Results ──────────────────────────────────────────────────────────────
    result = st.session_state.get("last_result")
    if result is not None:
        st.divider()

        # Determine which recipe to display (translated or English)
        display_recipe = result.translated_recipe or result.recipe

        st.markdown(f"## {display_recipe.recipe_name}")

        tab_recipe, tab_nutrition, tab_beverage, tab_debug = st.tabs([
            _t("recipe_tab"),
            _t("nutrition_tab"),
            _t("beverage_tab"),
            _t("debug_tab"),
        ])

        with tab_recipe:
            _render_recipe_tab(display_recipe, st.session_state.language)

        with tab_nutrition:
            _render_nutrition_tab(result.nutrition)

        with tab_beverage:
            _render_beverage_tab(display_recipe)

        with tab_debug:
            _render_debug_tab(result)


if __name__ == "__main__":
    main()
