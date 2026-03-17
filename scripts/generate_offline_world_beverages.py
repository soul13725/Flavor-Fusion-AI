from __future__ import annotations

import csv
import random
from pathlib import Path


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "offline_world_beverages.csv"
BEVERAGE_COUNT = 5000

PROFILES = {
    "Cocktail": {
        "regions": ["Latin", "Mediterranean", "Nordic", "Asian", "Tropical"],
        "base": ["vodka", "gin", "rum", "tequila", "whiskey"],
        "mixers": ["lime juice", "lemon juice", "orange juice", "tonic water", "soda water", "ginger beer"],
        "flavors": ["mint", "basil", "cucumber", "pineapple", "berry syrup", "passion fruit"],
        "equipment": [["Blender"], ["Blender", "Stove"], []],
    },
    "Mocktail": {
        "regions": ["Indian", "Middle Eastern", "Caribbean", "European", "Global"],
        "base": ["sparkling water", "coconut water", "apple juice", "pineapple juice", "orange juice"],
        "mixers": ["lime juice", "lemon juice", "mint", "ginger", "rose syrup", "honey"],
        "flavors": ["mango", "watermelon", "cucumber", "pomegranate", "strawberry", "basil"],
        "equipment": [["Blender"], [], ["Stove"]],
    },
    "Coffee": {
        "regions": ["Italian", "Vietnamese", "Latin", "Nordic", "Global"],
        "base": ["espresso", "cold brew coffee", "drip coffee", "instant coffee"],
        "mixers": ["milk", "almond milk", "oat milk", "condensed milk", "water"],
        "flavors": ["cinnamon", "vanilla syrup", "cardamom", "cocoa", "brown sugar", "ice"],
        "equipment": [["Espresso Machine"], ["Blender"], []],
    },
    "Tea": {
        "regions": ["Indian", "Chinese", "Japanese", "Moroccan", "British"],
        "base": ["black tea", "green tea", "oolong tea", "matcha powder", "herbal tea"],
        "mixers": ["milk", "hot water", "lemon juice", "mint", "honey"],
        "flavors": ["ginger", "cardamom", "cinnamon", "rose petals", "orange peel", "ice"],
        "equipment": [["Stove"], ["Blender"], []],
    },
    "Smoothie": {
        "regions": ["Tropical", "Mediterranean", "American", "Asian", "African"],
        "base": ["yogurt", "milk", "almond milk", "coconut water"],
        "mixers": ["banana", "mango", "berries", "pineapple", "spinach", "oats"],
        "flavors": ["chia seeds", "honey", "peanut butter", "cocoa", "mint", "ginger"],
        "equipment": [["Blender"]],
    },
}


def amount(name: str, rng: random.Random) -> str:
    lower = name.lower()
    if any(token in lower for token in ["water", "juice", "milk", "coffee", "tea", "espresso", "syrup"]):
        return f"{rng.randint(20, 300)}ml"
    if any(token in lower for token in ["ice", "banana", "mango", "pineapple", "berries", "cucumber"]):
        return f"{rng.randint(20, 220)}g"
    if any(token in lower for token in ["mint", "basil", "ginger", "cardamom", "cinnamon", "cocoa", "chia"]):
        return f"{rng.randint(2, 20)}g"
    return f"{rng.randint(5, 90)}g"


def build_row(beverage_id: int, category: str, rng: random.Random) -> dict[str, str]:
    profile = PROFILES[category]
    region = rng.choice(profile["regions"])
    base = rng.choice(profile["base"])
    mixers = rng.sample(profile["mixers"], k=2)
    flavors = rng.sample(profile["flavors"], k=2)
    equipment = rng.choice(profile["equipment"])
    skill_level = rng.choice(["Beginner", "Intermediate", "Pro"] if category == "Cocktail" else ["Beginner", "Intermediate"])
    prep = rng.randint(5, 20)
    total = prep + rng.randint(0, 15)
    beverage_name = f"{region} {base.title()} {category} {beverage_id}"
    ingredients = [base, *mixers, *flavors]
    instructions = "|".join([
        f"Prepare the glassware for the {beverage_name.lower()}",
        f"Combine {base} with {mixers[0]} and {mixers[1]}",
        f"Add {flavors[0]} and {flavors[1]} and mix until balanced",
        f"Finish using {', '.join(equipment) if equipment else 'a serving glass'}",
        f"Serve the {beverage_name.lower()} immediately",
    ])
    return {
        "beverage_id": str(beverage_id),
        "beverage_name": beverage_name,
        "type": category,
        "category": category,
        "skill_level": skill_level,
        "prep_time_min": str(prep),
        "total_time_min": str(total),
        "equipment": ",".join(equipment),
        "ingredients": ",".join(f"{name}:{amount(name, rng)}" for name in ingredients),
        "instructions": instructions,
    }


def main() -> None:
    rng = random.Random(20260317)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    categories = list(PROFILES)

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "beverage_id",
                "beverage_name",
                "type",
                "category",
                "skill_level",
                "prep_time_min",
                "total_time_min",
                "equipment",
                "ingredients",
                "instructions",
            ],
        )
        writer.writeheader()
        for beverage_id in range(1, BEVERAGE_COUNT + 1):
            writer.writerow(build_row(beverage_id, categories[(beverage_id - 1) % len(categories)], rng))

    print(f"Generated {BEVERAGE_COUNT} beverages at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()