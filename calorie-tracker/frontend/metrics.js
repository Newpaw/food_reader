import {
  API,
  apiFetch,
  bindQuickRangeButtons,
  getDefaultDateRange,
  getJsonOrThrow,
  localDateRangeToUtc,
  setupPage,
  showStatus,
} from './common.js';
import {
  buildDailyAverages,
  calculateMacroTotals,
  renderCalorieBars,
  renderMacroRing,
} from './charts.js';


export function summarizeMeals(meals) {
  const totals = calculateMacroTotals(meals);
  const daysWithMeals = new Set(meals.map((meal) => meal.consumed_at.slice(0, 10))).size || 1;

  return {
    ...totals,
    averageCalories: Math.round(totals.calories / daysWithMeals),
    averageProtein: Math.round(totals.protein / daysWithMeals),
    averageCarbs: Math.round(totals.carbs / daysWithMeals),
    averageFat: Math.round(totals.fat / daysWithMeals),
  };
}


function renderTargets(targets) {
  const panel = document.getElementById('targetPanel');
  if (!targets) {
    panel.innerHTML = `
      <div class="empty-state">
        <p>Create a profile to unlock personalized calorie and macro targets.</p>
        <a class="btn btn-secondary" href="profile.html">Set up profile</a>
      </div>
    `;
    return;
  }

  panel.innerHTML = `
    <div class="stat-grid">
      <article class="stat-card"><span>Calories</span><strong>${targets.calories}</strong></article>
      <article class="stat-card"><span>Protein</span><strong>${targets.protein_g}g</strong></article>
      <article class="stat-card"><span>Carbs</span><strong>${targets.carbs_g}g</strong></article>
      <article class="stat-card"><span>Fat</span><strong>${targets.fats_g}g</strong></article>
      <article class="stat-card"><span>Fiber</span><strong>${targets.fiber_g}g</strong></article>
    </div>
    <p class="panel-note">${targets.calculation_method}</p>
  `;
}


function renderProgress(summary, targets) {
  const target = document.getElementById('progressPanel');
  if (!targets) {
    target.innerHTML = '';
    return;
  }

  const rows = [
    ['Calories', summary.averageCalories, targets.calories, 'kcal'],
    ['Protein', summary.averageProtein, targets.protein_g, 'g'],
    ['Carbs', summary.averageCarbs, targets.carbs_g, 'g'],
    ['Fat', summary.averageFat, targets.fats_g, 'g'],
  ];

  target.innerHTML = rows
    .map(([label, actual, expected, unit]) => {
      const percentage = expected ? Math.min(140, Math.round((actual / expected) * 100)) : 0;
      return `
        <div class="progress-row">
          <div class="progress-row-header">
            <strong>${label}</strong>
            <span>${actual}${unit} / ${expected}${unit}</span>
          </div>
          <div class="progress-track">
            <span class="progress-fill" style="width:${percentage}%"></span>
          </div>
        </div>
      `;
    })
    .join('');
}


function renderNutritionStats(summaryDays, meals) {
  const averages = buildDailyAverages(summaryDays);
  const macroTotals = calculateMacroTotals(meals);
  document.getElementById('metricsStats').innerHTML = `
    <article class="stat-card"><span>Avg daily calories</span><strong>${averages.averageCalories}</strong></article>
    <article class="stat-card"><span>Total calories</span><strong>${averages.totalCalories}</strong></article>
    <article class="stat-card"><span>Total meals</span><strong>${averages.totalMeals}</strong></article>
    <article class="stat-card"><span>Fiber logged</span><strong>${macroTotals.fiber}g</strong></article>
  `;
}


function renderDailyList(summaryDays) {
  const target = document.getElementById('dailyList');
  if (!summaryDays.length) {
    target.innerHTML = '<p class="empty-state compact">Daily breakdown will appear after you log meals.</p>';
    return;
  }

  target.innerHTML = summaryDays
    .map(
      (day) => `
        <div class="daily-row">
          <div>
            <strong>${day.date}</strong>
            <span>${day.meals} meals</span>
          </div>
          <strong>${day.total_calories} kcal</strong>
        </div>
      `,
    )
    .join('');
}


async function loadMetrics() {
  const status = document.getElementById('metricsStatus');
  const { from, to } = localDateRangeToUtc(
    document.getElementById('metricsFrom').value,
    document.getElementById('metricsTo').value,
  );
  const params = new URLSearchParams();
  if (from) {
    params.set('frm', from);
  }
  if (to) {
    params.set('to', to);
  }

  showStatus(status, 'Loading metrics...', 'info');

  try {
    const [targetsResponse, summaryResponse, mealsResponse] = await Promise.all([
      apiFetch(`${API.profile}/targets`),
      apiFetch(`${API.summary}?${params.toString()}&tz_offset_minutes=${new Date().getTimezoneOffset()}`),
      apiFetch(`${API.meals}?limit=200&${params.toString()}`),
    ]);

    const targets = targetsResponse.ok ? await targetsResponse.json() : null;
    const summaryData = await getJsonOrThrow(summaryResponse, 'Unable to load summary');
    const meals = await getJsonOrThrow(mealsResponse, 'Unable to load meals');
    const mealSummary = summarizeMeals(meals);

    renderTargets(targets);
    renderNutritionStats(summaryData.days, meals);
    renderProgress(mealSummary, targets);
    renderCalorieBars(document.getElementById('calorieBars'), summaryData.days, targets?.calories ?? null);
    renderMacroRing(document.getElementById('macroRing'), mealSummary);
    renderDailyList(summaryData.days);
    showStatus(status, '', 'info');
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}


document.addEventListener('DOMContentLoaded', async () => {
  await setupPage();

  const range = getDefaultDateRange(6);
  document.getElementById('metricsFrom').value = range.from;
  document.getElementById('metricsTo').value = range.to;

  document.getElementById('metricsFilters').addEventListener('submit', (event) => {
    event.preventDefault();
    loadMetrics();
  });

  bindQuickRangeButtons(Array.from(document.querySelectorAll('[data-days]')), ({ from, to }) => {
    document.getElementById('metricsFrom').value = from;
    document.getElementById('metricsTo').value = to;
    loadMetrics();
  });

  await loadMetrics();
});
