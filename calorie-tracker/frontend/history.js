import {
  API,
  apiFetch,
  bindQuickRangeButtons,
  formatDateTime,
  formatDayLabel,
  formatTime,
  getDefaultDateRange,
  getMealDisplayName,
  getJsonOrThrow,
  getLocalDateKey,
  localDateRangeToUtc,
  normalizeOptionalNumber,
  resolveAssetUrl,
  setupPage,
  showStatus,
  t,
  toggleModal,
  toDateTimeInputValue,
} from './common.js?v=20260403-2';

let historyMeals = [];
let activeMeal = null;

function formatRangeLabel(from, to) {
  if (!from || !to) {
    return '';
  }
  const format = (value) =>
    new Intl.DateTimeFormat(document.documentElement.lang || undefined, {
      day: 'numeric',
      month: 'short',
    }).format(new Date(`${value}T00:00:00`));
  return `${format(from)} - ${format(to)}`;
}

function updateHistoryRangeLabel() {
  const from = document.getElementById('historyFrom').value;
  const to = document.getElementById('historyTo').value;
  document.getElementById('historyRangeLabel').textContent = formatRangeLabel(from, to);
}

function toggleHistoryCustomRange(forceOpen = null) {
  const form = document.getElementById('historyFilters');
  const nextState = forceOpen === null ? form.hidden : !forceOpen;
  form.hidden = nextState;
}

export function groupMealsByDay(meals) {
  const grouped = meals.reduce((collection, meal) => {
    const key = getLocalDateKey(meal.consumed_at);
    if (!collection[key]) {
      collection[key] = [];
    }
    collection[key].push(meal);
    return collection;
  }, {});

  return Object.entries(grouped)
    .sort((left, right) => right[0].localeCompare(left[0]))
    .map(([date, items]) => ({
      date,
      meals: items.sort((left, right) => new Date(right.consumed_at) - new Date(left.consumed_at)),
    }));
}

function renderSummary(meals) {
  const target = document.getElementById('historySummary');
  const totalCalories = meals.reduce((sum, meal) => sum + meal.calories, 0);
  const averageCalories = meals.length ? Math.round(totalCalories / meals.length) : 0;

  target.innerHTML = `
    <article class="stat-card"><span>${t('history.summary.totalMeals')}</span><strong>${meals.length}</strong></article>
    <article class="stat-card"><span>${t('history.summary.totalCalories')}</span><strong>${totalCalories}</strong></article>
    <article class="stat-card"><span>${t('history.summary.avgPerMeal')}</span><strong>${averageCalories}</strong></article>
  `;
}

function renderHistory(meals) {
  const target = document.getElementById('historyList');
  if (!meals.length) {
    target.innerHTML = `<p class="empty-state">${t('history.empty')}</p>`;
    renderSummary([]);
    return;
  }

  renderSummary(meals);

  target.innerHTML = groupMealsByDay(meals)
    .map(
      (day) => `
        <section class="day-section">
          <header class="day-section-header">
            <h2>${formatDayLabel(day.date)}</h2>
            <span>${day.meals.length} ${t('history.mealsLabel')}</span>
          </header>
          <div class="meal-grid">
            ${day.meals
              .map(
                (meal) => `
                  <article class="meal-card">
                    <img src="${resolveAssetUrl(meal.image_url)}" alt="${getMealDisplayName(meal)}" class="meal-card-image">
                    <div class="meal-card-body">
                      <div class="meal-card-heading">
                        <h3>${getMealDisplayName(meal)}</h3>
                        <span>${formatTime(meal.consumed_at)}</span>
                      </div>
                      <p class="meal-card-metric">${meal.calories} kcal</p>
                      <p class="meal-card-note">${meal.notes || t('history.noNotes')}</p>
                      <div class="meal-card-actions">
                        <button class="btn btn-secondary btn-small" data-open-meal="${meal.id}">${t('button.view')}</button>
                        <button class="btn btn-ghost btn-small" data-edit-meal="${meal.id}">${t('button.editMeal')}</button>
                        <button class="btn btn-danger btn-small" data-delete-meal="${meal.id}">${t('button.delete')}</button>
                      </div>
                    </div>
                  </article>
                `,
              )
              .join('')}
          </div>
        </section>
      `,
    )
    .join('');

  target.querySelectorAll('[data-open-meal]').forEach((button) => {
    button.addEventListener('click', () => openMealModal(Number(button.dataset.openMeal)));
  });
  target.querySelectorAll('[data-edit-meal]').forEach((button) => {
    button.addEventListener('click', () => openMealModal(Number(button.dataset.editMeal), true));
  });
  target.querySelectorAll('[data-delete-meal]').forEach((button) => {
    button.addEventListener('click', () => deleteMeal(Number(button.dataset.deleteMeal)));
  });
}

async function loadMeals() {
  const status = document.getElementById('historyStatus');
  const { from, to } = localDateRangeToUtc(
    document.getElementById('historyFrom').value,
    document.getElementById('historyTo').value,
  );

  showStatus(status, t('history.loading'), 'info');

  try {
    const search = new URLSearchParams({ limit: '100' });
    if (from) {
      search.set('frm', from);
    }
    if (to) {
      search.set('to', to);
    }

    const response = await apiFetch(`${API.meals}?${search.toString()}`);
    historyMeals = await getJsonOrThrow(response, 'Unable to load meals');
    renderHistory(historyMeals);
    showStatus(status, '', 'info');
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}

function openMealModal(mealId, editMode = false) {
  activeMeal = historyMeals.find((meal) => meal.id === mealId) || null;
  if (!activeMeal) {
    return;
  }

  const mealName = getMealDisplayName(activeMeal);
  document.getElementById('modalMealImage').src = resolveAssetUrl(activeMeal.image_url);
  document.getElementById('modalMealTitle').textContent = `${mealName} · ${activeMeal.calories} kcal`;
  document.getElementById('modalMealMeta').textContent = formatDateTime(activeMeal.consumed_at);
  document.getElementById('modalMealNotes').textContent = activeMeal.notes || t('history.noNotes');

  document.getElementById('editMealType').value = activeMeal.meal_type;
  document.getElementById('editCalories').value = activeMeal.calories;
  document.getElementById('editProtein').value = activeMeal.protein ?? 0;
  document.getElementById('editFat').value = activeMeal.fat ?? 0;
  document.getElementById('editCarbs').value = activeMeal.carbs ?? 0;
  document.getElementById('editFiber').value = activeMeal.fiber ?? 0;
  document.getElementById('editSugar').value = activeMeal.sugar ?? 0;
  document.getElementById('editSodium').value = activeMeal.sodium ?? 0;
  document.getElementById('editConsumedAt').value = toDateTimeInputValue(activeMeal.consumed_at);
  document.getElementById('editNotes').value = activeMeal.notes ?? '';

  document.getElementById('mealModalBody').hidden = editMode;
  document.getElementById('mealEditForm').hidden = !editMode;
  toggleModal(document.getElementById('mealModal'), true);
}

function closeMealModal() {
  toggleModal(document.getElementById('mealModal'), false);
  activeMeal = null;
  showStatus(document.getElementById('mealModalStatus'), '', 'info');
}

async function saveMealEdits(event) {
  event.preventDefault();
  if (!activeMeal) {
    return;
  }

  const form = event.currentTarget;
  const status = document.getElementById('mealModalStatus');
  showStatus(status, t('history.saving'), 'info');

  try {
    const response = await apiFetch(`${API.meals}/${activeMeal.id}`, {
      method: 'PUT',
      body: {
        meal_type: form.mealType.value,
        calories: Number(form.calories.value),
        protein: normalizeOptionalNumber(form.protein.value),
        fat: normalizeOptionalNumber(form.fat.value),
        carbs: normalizeOptionalNumber(form.carbs.value),
        fiber: normalizeOptionalNumber(form.fiber.value),
        sugar: normalizeOptionalNumber(form.sugar.value),
        sodium: normalizeOptionalNumber(form.sodium.value),
        consumed_at: new Date(form.consumedAt.value).toISOString(),
        notes: form.notes.value.trim() || null,
      },
    });

    const updatedMeal = await getJsonOrThrow(response, 'Unable to update meal');
    historyMeals = historyMeals.map((meal) => (meal.id === updatedMeal.id ? updatedMeal : meal));
    renderHistory(historyMeals);
    openMealModal(updatedMeal.id);
    showStatus(status, t('history.saved'), 'success');
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}

async function deleteMeal(mealId) {
  if (!window.confirm(t('history.deleteConfirm'))) {
    return;
  }

  const status = document.getElementById('historyStatus');
  showStatus(status, t('history.deleting'), 'info');

  try {
    const response = await apiFetch(`${API.meals}/${mealId}`, { method: 'DELETE' });
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw new Error(data?.detail || 'Unable to delete meal');
    }

    historyMeals = historyMeals.filter((meal) => meal.id !== mealId);
    renderHistory(historyMeals);
    closeMealModal();
    showStatus(status, t('history.deleted'), 'success');
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  await setupPage();

  const range = getDefaultDateRange(6);
  document.getElementById('historyFrom').value = range.from;
  document.getElementById('historyTo').value = range.to;
  updateHistoryRangeLabel();

  document.getElementById('historyFilters').addEventListener('submit', (event) => {
    event.preventDefault();
    updateHistoryRangeLabel();
    toggleHistoryCustomRange(false);
    loadMeals();
  });
  document.getElementById('historyToggleCustomRange').addEventListener('click', () => {
    toggleHistoryCustomRange();
  });
  document.getElementById('closeMealModal').addEventListener('click', closeMealModal);
  document.getElementById('mealModal').addEventListener('click', (event) => {
    if (event.target.id === 'mealModal') {
      closeMealModal();
    }
  });
  document.getElementById('openMealEdit').addEventListener('click', () => {
    if (activeMeal) {
      openMealModal(activeMeal.id, true);
    }
  });
  document.getElementById('mealEditForm').addEventListener('submit', saveMealEdits);

  bindQuickRangeButtons(Array.from(document.querySelectorAll('[data-days]')), ({ from, to }) => {
    document.getElementById('historyFrom').value = from;
    document.getElementById('historyTo').value = to;
    updateHistoryRangeLabel();
    toggleHistoryCustomRange(false);
    loadMeals();
  });

  window.addEventListener('food-reader:localechange', () => {
    updateHistoryRangeLabel();
    renderHistory(historyMeals);
    if (activeMeal) {
      openMealModal(activeMeal.id, document.getElementById('mealEditForm').hidden === false);
    }
  });

  await loadMeals();
});
