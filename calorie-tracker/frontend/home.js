import {
  API,
  apiFetch,
  formatDateTime,
  formatTime,
  getMealDisplayName,
  getJsonOrThrow,
  resolveAssetUrl,
  setupPage,
  showStatus,
  toDateTimeInputValue,
} from './common.js';


let currentMeal = null;
let originalMeal = null;


export function buildMealUpdatePayload(draft) {
  return {
    calories: Number(draft.calories || 0),
    protein: Number(draft.protein || 0),
    fat: Number(draft.fat || 0),
    carbs: Number(draft.carbs || 0),
    fiber: Number(draft.fiber || 0),
    sugar: Number(draft.sugar || 0),
    sodium: Number(draft.sodium || 0),
    meal_type: draft.mealType,
    consumed_at: new Date(draft.consumedAt).toISOString(),
    notes: draft.notes.trim() || null,
  };
}


function getAnalysisFields() {
  return {
    calories: document.getElementById('analysisCalories'),
    protein: document.getElementById('analysisProtein'),
    fat: document.getElementById('analysisFat'),
    carbs: document.getElementById('analysisCarbs'),
    fiber: document.getElementById('analysisFiber'),
    sugar: document.getElementById('analysisSugar'),
    sodium: document.getElementById('analysisSodium'),
    mealType: document.getElementById('analysisMealType'),
    consumedAt: document.getElementById('analysisConsumedAt'),
    notes: document.getElementById('analysisNotes'),
  };
}


function renderMealEditor(meal) {
  currentMeal = meal;
  originalMeal = { ...meal };
  const imageUrl = resolveAssetUrl(meal.image_url);
  const mealName = getMealDisplayName(meal);

  const panel = document.getElementById('analysisPanel');
  const fields = getAnalysisFields();
  panel.hidden = false;

  fields.calories.value = meal.calories ?? 0;
  fields.protein.value = meal.protein ?? 0;
  fields.fat.value = meal.fat ?? 0;
  fields.carbs.value = meal.carbs ?? 0;
  fields.fiber.value = meal.fiber ?? 0;
  fields.sugar.value = meal.sugar ?? 0;
  fields.sodium.value = meal.sodium ?? 0;
  fields.mealType.value = meal.meal_type;
  fields.consumedAt.value = toDateTimeInputValue(meal.consumed_at);
  fields.notes.value = meal.notes ?? '';

  const preview = document.getElementById('analysisPreview');
  preview.innerHTML = `
    <img src="${imageUrl}" alt="${mealName}" class="analysis-preview-image">
    <div>
      <p class="eyebrow">Latest entry</p>
      <h3>${mealName} logged</h3>
      <p>${formatDateTime(meal.consumed_at)}</p>
    </div>
  `;

  const reanalysisBlock = document.getElementById('reanalysisBlock');
  reanalysisBlock.hidden = meal.image_url === '/assets/images/text-meal-placeholder.svg';
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}


function renderRecentMeals(meals) {
  const target = document.getElementById('recentMeals');
  if (!meals.length) {
    target.innerHTML = '<p class="empty-state">No meals yet. Add one to get started.</p>';
    return;
  }

  target.innerHTML = meals
    .map(
      (meal) => `
        <article class="meal-card compact">
          <img src="${resolveAssetUrl(meal.image_url)}" alt="${getMealDisplayName(meal)}" class="meal-card-image">
          <div class="meal-card-body">
            <div class="meal-card-heading">
              <h3>${getMealDisplayName(meal)}</h3>
              <span>${formatTime(meal.consumed_at)}</span>
            </div>
            <p>${meal.calories} kcal</p>
            <button class="btn btn-secondary btn-small" data-meal-open="${meal.id}">Review</button>
          </div>
        </article>
      `,
    )
    .join('');

  target.querySelectorAll('[data-meal-open]').forEach((button) => {
    button.addEventListener('click', () => {
      const meal = meals.find((item) => item.id === Number(button.dataset.mealOpen));
      if (meal) {
        renderMealEditor(meal);
      }
    });
  });
}


async function loadRecentMeals() {
  const response = await apiFetch(`${API.meals}?limit=5`);
  const meals = await getJsonOrThrow(response, 'Unable to load recent meals');
  renderRecentMeals(meals);
}


function handleFileSelection(event) {
  const file = event.target.files?.[0];
  const preview = document.getElementById('selectedImagePreview');
  const emptyState = document.getElementById('selectedImageEmpty');

  if (!file) {
    preview.src = '';
    preview.hidden = true;
    emptyState.hidden = false;
    return;
  }

  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
  emptyState.hidden = true;
}


async function handlePhotoMealSubmit(event) {
  event.preventDefault();
  const fileInput = document.getElementById('mealImage');
  const file = fileInput.files?.[0];
  const status = document.getElementById('captureStatus');

  if (!file) {
    showStatus(status, 'Choose a photo before submitting.', 'danger');
    return;
  }

  const formData = new FormData();
  formData.append('image', file);
  showStatus(status, 'Analyzing your meal photo...', 'info');

  try {
    const response = await apiFetch(API.meals, {
      method: 'POST',
      body: formData,
    });
    const meal = await getJsonOrThrow(response, 'Unable to add meal from photo');
    showStatus(status, 'Meal added. Review the estimate below.', 'success');
    renderMealEditor(meal);
    event.currentTarget.reset();
    handleFileSelection({ target: { files: [] } });
    await loadRecentMeals();
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}


async function handleTextMealSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const status = document.getElementById('captureStatus');
  const description = form.foodDescription.value.trim();

  if (!description) {
    showStatus(status, 'Describe the meal before submitting.', 'danger');
    return;
  }

  showStatus(status, 'Analyzing your meal description...', 'info');

  try {
    const response = await apiFetch(`${API.meals}/text`, {
      method: 'POST',
      body: { food_description: description },
    });
    const meal = await getJsonOrThrow(response, 'Unable to add meal from text');
    showStatus(status, 'Meal added. Review the estimate below.', 'success');
    renderMealEditor(meal);
    form.reset();
    await loadRecentMeals();
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}


async function handleSaveMealChanges() {
  if (!currentMeal) {
    return;
  }

  const status = document.getElementById('analysisStatus');
  const fields = getAnalysisFields();
  showStatus(status, 'Saving adjustments...', 'info');

  try {
    const response = await apiFetch(`${API.meals}/${currentMeal.id}`, {
      method: 'PUT',
      body: buildMealUpdatePayload({
        calories: fields.calories.value,
        protein: fields.protein.value,
        fat: fields.fat.value,
        carbs: fields.carbs.value,
        fiber: fields.fiber.value,
        sugar: fields.sugar.value,
        sodium: fields.sodium.value,
        mealType: fields.mealType.value,
        consumedAt: fields.consumedAt.value,
        notes: fields.notes.value,
      }),
    });
    currentMeal = await getJsonOrThrow(response, 'Unable to save meal changes');
    originalMeal = { ...currentMeal };
    renderMealEditor(currentMeal);
    showStatus(status, 'Meal updated.', 'success');
    await loadRecentMeals();
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}


function resetMealChanges() {
  if (originalMeal) {
    renderMealEditor(originalMeal);
    showStatus(document.getElementById('analysisStatus'), 'Changes reset.', 'info');
  }
}


async function handleReanalyze() {
  if (!currentMeal) {
    return;
  }

  const corrections = document.getElementById('reanalysisCorrections').value.trim();
  const status = document.getElementById('analysisStatus');

  if (!corrections) {
    showStatus(status, 'Add a correction before re-running the analysis.', 'danger');
    return;
  }

  showStatus(status, 'Reanalyzing meal...', 'info');

  try {
    const response = await apiFetch(`${API.meals}/${currentMeal.id}/reanalyze`, {
      method: 'POST',
      body: { corrections: { note: corrections } },
    });
    currentMeal = await getJsonOrThrow(response, 'Unable to reanalyze meal');
    originalMeal = { ...currentMeal };
    renderMealEditor(currentMeal);
    document.getElementById('reanalysisCorrections').value = '';
    showStatus(status, 'AI analysis updated.', 'success');
    await loadRecentMeals();
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}


function initializeModeSwitch() {
  const buttons = document.querySelectorAll('[data-capture-mode]');
  const sections = document.querySelectorAll('[data-mode-panel]');

  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      buttons.forEach((item) => item.classList.toggle('active', item === button));
      sections.forEach((panel) => {
        panel.hidden = panel.dataset.modePanel !== button.dataset.captureMode;
      });
    });
  });
}


document.addEventListener('DOMContentLoaded', async () => {
  await setupPage();

  initializeModeSwitch();
  document.getElementById('mealImage').addEventListener('change', handleFileSelection);
  document.getElementById('photoMealForm').addEventListener('submit', handlePhotoMealSubmit);
  document.getElementById('textMealForm').addEventListener('submit', handleTextMealSubmit);
  document.getElementById('saveAnalysisButton').addEventListener('click', handleSaveMealChanges);
  document.getElementById('resetAnalysisButton').addEventListener('click', resetMealChanges);
  document.getElementById('reanalyzeButton').addEventListener('click', handleReanalyze);

  await loadRecentMeals();
});
