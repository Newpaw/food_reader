// Helper function to get auth headers
function authHeaders() {
  const token = localStorage.getItem('token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

// Check if user is authenticated
function checkAuth() {
  const token = localStorage.getItem('token');
  if (!token) {
    window.location.href = 'login.html';
    return false;
  }
  return true;
}

// Handle meal form submission
document.getElementById('mealForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  if (!checkAuth()) return;
  
  const messageEl = document.getElementById('mealMessage');
  const analysisResultEl = document.getElementById('analysisResult');
  const analysisContentEl = document.getElementById('analysisContent');
  
  messageEl.textContent = '';
  messageEl.style.color = '';
  analysisResultEl.style.display = 'none';
  
  // Show loading message
  messageEl.textContent = 'Analyzing your food image...';
  messageEl.style.color = 'blue';
  
  try {
    const form = e.target;
    const formData = new FormData(form);
    
    // Handle optional datetime field
    const consumedAtInput = formData.get('consumed_at');
    if (consumedAtInput) {
      const dateTime = new Date(consumedAtInput);
      formData.set('consumed_at', dateTime.toISOString());
    } else {
      // Remove empty field to let backend use default
      formData.delete('consumed_at');
    }
    
    // Remove empty optional fields
    if (!formData.get('calories')) formData.delete('calories');
    if (!formData.get('protein')) formData.delete('protein');
    if (!formData.get('fat')) formData.delete('fat');
    if (!formData.get('carbs')) formData.delete('carbs');
    if (!formData.get('fiber')) formData.delete('fiber');
    if (!formData.get('sugar')) formData.delete('sugar');
    if (!formData.get('sodium')) formData.delete('sodium');
    if (!formData.get('meal_type') || formData.get('meal_type') === '') formData.delete('meal_type');
    if (!formData.get('notes')) formData.delete('notes');
    
    const response = await fetch('http://localhost:8000/me/meals', {
      method: 'POST',
      headers: authHeaders(),
      body: formData
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to upload meal');
    }
    
    const mealData = await response.json();
    
    // Display success message
    messageEl.textContent = 'Meal analyzed and added successfully!';
    messageEl.style.color = 'green';
    
    // Display analysis results
    analysisResultEl.style.display = 'block';
    analysisContentEl.innerHTML = `
      <p><strong>Food:</strong> ${mealData.notes ? mealData.notes.replace('AI Analysis: ', '') : 'Food item'}</p>
      <p><strong>Meal Type:</strong> ${mealData.meal_type.charAt(0).toUpperCase() + mealData.meal_type.slice(1)}</p>
      <p><strong>Time:</strong> ${new Date(mealData.consumed_at).toLocaleString()}</p>
    `;
    
    // Update nutrition information
    document.getElementById('nutrition-calories').textContent = mealData.calories || 0;
    document.getElementById('nutrition-protein').textContent = mealData.protein || 0;
    document.getElementById('nutrition-fat').textContent = mealData.fat || 0;
    document.getElementById('nutrition-carbs').textContent = mealData.carbs || 0;
    document.getElementById('nutrition-fiber').textContent = mealData.fiber || 0;
    document.getElementById('nutrition-sugar').textContent = mealData.sugar || 0;
    document.getElementById('nutrition-sodium').textContent = mealData.sodium || 0;
    
    form.reset();
    
    // Reload the meals list
    loadMeals();
  } catch (error) {
    messageEl.textContent = error.message;
    messageEl.style.color = 'red';
    console.error('Error uploading meal:', error);
  }
});

// Load and display meals
async function loadMeals() {
  if (!checkAuth()) return;
  
  try {
    const response = await fetch('http://localhost:8000/me/meals?limit=20', {
      headers: authHeaders()
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('token');
        window.location.href = 'login.html';
        return;
      }
      throw new Error('Failed to load meals');
    }
    
    const meals = await response.json();
    const listElement = document.getElementById('list');
    
    if (meals.length === 0) {
      listElement.innerHTML = '<p>No meals found. Add your first meal above!</p>';
      return;
    }
    
    listElement.innerHTML = meals.map(meal => `
      <div class="meal-item">
        <img src="http://localhost:8000${meal.image_url}" alt="${meal.meal_type}" />
        <div><strong>${meal.meal_type.charAt(0).toUpperCase() + meal.meal_type.slice(1)}</strong> — ${meal.calories} calories</div>
        <div>Consumed: ${new Date(meal.consumed_at).toLocaleString()}</div>
        <div class="nutrition-info" style="margin-top: 8px; font-size: 0.9em;">
          <div><strong>Nutrition:</strong>
            ${meal.protein}g protein,
            ${meal.fat}g fat,
            ${meal.carbs}g carbs,
            ${meal.fiber}g fiber,
            ${meal.sugar}g sugar,
            ${meal.sodium}mg sodium
          </div>
        </div>
        ${meal.notes ? `<div>Notes: ${meal.notes}</div>` : ''}
      </div>
    `).join('');
  } catch (error) {
    console.error('Error loading meals:', error);
    document.getElementById('list').innerHTML = `<p class="error">Error loading meals: ${error.message}</p>`;
  }
}

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
  if (checkAuth()) {
    loadMeals();
  }
});