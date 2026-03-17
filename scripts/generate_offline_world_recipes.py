from __future__ import annotations

import csv
import random
from pathlib import Path


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "offline_world_recipes.csv"
RECIPE_COUNT = 20_000

CUISINE_PROFILES = {
    "Italian": {
        "proteins": ["chicken", "shrimp", "italian sausage", "white beans"],
        "bases": ["spaghetti", "penne", "risotto rice", "polenta"],
        "vegetables": ["tomato", "zucchini", "spinach", "eggplant", "mushroom"],
        "aromatics": ["garlic", "onion", "basil", "oregano"],
        "fats": ["olive oil", "butter"],
        "equipment": [["Stove"], ["Stove", "Oven"]],
    },
    "Mexican": {
        "proteins": ["chicken", "beef", "black beans", "pinto beans"],
        "bases": ["corn tortilla", "rice", "quinoa", "masa"],
        "vegetables": ["tomato", "onion", "bell pepper", "corn", "avocado"],
        "aromatics": ["garlic", "cilantro", "lime", "jalapeno"],
        "fats": ["olive oil", "avocado oil"],
        "equipment": [["Stove"], ["Stove", "Grill"], ["Oven", "Stove"]],
    },
    "Chinese": {
        "proteins": ["chicken", "tofu", "pork", "shrimp"],
        "bases": ["rice", "rice noodles", "egg noodles"],
        "vegetables": ["bok choy", "broccoli", "carrot", "mushroom", "bell pepper"],
        "aromatics": ["garlic", "ginger", "green onion", "soy sauce"],
        "fats": ["sesame oil", "vegetable oil"],
        "equipment": [["Wok", "Stove"], ["Stove"]],
    },
    "Japanese": {
        "proteins": ["salmon", "tofu", "chicken", "egg"],
        "bases": ["sushi rice", "udon", "soba", "rice"],
        "vegetables": ["cucumber", "carrot", "mushroom", "spinach", "daikon"],
        "aromatics": ["soy sauce", "ginger", "sesame seeds", "green onion"],
        "fats": ["sesame oil", "neutral oil"],
        "equipment": [["Stove"], ["Stove", "Oven"], ["Stove", "Blender"]],
    },
    "Thai": {
        "proteins": ["shrimp", "chicken", "tofu", "egg"],
        "bases": ["jasmine rice", "rice noodles", "coconut milk"],
        "vegetables": ["bell pepper", "mushroom", "baby corn", "snap peas", "tomato"],
        "aromatics": ["garlic", "ginger", "lime", "cilantro", "fish sauce"],
        "fats": ["coconut oil", "vegetable oil"],
        "equipment": [["Wok", "Stove"], ["Stove"]],
    },
    "French": {
        "proteins": ["chicken", "salmon", "egg", "white beans"],
        "bases": ["potato", "baguette", "lentils", "rice"],
        "vegetables": ["mushroom", "leek", "carrot", "spinach", "tomato"],
        "aromatics": ["garlic", "shallot", "thyme", "parsley"],
        "fats": ["butter", "olive oil"],
        "equipment": [["Stove"], ["Oven", "Stove"]],
    },
    "Mediterranean": {
        "proteins": ["chickpeas", "chicken", "feta cheese", "lamb"],
        "bases": ["couscous", "bulgur", "rice", "pita bread"],
        "vegetables": ["cucumber", "tomato", "eggplant", "zucchini", "olive"],
        "aromatics": ["garlic", "lemon", "oregano", "parsley"],
        "fats": ["olive oil"],
        "equipment": [["Stove"], ["Oven", "Stove"], []],
    },
    "American": {
        "proteins": ["chicken", "beef", "turkey", "black beans"],
        "bases": ["potato", "bread", "pasta", "rice"],
        "vegetables": ["tomato", "onion", "lettuce", "corn", "bell pepper"],
        "aromatics": ["garlic", "mustard", "pickle", "paprika"],
        "fats": ["butter", "olive oil"],
        "equipment": [["Stove"], ["Oven"], ["Grill", "Stove"]],
    },
    "Korean": {
        "proteins": ["beef", "chicken", "tofu", "egg"],
        "bases": ["rice", "sweet potato noodles", "lettuce wraps"],
        "vegetables": ["kimchi", "mushroom", "spinach", "cucumber", "carrot"],
        "aromatics": ["garlic", "ginger", "green onion", "soy sauce", "gochujang"],
        "fats": ["sesame oil", "neutral oil"],
        "equipment": [["Stove"], ["Stove", "Grill"]],
    },
    "Middle Eastern": {
        "proteins": ["chickpeas", "lamb", "chicken", "lentils"],
        "bases": ["rice", "pita bread", "bulgur", "couscous"],
        "vegetables": ["tomato", "cucumber", "eggplant", "onion", "spinach"],
        "aromatics": ["garlic", "lemon", "parsley", "cumin"],
        "fats": ["olive oil", "yogurt"],
        "equipment": [["Stove"], ["Oven", "Stove"], []],
    },
    "Ethiopian": {
        "proteins": ["lentils", "chicken", "chickpeas", "beef"],
        "bases": ["injera", "rice", "potato"],
        "vegetables": ["cabbage", "carrot", "tomato", "onion", "spinach"],
        "aromatics": ["garlic", "ginger", "berbere", "cilantro"],
        "fats": ["oil", "butter"],
        "equipment": [["Stove"], ["Stove", "Oven"]],
    },
    "Global": {
        "proteins": ["chicken", "tofu", "beans", "egg", "shrimp"],
        "bases": ["rice", "quinoa", "pasta", "potato"],
        "vegetables": ["tomato", "onion", "spinach", "bell pepper", "mushroom"],
        "aromatics": ["garlic", "lemon", "parsley", "paprika"],
        "fats": ["olive oil", "butter"],
        "equipment": [["Stove"], ["Oven", "Stove"], ["Air Fryer"]],
    },
}

MEAL_TEMPLATES = {
    "Breakfast": ["Skillet", "Scramble", "Hash", "Toast Bowl"],
    "Lunch": ["Bowl", "Salad", "Wrap", "Soup"],
    "Dinner": ["Roast", "Stir-Fry", "Pilaf", "Pasta"],
    "Snack": ["Bites", "Dip Plate", "Cups", "Toast"],
    "Dessert": ["Compote", "Pudding", "Bake", "Crumble"],
    "Appetizer": ["Skewers", "Crostini", "Spoons", "Small Plate"],
    "Side Dish": ["Pilaf", "Roasted Mix", "Greens", "Mash"],
}

SKILL_BY_MEAL = {
    "Breakfast": ["Beginner", "Intermediate"],
    "Lunch": ["Beginner", "Intermediate"],
    "Dinner": ["Intermediate", "Pro"],
    "Snack": ["Beginner", "Intermediate"],
    "Dessert": ["Intermediate", "Pro"],
    "Appetizer": ["Beginner", "Intermediate", "Pro"],
    "Side Dish": ["Beginner", "Intermediate"],
}

MEAL_CATEGORIES = list(MEAL_TEMPLATES)


def ingredient_amount(name: str, category: str, rng: random.Random) -> str:
    lower = name.lower()
    if any(token in lower for token in ["oil", "sauce", "juice", "milk", "broth", "water", "yogurt"]):
        return f"{rng.randint(15, 180)}ml"
    if lower in {"egg", "eggs"}:
        return str(rng.randint(1, 4))
    if any(token in lower for token in ["salt", "pepper", "paprika", "cumin", "oregano", "thyme", "parsley", "basil", "berbere", "gochujang"]):
        return f"{rng.randint(2, 12)}g"
    if category == "Dessert":
        return f"{rng.randint(20, 220)}g"
    return f"{rng.randint(30, 320)}g"


def build_row(recipe_id: int, cuisine: str, meal_category: str, rng: random.Random) -> dict[str, str]:
    profile = CUISINE_PROFILES[cuisine]
    style = rng.choice(MEAL_TEMPLATES[meal_category])
    protein = rng.choice(profile["proteins"])
    base = rng.choice(profile["bases"])
    vegetables = rng.sample(profile["vegetables"], k=2)
    aromatics = rng.sample(profile["aromatics"], k=2)
    fat = rng.choice(profile["fats"])
    recipe_name = f"{cuisine} {protein.title()} {style} {recipe_id}"
    skill_level = rng.choice(SKILL_BY_MEAL[meal_category])
    prep_time = rng.randint(5, 35)
    total_time = prep_time + rng.randint(5, 55)
    equipment = rng.choice(profile["equipment"])
    ingredient_names = [protein, base, *vegetables, *aromatics, fat, "salt", "black pepper"]
    ingredients = ",".join(
        f"{name}:{ingredient_amount(name, meal_category, rng)}"
        for name in ingredient_names
    )
    instructions = "|".join([
        f"Prep {protein} and {base} for the {style.lower()}",
        f"Cook {aromatics[0]} and {aromatics[1]} with {fat} until fragrant",
        f"Add {protein}, {vegetables[0]}, and {vegetables[1]} and cook until tender",
        f"Fold in {base} and season with salt and black pepper",
        f"Adjust texture and finish in {', '.join(equipment) if equipment else 'a serving bowl'}",
        f"Serve the {recipe_name.lower()} warm",
    ])
    return {
        "recipe_id": str(recipe_id),
        "recipe_name": recipe_name,
        "cuisine": cuisine,
        "meal_category": meal_category,
        "skill_level": skill_level,
        "prep_time_min": str(prep_time),
        "total_time_min": str(total_time),
        "equipment": ",".join(equipment),
        "ingredients": ingredients,
        "instructions": instructions,
    }


def main() -> None:
    rng = random.Random(20260317)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "recipe_id",
                "recipe_name",
                "cuisine",
                "meal_category",
                "skill_level",
                "prep_time_min",
                "total_time_min",
                "equipment",
                "ingredients",
                "instructions",
            ],
        )
        writer.writeheader()
        cuisines = list(CUISINE_PROFILES)
        for recipe_id in range(1, RECIPE_COUNT + 1):
            cuisine = cuisines[(recipe_id - 1) % len(cuisines)]
            meal_category = MEAL_CATEGORIES[(recipe_id - 1) % len(MEAL_CATEGORIES)]
            writer.writerow(build_row(recipe_id, cuisine, meal_category, rng))

    print(f"Generated {RECIPE_COUNT} recipes at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()