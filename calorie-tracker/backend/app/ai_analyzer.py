import os
import base64
from openai import OpenAI
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from .settings import settings

# Initialize OpenAI client with the API key from settings
client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)

def encode_image_to_base64(image_path: str) -> str:
    """
    Encode an image file to base64 string
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_food_image(image_path: str) -> Dict[str, Any]:
    """
    Analyze a food image using OpenAI's Vision API to extract:
    - Food name/description
    - Estimated calories
    - Protein, fat, carbohydrates content
    - Fiber, sugar, sodium content (if possible)
    - Meal type (breakfast, lunch, dinner, snack)
    """
    # Encode the image to base64
    base64_image = encode_image_to_base64(image_path)
    
    # Prepare the prompt for the API
    prompt = """
    Analyze this food image and provide the following nutritional information in JSON format:
    1. Food description: What food items are visible in the image?
    2. Estimated calories: Provide a reasonable estimate of total calories.
    3. Protein: Estimated protein content in grams.
    4. Fat: Estimated fat content in grams.
    5. Carbohydrates: Estimated carbohydrate content in grams.
    6. Fiber: Estimated fiber content in grams.
    7. Sugar: Estimated sugar content in grams.
    8. Sodium: Estimated sodium content in milligrams.
    9. Meal type: Categorize as breakfast, lunch, dinner, or snack.
    10. Notes: Any additional nutritional information or observations.
    
    Format your response as a valid JSON object with these keys:
    {
        "food_description": "string",
        "estimated_calories": number,
        "protein": number,
        "fat": number,
        "carbs": number,
        "fiber": number,
        "sugar": number,
        "sodium": number,
        "meal_type": "breakfast|lunch|dinner|snack",
        "notes": "string"
    }
    """
    
    try:
        # Call the OpenAI API with the image
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        # Extract the response text
        response_text = response.choices[0].message.content
        
        # Parse the JSON from the response
        # Note: In a production environment, you would want more robust parsing
        import json
        import re
        
        # Try to extract JSON from the response text
        json_match = re.search(r'({.*})', response_text.replace('\n', ''), re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
        else:
            # Fallback if JSON extraction fails
            result = {
                "food_description": "Unknown food",
                "estimated_calories": 300,  # Default value
                "protein": 0,
                "fat": 0,
                "carbs": 0,
                "fiber": 0,
                "sugar": 0,
                "sodium": 0,
                "meal_type": "snack",       # Default value
                "notes": "Could not analyze the image properly."
            }
        
        # Ensure all required fields are present
        result.setdefault("food_description", "Unknown food")
        result.setdefault("estimated_calories", 300)
        result.setdefault("protein", 0)
        result.setdefault("fat", 0)
        result.setdefault("carbs", 0)
        result.setdefault("fiber", 0)
        result.setdefault("sugar", 0)
        result.setdefault("sodium", 0)
        result.setdefault("meal_type", "snack")
        result.setdefault("notes", "")
        
        return result
        
    except Exception as e:
        # Log the error and return a default response
        print(f"Error analyzing food image: {str(e)}")
        return {
            "food_description": "Error analyzing image",
            "estimated_calories": 300,  # Default value
            "protein": 0,
            "fat": 0,
            "carbs": 0,
            "fiber": 0,
            "sugar": 0,
            "sodium": 0,
            "meal_type": "snack",       # Default value
            "notes": f"Error: {str(e)}"
        }

def get_meal_data_from_image(image_path: str) -> Tuple[int, int, int, int, int, int, int, str, datetime, Optional[str]]:
    """
    Extract meal data from an image and return it in a format ready for the Meal model
    Returns: (calories, protein, fat, carbs, fiber, sugar, sodium, meal_type, consumed_at, notes)
    """
    # Analyze the image
    analysis = analyze_food_image(image_path)
    
    # Extract the data
    calories = int(analysis.get("estimated_calories", 300))
    protein = int(analysis.get("protein", 0))
    fat = int(analysis.get("fat", 0))
    carbs = int(analysis.get("carbs", 0))
    fiber = int(analysis.get("fiber", 0))
    sugar = int(analysis.get("sugar", 0))
    sodium = int(analysis.get("sodium", 0))
    meal_type = analysis.get("meal_type", "snack").lower()
    
    # Validate meal_type is one of the allowed values
    valid_meal_types = ["breakfast", "lunch", "dinner", "snack"]
    if meal_type not in valid_meal_types:
        meal_type = "snack"  # Default to snack if invalid
    
    # Use current time for consumed_at
    consumed_at = datetime.utcnow()
    
    # Combine food description and notes
    food_desc = analysis.get("food_description", "")
    additional_notes = analysis.get("notes", "")
    notes = f"{food_desc}. {additional_notes}" if additional_notes else food_desc
    
    return calories, protein, fat, carbs, fiber, sugar, sodium, meal_type, consumed_at, notes