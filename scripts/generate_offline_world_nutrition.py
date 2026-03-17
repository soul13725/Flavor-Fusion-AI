from __future__ import annotations

import csv
from pathlib import Path


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "offline_world_nutrition.csv"

ROWS = [
    ["vodka", "beverage", 231, 0.0, 0.0, 0.0, 0.0, 0.0, 1, 100],
    ["gin", "beverage", 263, 0.0, 0.0, 0.0, 0.0, 0.0, 2, 100],
    ["rum", "beverage", 231, 0.0, 0.0, 0.0, 0.0, 0.0, 1, 100],
    ["tequila", "beverage", 231, 0.0, 0.0, 0.0, 0.0, 0.0, 1, 100],
    ["whiskey", "beverage", 250, 0.0, 0.0, 0.1, 0.0, 0.0, 1, 100],
    ["tonic water", "beverage", 34, 0.0, 0.0, 8.8, 0.0, 8.8, 12, 100],
    ["soda water", "beverage", 0, 0.0, 0.0, 0.0, 0.0, 0.0, 4, 100],
    ["ginger beer", "beverage", 37, 0.0, 0.0, 9.0, 0.0, 8.7, 8, 100],
    ["sparkling water", "beverage", 0, 0.0, 0.0, 0.0, 0.0, 0.0, 5, 100],
    ["coconut water", "beverage", 19, 0.7, 0.2, 3.7, 1.1, 2.6, 105, 100],
    ["apple juice", "beverage", 46, 0.1, 0.1, 11.3, 0.2, 9.6, 4, 100],
    ["orange juice", "beverage", 45, 0.7, 0.2, 10.4, 0.2, 8.4, 1, 100],
    ["pineapple juice", "beverage", 53, 0.4, 0.1, 12.9, 0.2, 10.0, 1, 100],
    ["rose syrup", "beverage", 260, 0.0, 0.0, 65.0, 0.0, 64.0, 15, 100],
    ["berry syrup", "beverage", 240, 0.1, 0.0, 60.0, 0.2, 58.0, 12, 100],
    ["passion fruit", "fruit", 97, 2.2, 0.7, 23.4, 10.4, 11.2, 28, 100],
    ["mint", "herb", 44, 3.3, 0.7, 8.4, 6.8, 0.0, 31, 10],
    ["basil", "herb", 23, 3.2, 0.6, 2.7, 1.6, 0.3, 4, 10],
    ["cucumber", "vegetable", 15, 0.7, 0.1, 3.6, 0.5, 1.7, 2, 100],
    ["pineapple", "fruit", 50, 0.5, 0.1, 13.1, 1.4, 9.9, 1, 100],
    ["espresso", "beverage", 9, 0.1, 0.2, 1.7, 0.0, 0.0, 14, 30],
    ["cold brew coffee", "beverage", 2, 0.1, 0.0, 0.0, 0.0, 0.0, 5, 100],
    ["drip coffee", "beverage", 1, 0.1, 0.0, 0.0, 0.0, 0.0, 2, 100],
    ["instant coffee", "beverage", 353, 12.2, 0.5, 75.4, 0.0, 0.0, 37, 100],
    ["almond milk", "beverage", 15, 0.6, 1.2, 0.3, 0.2, 0.0, 47, 100],
    ["oat milk", "beverage", 46, 1.0, 1.5, 6.7, 0.8, 3.2, 40, 100],
    ["condensed milk", "dairy", 321, 7.9, 8.7, 54.4, 0.0, 54.4, 127, 100],
    ["black tea", "beverage", 1, 0.0, 0.0, 0.3, 0.0, 0.0, 4, 100],
    ["green tea", "beverage", 1, 0.2, 0.0, 0.0, 0.0, 0.0, 1, 100],
    ["oolong tea", "beverage", 1, 0.0, 0.0, 0.2, 0.0, 0.0, 3, 100],
    ["matcha powder", "beverage", 324, 30.6, 5.3, 38.5, 38.5, 0.0, 6, 100],
    ["herbal tea", "beverage", 1, 0.0, 0.0, 0.2, 0.0, 0.0, 1, 100],
    ["rose petals", "herb", 162, 1.7, 0.3, 37.0, 24.1, 2.2, 8, 100],
    ["orange peel", "fruit", 97, 1.5, 0.2, 25.0, 10.6, 1.7, 3, 100],
    ["banana", "fruit", 89, 1.1, 0.3, 22.8, 2.6, 12.2, 1, 100],
    ["berries", "fruit", 57, 0.7, 0.3, 14.5, 2.4, 10.0, 1, 100],
    ["spinach", "vegetable", 23, 2.9, 0.4, 3.6, 2.2, 0.4, 79, 100],
    ["oats", "grain", 389, 16.9, 6.9, 66.3, 10.6, 0.9, 2, 100],
    ["chia seeds", "seed", 486, 16.5, 30.7, 42.1, 34.4, 0.0, 16, 100],
    ["peanut butter", "spread", 588, 25.0, 50.0, 20.0, 6.0, 9.0, 426, 100],
    ["cocoa", "powder", 228, 19.6, 13.7, 57.9, 37.0, 1.8, 21, 100],
    ["brown sugar", "sweetener", 380, 0.0, 0.0, 98.1, 0.0, 97.0, 28, 100],
    ["honey", "sweetener", 304, 0.3, 0.0, 82.4, 0.2, 82.1, 4, 100],
    ["lime juice", "fruit", 25, 0.4, 0.1, 8.4, 0.4, 1.7, 2, 100],
    ["lemon juice", "fruit", 22, 0.4, 0.2, 6.9, 0.3, 2.5, 1, 100],
    ["ginger", "spice", 80, 1.8, 0.8, 17.8, 2.0, 1.7, 13, 100],
    ["cardamom", "spice", 311, 10.8, 6.7, 68.5, 28.0, 0.0, 18, 100],
    ["cinnamon", "spice", 247, 4.0, 1.2, 80.6, 53.1, 2.2, 10, 100],
    ["ice", "beverage", 0, 0.0, 0.0, 0.0, 0.0, 0.0, 1, 100],
    ["pomegranate", "fruit", 83, 1.7, 1.2, 18.7, 4.0, 13.7, 3, 100],
    ["watermelon", "fruit", 30, 0.6, 0.2, 7.6, 0.4, 6.2, 1, 100],
    ["strawberry", "fruit", 32, 0.7, 0.3, 7.7, 2.0, 4.9, 1, 100],
    ["vanilla syrup", "sweetener", 278, 0.0, 0.0, 69.0, 0.0, 68.0, 25, 100],
]


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "food_name",
            "category",
            "calories_per_100g",
            "protein_per_100g",
            "fat_per_100g",
            "carbs_per_100g",
            "fiber_per_100g",
            "sugar_per_100g",
            "sodium_per_100g",
            "unit_weight_grams",
        ])
        writer.writerows(ROWS)
    print(f"Generated {len(ROWS)} nutrition entries at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()