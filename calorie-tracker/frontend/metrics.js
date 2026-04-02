import {
  API,
  apiFetch,
  bindQuickRangeButtons,
  getBrowserTimeZone,
  getDefaultDateRange,
  getLocalDateKey,
  getJsonOrThrow,
  localDateRangeToUtc,
  parseDateInputValue,
  setupPage,
  showStatus,
  t,
} from './common.js?v=20260403-3';
import {
  buildDailyAverages,
  calculateMacroTotals,
  renderCalorieBars,
  renderMacroRing,
} from './charts.js?v=20260403-3';

let cachedTargets = null;
let cachedSummaryDays = [];
let cachedMeals = [];
let cachedTodayMeals = [];

function formatRangeLabel(from, to) {
  if (!from || !to) {
    return '';
  }
  const format = (value) =>
    new Intl.DateTimeFormat(document.documentElement.lang || undefined, {
      day: 'numeric',
      month: 'short',
    }).format(parseDateInputValue(value));
  return `${format(from)} - ${format(to)}`;
}

function updateMetricsRangeLabel() {
  const from = document.getElementById('metricsFrom').value;
  const to = document.getElementById('metricsTo').value;
  document.getElementById('metricsRangeLabel').textContent = formatRangeLabel(from, to);
}

function toggleMetricsCustomRange(forceOpen = null) {
  const form = document.getElementById('metricsFilters');
  const nextState = forceOpen === null ? form.hidden : !forceOpen;
  form.hidden = nextState;
}

export function summarizeMeals(meals) {
  const totals = calculateMacroTotals(meals);
  const daysWithMeals = new Set(meals.map((meal) => getLocalDateKey(meal.consumed_at))).size || 1;

  return {
    ...totals,
    averageCalories: Math.round(totals.calories / daysWithMeals),
    averageProtein: Math.round(totals.protein / daysWithMeals),
    averageCarbs: Math.round(totals.carbs / daysWithMeals),
    averageFat: Math.round(totals.fat / daysWithMeals),
  };
}

export function summarizeTodayGoal(meals, targets = null) {
  const totals = calculateMacroTotals(meals);
  const mealCount = meals.length;
  const targetCalories = targets?.calories ?? null;
  const remainingCalories = targetCalories === null ? null : targetCalories - totals.calories;
  const progressPercent = targetCalories ? Math.min(140, Math.round((totals.calories / targetCalories) * 100)) : 0;
  const metricBreakdown = [
    {
      key: 'calories',
      label: t('metrics.calories'),
      actual: totals.calories,
      target: targets?.calories ?? null,
      unit: 'kcal',
    },
    {
      key: 'protein',
      label: t('metrics.protein'),
      actual: totals.protein,
      target: targets?.protein_g ?? null,
      unit: 'g',
    },
    {
      key: 'carbs',
      label: t('metrics.carbs'),
      actual: totals.carbs,
      target: targets?.carbs_g ?? null,
      unit: 'g',
    },
    {
      key: 'fat',
      label: t('metrics.fat'),
      actual: totals.fat,
      target: targets?.fats_g ?? null,
      unit: 'g',
    },
    {
      key: 'fiber',
      label: t('metrics.fiber'),
      actual: totals.fiber,
      target: targets?.fiber_g ?? null,
      unit: 'g',
    },
  ].map((metric) => {
    const progress = metric.target ? Math.min(160, Math.round((metric.actual / metric.target) * 100)) : 0;
    const delta = metric.target === null ? null : metric.target - metric.actual;
    return {
      ...metric,
      progress,
      delta,
      tone: metric.target === null ? 'neutral' : delta >= 0 ? 'success' : 'danger',
    };
  });

  let tone = 'neutral';
  let headline = t('metrics.todayNoMeals');
  let detail = targetCalories === null
    ? t('metrics.todayNoTarget')
    : t('metrics.todayRemaining', { remaining: targetCalories });

  if (targetCalories === null) {
    headline = t('metrics.todayNoTarget');
    detail = t('metrics.todayNoTargetConsumed', { calories: totals.calories });
  } else if (!mealCount) {
    headline = t('metrics.todayNoMeals');
    detail = t('metrics.todayRemaining', { remaining: targetCalories });
  } else if (remainingCalories >= 0) {
    tone = 'success';
    headline = t('metrics.todayOnTrack');
    detail = t('metrics.todayRemaining', { remaining: remainingCalories });
  } else {
    tone = 'danger';
    headline = t('metrics.todayOverGoal');
    detail = t('metrics.todayOverAmount', { remaining: Math.abs(remainingCalories) });
  }

  return {
    ...totals,
    mealCount,
    targetCalories,
    remainingCalories,
    progressPercent,
    tone,
    headline,
    detail,
    metricBreakdown,
  };
}

function renderTodayGoal(todayMeals, targets) {
  const panel = document.getElementById('todayGoalPanel');
  const summary = summarizeTodayGoal(todayMeals, targets);
  const consumedLabel =
    summary.targetCalories === null
      ? t('metrics.todayNoTargetConsumed', { calories: summary.calories })
      : t('metrics.todayConsumed', { calories: summary.calories, target: summary.targetCalories });

  const progressFill = summary.targetCalories
    ? `<span class="goal-progress-fill" style="width:${summary.progressPercent}%"></span>`
    : '';

  panel.innerHTML = `
    <div class="panel-heading">
      <div>
        <p class="eyebrow">${t('metrics.todayEyebrow')}</p>
        <h1 class="metrics-today-title">${t('metrics.todayHeading')}</h1>
      </div>
      <button type="button" class="btn btn-secondary btn-small" id="metricsTodayShortcut">${t('button.today')}</button>
    </div>
    <div class="metrics-today-grid">
      <div class="metrics-today-copy">
        <p class="goal-state" data-tone="${summary.tone}">${summary.headline}</p>
        <div class="goal-kcal-block">
          <strong>${summary.calories}</strong>
          <span>${consumedLabel}</span>
        </div>
        <p class="panel-note">${summary.detail}</p>
      </div>
      <div class="goal-progress-card">
        <div class="goal-progress-track">
          ${progressFill}
        </div>
        <div class="goal-progress-meta">
          <strong>${summary.targetCalories ? `${summary.progressPercent}%` : '-'}</strong>
          <span>${summary.targetCalories ? t('metrics.calories') : t('metrics.setupProfile')}</span>
        </div>
      </div>
    </div>
    <div class="metrics-today-meta">
      <article class="stat-card metrics-mini-stat">
        <span>${t('metrics.todayMeals')}</span>
        <strong>${summary.mealCount}</strong>
      </article>
    </div>
    <div class="today-metrics-list">
      ${summary.metricBreakdown
        .map(
          (metric) => `
            <div class="today-metric-row">
              <div class="today-metric-header">
                <strong>${metric.label}</strong>
                <span>${metric.actual}${metric.unit}${metric.target === null ? '' : ` / ${metric.target}${metric.unit}`}</span>
              </div>
              <div class="today-metric-track">
                <span class="today-metric-fill" data-tone="${metric.tone}" style="width:${metric.target ? metric.progress : 0}%"></span>
              </div>
            </div>
          `,
        )
        .join('')}
    </div>
  `;

  document.getElementById('metricsTodayShortcut')?.addEventListener('click', () => {
    const range = getDefaultDateRange(0);
    document.getElementById('metricsFrom').value = range.from;
    document.getElementById('metricsTo').value = range.to;
    updateMetricsRangeLabel();
    toggleMetricsCustomRange(false);
    loadMetrics();
  });
}

function renderTargets(targets) {
  const panel = document.getElementById('targetPanel');
  if (!targets) {
    panel.innerHTML = `
      <div class="panel-heading">
        <div>
          <p class="eyebrow">${t('metrics.targetsEyebrow')}</p>
          <h2>${t('metrics.targetsHeading')}</h2>
        </div>
      </div>
      <div class="empty-state">
        <p>${t('metrics.targetsMissing')}</p>
        <a class="btn btn-secondary" href="profile.html">${t('metrics.setupProfile')}</a>
      </div>
    `;
    return;
  }

  panel.innerHTML = `
    <div class="panel-heading">
      <div>
        <p class="eyebrow">${t('metrics.targetsEyebrow')}</p>
        <h2>${t('metrics.targetsHeading')}</h2>
      </div>
    </div>
    <div class="stat-grid">
      <article class="stat-card"><span>${t('metrics.calories')}</span><strong>${targets.calories}</strong></article>
      <article class="stat-card"><span>${t('metrics.protein')}</span><strong>${targets.protein_g}g</strong></article>
      <article class="stat-card"><span>${t('metrics.carbs')}</span><strong>${targets.carbs_g}g</strong></article>
      <article class="stat-card"><span>${t('metrics.fat')}</span><strong>${targets.fats_g}g</strong></article>
      <article class="stat-card"><span>${t('metrics.fiber')}</span><strong>${targets.fiber_g}g</strong></article>
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
    [t('metrics.calories'), summary.averageCalories, targets.calories, 'kcal'],
    [t('metrics.protein'), summary.averageProtein, targets.protein_g, 'g'],
    [t('metrics.carbs'), summary.averageCarbs, targets.carbs_g, 'g'],
    [t('metrics.fat'), summary.averageFat, targets.fats_g, 'g'],
  ];

  target.innerHTML = rows
    .map(([label, actual, expected, unit]) => {
      const percentage = expected ? Math.min(140, Math.round((actual / expected) * 100)) : 0;
      return `
        <div class="progress-row">
          <div class="progress-row-header">
            <strong>${label}</strong>
            <span>${actual}${unit} ${t('metrics.avgPerDay')} / ${expected}${unit}</span>
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
    <article class="stat-card"><span>${t('metrics.avgDailyCalories')}</span><strong>${averages.averageCalories}</strong></article>
    <article class="stat-card"><span>${t('metrics.totalCalories')}</span><strong>${averages.totalCalories}</strong></article>
    <article class="stat-card"><span>${t('metrics.totalMeals')}</span><strong>${averages.totalMeals}</strong></article>
    <article class="stat-card"><span>${t('metrics.fiberLogged')}</span><strong>${macroTotals.fiber}g</strong></article>
  `;
}

function renderDailyList(summaryDays) {
  const target = document.getElementById('dailyList');
  if (!summaryDays.length) {
    target.innerHTML = `<p class="empty-state compact">${t('metrics.dayListEmpty')}</p>`;
    return;
  }

  target.innerHTML = summaryDays
    .map(
      (day) => `
        <div class="daily-row">
          <div>
            <strong>${day.date}</strong>
            <span>${day.meals} ${t('metrics.mealsLabel')}</span>
          </div>
          <strong>${day.total_calories} kcal</strong>
        </div>
      `,
    )
    .join('');
}

function rerenderMetrics() {
  const mealSummary = summarizeMeals(cachedMeals);
  renderTodayGoal(cachedTodayMeals, cachedTargets);
  renderTargets(cachedTargets);
  renderNutritionStats(cachedSummaryDays, cachedMeals);
  renderProgress(mealSummary, cachedTargets);
  renderCalorieBars(document.getElementById('calorieBars'), cachedSummaryDays, cachedTargets?.calories ?? null);
  renderMacroRing(document.getElementById('macroRing'), mealSummary);
  renderDailyList(cachedSummaryDays);
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

  showStatus(status, t('metrics.loading'), 'info');

  try {
    const todayRange = getDefaultDateRange(0);
    const todayUtcRange = localDateRangeToUtc(todayRange.from, todayRange.to);
    const todayParams = new URLSearchParams();
    if (todayUtcRange.from) {
      todayParams.set('frm', todayUtcRange.from);
    }
    if (todayUtcRange.to) {
      todayParams.set('to', todayUtcRange.to);
    }

    const [targetsResponse, summaryResponse, mealsResponse, todayMealsResponse] = await Promise.all([
      apiFetch(`${API.profile}/targets`),
      apiFetch(`${API.summary}?${params.toString()}&tz_name=${encodeURIComponent(getBrowserTimeZone())}`),
      apiFetch(`${API.meals}?limit=200&${params.toString()}`),
      apiFetch(`${API.meals}?limit=100&${todayParams.toString()}`),
    ]);

    cachedTargets = targetsResponse.ok ? await targetsResponse.json() : null;
    const summaryData = await getJsonOrThrow(summaryResponse, 'Unable to load summary');
    cachedSummaryDays = summaryData.days;
    cachedMeals = await getJsonOrThrow(mealsResponse, 'Unable to load meals');
    cachedTodayMeals = await getJsonOrThrow(todayMealsResponse, 'Unable to load today meals');

    rerenderMetrics();
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
  updateMetricsRangeLabel();

  document.getElementById('metricsFilters').addEventListener('submit', (event) => {
    event.preventDefault();
    updateMetricsRangeLabel();
    toggleMetricsCustomRange(false);
    loadMetrics();
  });
  document.getElementById('metricsToggleCustomRange').addEventListener('click', () => {
    toggleMetricsCustomRange();
  });

  bindQuickRangeButtons(Array.from(document.querySelectorAll('[data-days]')), ({ from, to }) => {
    document.getElementById('metricsFrom').value = from;
    document.getElementById('metricsTo').value = to;
    updateMetricsRangeLabel();
    toggleMetricsCustomRange(false);
    loadMetrics();
  });

  window.addEventListener('food-reader:localechange', () => {
    updateMetricsRangeLabel();
    rerenderMetrics();
  });

  await loadMetrics();
});
