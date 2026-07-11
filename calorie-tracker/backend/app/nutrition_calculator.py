"""Nutrition target calculations optimized for sustainable fat loss and muscle retention."""

from typing import Optional, Tuple


class NutritionCalculator:
    MACRO_DISTRIBUTIONS = {
        "none": (0.30, 0.40, 0.30),
        "vegetarian": (0.28, 0.42, 0.30),
        "vegan": (0.25, 0.45, 0.30),
        "keto": (0.25, 0.05, 0.70),
        "high_protein": (0.40, 0.30, 0.30),
        "low_carb": (0.35, 0.20, 0.45),
    }

    ACTIVITY_MULTIPLIERS = {
        "sedentary": 1.2,
        "lightly_active": 1.375,
        "moderately_active": 1.55,
        "very_active": 1.725,
        "extremely_active": 1.9,
    }

    @staticmethod
    def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
        base_bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
        if gender.lower() == "male":
            bmr = base_bmr + 5
        elif gender.lower() == "female":
            bmr = base_bmr - 161
        else:
            bmr = base_bmr - 78
        return round(bmr, 2)

    @staticmethod
    def calculate_tdee(bmr: float, activity_level: str) -> float:
        return round(bmr * NutritionCalculator.ACTIVITY_MULTIPLIERS.get(activity_level, 1.2), 2)

    @staticmethod
    def calculate_target_calories(tdee: float, goal: str, bmr: float | None = None) -> int:
        if goal == "weight_loss":
            deficit = min(max(round(tdee * 0.18), 300), 650)
            floor = round((bmr or tdee / 1.2) * 1.05)
            return max(floor, round(tdee - deficit))
        if goal == "muscle_gain":
            return round(tdee + min(300, max(150, tdee * 0.08)))
        return round(tdee)

    @staticmethod
    def calculate_macros(
        target_calories: int,
        dietary_preference: str = "none",
        *,
        weight_kg: float | None = None,
        goal: str = "maintenance",
    ) -> Tuple[int, int, int]:
        if weight_kg:
            protein_multiplier = 1.8 if goal == "weight_loss" else 2.0 if goal == "muscle_gain" else 1.6
            if dietary_preference == "vegan":
                protein_multiplier += 0.1
            protein_g = round(weight_kg * protein_multiplier)
            fat_g = round(weight_kg * (0.8 if dietary_preference != "keto" else 1.4))
            if dietary_preference == "low_carb":
                fat_g = round(weight_kg * 1.0)
            protein_g = min(protein_g, round(target_calories * 0.40 / 4))
            fat_g = min(fat_g, round(target_calories * 0.45 / 9))
            remaining = max(target_calories - protein_g * 4 - fat_g * 9, 0)
            carbs_g = round(remaining / 4)
            if dietary_preference == "keto":
                carbs_g = min(carbs_g, 35)
                remaining_after_carbs = max(target_calories - protein_g * 4 - carbs_g * 4, 0)
                fat_g = round(remaining_after_carbs / 9)
            return protein_g, carbs_g, fat_g

        protein_pct, carbs_pct, fat_pct = NutritionCalculator.MACRO_DISTRIBUTIONS.get(
            dietary_preference, NutritionCalculator.MACRO_DISTRIBUTIONS["none"]
        )
        return (
            round(target_calories * protein_pct / 4),
            round(target_calories * carbs_pct / 4),
            round(target_calories * fat_pct / 9),
        )

    @staticmethod
    def calculate_fiber_target(target_calories: int, age: int, gender: str) -> int:
        fiber_base = round((target_calories / 1000) * 14)
        if age < 50:
            minimum = 25 if gender.lower() == "female" else 38 if gender.lower() == "male" else 30
        else:
            minimum = 21 if gender.lower() == "female" else 30 if gender.lower() == "male" else 25
        return max(fiber_base, minimum)

    @staticmethod
    def calculate_all_targets(
        weight_kg: float,
        height_cm: float,
        age: int,
        gender: str,
        activity_level: str = "sedentary",
        goal: str = "maintenance",
        dietary_preference: str = "none",
        custom_calories: Optional[int] = None,
        custom_protein_g: Optional[int] = None,
        custom_carbs_g: Optional[int] = None,
        custom_fats_g: Optional[int] = None,
        custom_fiber_g: Optional[int] = None,
    ) -> dict:
        bmr = NutritionCalculator.calculate_bmr(weight_kg, height_cm, age, gender)
        tdee = NutritionCalculator.calculate_tdee(bmr, activity_level)
        if custom_calories is not None:
            target_calories = custom_calories
            method = "custom"
        else:
            target_calories = NutritionCalculator.calculate_target_calories(tdee, goal, bmr)
            method = "adaptive_formula"

        protein_g, carbs_g, fats_g = NutritionCalculator.calculate_macros(
            target_calories,
            dietary_preference,
            weight_kg=weight_kg,
            goal=goal,
        )
        if custom_protein_g is not None:
            protein_g = custom_protein_g
            method = "custom"
        if custom_carbs_g is not None:
            carbs_g = custom_carbs_g
            method = "custom"
        if custom_fats_g is not None:
            fats_g = custom_fats_g
            method = "custom"
        fiber_g = custom_fiber_g if custom_fiber_g is not None else NutritionCalculator.calculate_fiber_target(target_calories, age, gender)
        if custom_fiber_g is not None:
            method = "custom"

        return {
            "bmr": bmr,
            "tdee": tdee,
            "target_calories": target_calories,
            "target_protein_g": protein_g,
            "target_carbs_g": carbs_g,
            "target_fats_g": fats_g,
            "target_fiber_g": fiber_g,
            "calculation_method": method,
            "activity_level": activity_level,
            "goal": goal,
            "dietary_preference": dietary_preference,
        }

    @staticmethod
    def get_activity_level_description(activity_level: str) -> str:
        descriptions = {
            "sedentary": "Little or no exercise",
            "lightly_active": "Light exercise 1-3 days/week",
            "moderately_active": "Moderate exercise 3-5 days/week",
            "very_active": "Hard exercise 6-7 days/week",
            "extremely_active": "Very hard exercise and physical job",
        }
        return descriptions.get(activity_level, "Unknown activity level")

    @staticmethod
    def get_goal_description(goal: str) -> str:
        descriptions = {
            "weight_loss": "Weight loss with an approximately 18% energy deficit",
            "maintenance": "Weight maintenance",
            "muscle_gain": "Muscle gain with a small energy surplus",
        }
        return descriptions.get(goal, "Unknown goal")
