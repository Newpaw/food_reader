# Personal Profile & Nutritional Recommendations System

## Overview

This comprehensive personal profile system captures user biometric data and calculates personalized daily nutritional intake recommendations using established formulas like the Mifflin-St Jeor equation.

## Features

### 1. User Profile Management
- **Biometric Data Collection**:
  - Height (cm)
  - Weight (kg)
  - Age (years)
  - Gender (male/female/other)

- **Activity Level Configuration**:
  - Sedentary - Little or no exercise
  - Lightly Active - Light exercise 1-3 days/week
  - Moderately Active - Moderate exercise 3-5 days/week
  - Very Active - Hard exercise 6-7 days/week
  - Extremely Active - Very hard exercise & physical job

- **Fitness Goals**:
  - Weight Loss (-500 cal/day deficit)
  - Weight Maintenance (no deficit/surplus)
  - Muscle Gain (+300 cal/day surplus)

- **Dietary Preferences**:
  - Balanced (30% protein, 40% carbs, 30% fat)
  - High Protein (40% protein, 30% carbs, 30% fat)
  - Low Carb (35% protein, 20% carbs, 45% fat)
  - Keto (25% protein, 5% carbs, 70% fat)
  - Vegetarian (25% protein, 45% carbs, 30% fat)
  - Vegan (20% protein, 50% carbs, 30% fat)

### 2. Nutritional Calculations

#### Basal Metabolic Rate (BMR)
Uses the **Mifflin-St Jeor Equation**, considered one of the most accurate:
- **Men**: BMR = (10 × weight_kg) + (6.25 × height_cm) - (5 × age) + 5
- **Women**: BMR = (10 × weight_kg) + (6.25 × height_cm) - (5 × age) - 161
- **Other**: Average of male and female formulas

#### Total Daily Energy Expenditure (TDEE)
BMR multiplied by activity level factor:
- Sedentary: 1.2
- Lightly Active: 1.375
- Moderately Active: 1.55
- Very Active: 1.725
- Extremely Active: 1.9

#### Target Calories
TDEE adjusted for fitness goal:
- Weight Loss: TDEE - 500 calories
- Maintenance: TDEE
- Muscle Gain: TDEE + 300 calories

#### Macronutrient Distribution
Calculated based on dietary preference:
- **Protein**: 4 calories/gram
- **Carbohydrates**: 4 calories/gram
- **Fats**: 9 calories/gram

#### Fiber Recommendations
Based on 14g per 1000 calories, with minimums:
- Women <50: 25g minimum
- Men <50: 38g minimum
- Women 50+: 21g minimum
- Men 50+: 30g minimum

### 3. Custom Targets
Users can override automatic calculations with custom values from healthcare professionals:
- Custom daily calories
- Custom protein (g)
- Custom carbohydrates (g)
- Custom fats (g)
- Custom fiber (g)

### 4. Visual Progress Tracking

The metrics dashboard displays:
- **Nutritional Targets Section**: Shows recommended daily intake
- **Progress Comparison**: Visual progress bars comparing actual vs target
- **Color-Coded Status**:
  - 🟢 Green (Success): 90-110% of target
  - 🟡 Yellow (Warning): 70-90% or 110-130% of target
  - 🔴 Red (Danger): <70% or >130% of target

## API Endpoints

### Profile Management

#### GET `/profile`
Get the current user's profile
- **Response**: `UserProfileOut`

#### POST `/profile`
Create a new profile
- **Request Body**: `UserProfileCreate`
- **Response**: `UserProfileOut`
- **Status**: 201 Created

#### PUT `/profile`
Update existing profile
- **Request Body**: `UserProfileUpdate`
- **Response**: `UserProfileOut`

#### DELETE `/profile`
Delete user profile
- **Status**: 204 No Content

#### GET `/profile/targets`
Get calculated nutritional targets
- **Response**: `NutritionTargets` with:
  - calories
  - protein_g
  - carbs_g
  - fats_g
  - fiber_g
  - calculation_method
  - bmr
  - tdee
  - last_updated

#### GET `/profile/activity-levels`
Get available activity levels with descriptions

#### GET `/profile/goals`
Get available fitness goals with descriptions

#### GET `/profile/dietary-preferences`
Get available dietary preferences with macro distributions

## Database Schema

### user_profiles Table
```sql
CREATE TABLE user_profiles (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    height_cm FLOAT,
    weight_kg FLOAT,
    age INTEGER,
    gender VARCHAR,
    activity_level VARCHAR DEFAULT 'sedentary',
    goal VARCHAR DEFAULT 'maintenance',
    dietary_preference VARCHAR DEFAULT 'none',
    custom_calories INTEGER,
    custom_protein_g INTEGER,
    custom_carbs_g INTEGER,
    custom_fats_g INTEGER,
    custom_fiber_g INTEGER,
    bmr FLOAT,
    tdee FLOAT,
    target_calories INTEGER,
    target_protein_g INTEGER,
    target_carbs_g INTEGER,
    target_fats_g INTEGER,
    target_fiber_g INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## Frontend Pages

### profile.html
- Complete profile management interface
- Form validation for realistic value ranges
- Display of calculated targets
- Calculation methodology transparency
- Last updated timestamps

### metrics.html (Enhanced)
- Nutritional targets display
- Daily progress vs targets comparison
- Visual progress bars with color coding
- Percentage indicators
- Status messages (below/met/exceeded)

## Usage Flow

1. **Create Profile**: User fills in biometric data, activity level, goal, and dietary preference
2. **Automatic Calculation**: System calculates BMR, TDEE, and target macros
3. **View Targets**: User sees personalized nutritional recommendations
4. **Track Progress**: Metrics page shows actual intake vs targets with visual indicators
5. **Update Profile**: User can update data as needed (weight changes, activity level, etc.)

## Validation

All inputs are validated with realistic ranges:
- Height: 50-300 cm
- Weight: 20-500 kg
- Age: 10-120 years
- Gender: male, female, other
- Custom values: Non-negative, reasonable maximums

## Benefits

1. **Personalized**: Recommendations based on individual biometric data
2. **Scientific**: Uses established nutritional formulas
3. **Flexible**: Supports various goals and dietary preferences
4. **Transparent**: Shows calculation methodology
5. **Visual**: Clear progress indicators
6. **Customizable**: Override with healthcare professional recommendations
7. **Current**: Timestamps encourage keeping data updated

## File Structure

```
backend/app/
├── models.py                    # UserProfile model & enums
├── schemas.py                   # Pydantic schemas
├── crud.py                      # Profile CRUD operations
├── nutrition_calculator.py      # BMR/TDEE calculations
├── routers/
│   └── profile_router.py       # Profile API endpoints
└── main.py                      # Router registration

frontend/
├── profile.html                 # Profile management UI
├── metrics.html                 # Enhanced metrics with targets
└── styles.css                   # Profile & progress bar styles
```

## Testing

The system automatically creates database tables on startup. To test:

1. Start the backend server
2. Navigate to `/profile.html`
3. Create a profile with your data
4. View calculated targets
5. Check `/metrics.html` to see progress comparison

## Future Enhancements

Potential additions:
- Micronutrient recommendations (vitamins, minerals)
- Hydration tracking
- Sleep quality integration
- Weekly/monthly goal adjustments
- Progress photos
- Body composition tracking (body fat %)
- Integration with fitness trackers