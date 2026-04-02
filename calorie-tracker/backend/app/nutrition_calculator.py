"""
Nutrition calculator utilities for BMR, TDEE, and macronutrient recommendations.
Uses Mifflin-St Jeor equation for BMR calculation and established nutritional guidelines.
"""
from typing import Tuple, Optional


class NutritionCalculator:
    """Calculate nutritional requirements based on user profile."""
    
    # Activity level multipliers for TDEE calculation
    ACTIVITY_MULTIPLIERS = {
        "sedentary": 1.2,           # Little or no exercise
        "lightly_active": 1.375,    # Light exercise 1-3 days/week
        "moderately_active": 1.55,  # Moderate exercise 3-5 days/week
        "very_active": 1.725,       # Hard exercise 6-7 days/week
        "extremely_active": 1.9     # Very hard exercise & physical job
    }
    
    # Goal adjustments (calories per day)
    GOAL_ADJUSTMENTS = {
        "weight_loss": -500,      # 500 calorie deficit
        "maintenance": 0,         # No adjustment
        "muscle_gain": 300        # 300 calorie surplus
    }
    
    # Macronutrient distributions by dietary preference (% of calories)
    # Format: (protein%, carbs%, fat%)
    MACRO_DISTRIBUTIONS = {
        "none": (0.30, 0.40, 0.30),          # Balanced
        "vegetarian": (0.25, 0.45, 0.30),    # Slightly higher carbs
        "vegan": (0.20, 0.50, 0.30),         # Higher carbs for plant-based
        "keto": (0.25, 0.05, 0.70),          # Very low carb, high fat
        "high_protein": (0.40, 0.30, 0.30),  # High protein
        "low_carb": (0.35, 0.20, 0.45)       # Low carb, higher fat
    }
    
    @staticmethod
    def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
        """
        Calculate Basal Metabolic Rate using Mifflin-St Jeor Equation.
        
        This is considered one of the most accurate equations for BMR calculation.
        
        Args:
            weight_kg: Weight in kilograms
            height_cm: Height in centimeters
            age: Age in years
            gender: 'male', 'female', or 'other'
        
        Returns:
            BMR in calories per day
        """
        # Mifflin-St Jeor Equation
        # Men: BMR = (10 × weight in kg) + (6.25 × height in cm) - (5 × age in years) + 5
        # Women: BMR = (10 × weight in kg) + (6.25 × height in cm) - (5 × age in years) - 161
        
        base_bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
        
        if gender.lower() == "male":
            bmr = base_bmr + 5
        elif gender.lower() == "female":
            bmr = base_bmr - 161
        else:
            # For 'other', use average of male and female
            bmr = base_bmr - 78
        
        return round(bmr, 2)
    
    @staticmethod
    def calculate_tdee(bmr: float, activity_level: str) -> float:
        """
        Calculate Total Daily Energy Expenditure.
        
        Args:
            bmr: Basal Metabolic Rate
            activity_level: Activity level string
        
        Returns:
            TDEE in calories per day
        """
        multiplier = NutritionCalculator.ACTIVITY_MULTIPLIERS.get(
            activity_level, 
            1.2  # Default to sedentary
        )
        return round(bmr * multiplier, 2)
    
    @staticmethod
    def calculate_target_calories(tdee: float, goal: str) -> int:
        """
        Calculate target daily calories based on goal.
        
        Args:
            tdee: Total Daily Energy Expenditure
            goal: Fitness goal ('weight_loss', 'maintenance', 'muscle_gain')
        
        Returns:
            Target calories per day
        """
        adjustment = NutritionCalculator.GOAL_ADJUSTMENTS.get(goal, 0)
        return round(tdee + adjustment)
    
    @staticmethod
    def calculate_macros(
        target_calories: int, 
        dietary_preference: str = "none"
    ) -> Tuple[int, int, int]:
        """
        Calculate macronutrient targets in grams.
        
        Args:
            target_calories: Target daily calories
            dietary_preference: Dietary preference affecting macro distribution
        
        Returns:
            Tuple of (protein_g, carbs_g, fats_g)
        """
        # Get macro distribution percentages
        protein_pct, carbs_pct, fat_pct = NutritionCalculator.MACRO_DISTRIBUTIONS.get(
            dietary_preference,
            (0.30, 0.40, 0.30)  # Default balanced
        )
        
        # Calculate calories for each macro
        protein_calories = target_calories * protein_pct
        carbs_calories = target_calories * carbs_pct
        fat_calories = target_calories * fat_pct
        
        # Convert to grams
        # Protein: 4 cal/g, Carbs: 4 cal/g, Fat: 9 cal/g
        protein_g = round(protein_calories / 4)
        carbs_g = round(carbs_calories / 4)
        fats_g = round(fat_calories / 9)
        
        return (protein_g, carbs_g, fats_g)
    
    @staticmethod
    def calculate_fiber_target(target_calories: int, age: int, gender: str) -> int:
        """
        Calculate recommended daily fiber intake.
        
        Based on dietary guidelines: 14g per 1000 calories,
        with minimums of 25g for women and 38g for men.
        
        Args:
            target_calories: Target daily calories
            age: Age in years
            gender: Gender
        
        Returns:
            Target fiber in grams
        """
        # Base calculation: 14g per 1000 calories
        fiber_base = round((target_calories / 1000) * 14)
        
        # Apply minimums based on gender (for adults under 50)
        if age < 50:
            if gender.lower() == "female":
                fiber_min = 25
            elif gender.lower() == "male":
                fiber_min = 38
            else:
                fiber_min = 30  # Average for 'other'
        else:
            # Slightly lower for 50+
            if gender.lower() == "female":
                fiber_min = 21
            elif gender.lower() == "male":
                fiber_min = 30
            else:
                fiber_min = 25
        
        return max(fiber_base, fiber_min)
    
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
        custom_fiber_g: Optional[int] = None
    ) -> dict:
        """
        Calculate all nutritional targets for a user profile.
        
        Returns:
            Dictionary with all calculated values and metadata
        """
        # Calculate BMR and TDEE
        bmr = NutritionCalculator.calculate_bmr(weight_kg, height_cm, age, gender)
        tdee = NutritionCalculator.calculate_tdee(bmr, activity_level)
        
        # Use custom calories if provided, otherwise calculate
        if custom_calories is not None:
            target_calories = custom_calories
            calculation_method = "custom"
        else:
            target_calories = NutritionCalculator.calculate_target_calories(tdee, goal)
            calculation_method = "calculated"
        
        # Calculate macros (use custom if provided)
        if custom_protein_g is not None and custom_carbs_g is not None and custom_fats_g is not None:
            protein_g = custom_protein_g
            carbs_g = custom_carbs_g
            fats_g = custom_fats_g
            calculation_method = "custom"
        else:
            protein_g, carbs_g, fats_g = NutritionCalculator.calculate_macros(
                target_calories, dietary_preference
            )
            if custom_protein_g is not None:
                protein_g = custom_protein_g
            if custom_carbs_g is not None:
                carbs_g = custom_carbs_g
            if custom_fats_g is not None:
                fats_g = custom_fats_g
        
        # Calculate fiber target (use custom if provided)
        if custom_fiber_g is not None:
            fiber_g = custom_fiber_g
        else:
            fiber_g = NutritionCalculator.calculate_fiber_target(
                target_calories, age, gender
            )
        
        return {
            "bmr": bmr,
            "tdee": tdee,
            "target_calories": target_calories,
            "target_protein_g": protein_g,
            "target_carbs_g": carbs_g,
            "target_fats_g": fats_g,
            "target_fiber_g": fiber_g,
            "calculation_method": calculation_method,
            "activity_level": activity_level,
            "goal": goal,
            "dietary_preference": dietary_preference
        }
    
    @staticmethod
    def get_activity_level_description(activity_level: str) -> str:
        """Get human-readable description of activity level."""
        descriptions = {
            "sedentary": "Little or no exercise",
            "lightly_active": "Light exercise 1-3 days/week",
            "moderately_active": "Moderate exercise 3-5 days/week",
            "very_active": "Hard exercise 6-7 days/week",
            "extremely_active": "Very hard exercise & physical job"
        }
        return descriptions.get(activity_level, "Unknown activity level")
    
    @staticmethod
    def get_goal_description(goal: str) -> str:
        """Get human-readable description of goal."""
        descriptions = {
            "weight_loss": "Weight Loss (-500 cal/day deficit)",
            "maintenance": "Weight Maintenance (no deficit/surplus)",
            "muscle_gain": "Muscle Gain (+300 cal/day surplus)"
        }
        return descriptions.get(goal, "Unknown goal")