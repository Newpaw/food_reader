export function calculateMacroTotals(meals) {
  return meals.reduce(
    (totals, meal) => {
      totals.protein += meal.protein || 0;
      totals.fat += meal.fat || 0;
      totals.carbs += meal.carbs || 0;
      totals.fiber += meal.fiber || 0;
      totals.calories += meal.calories || 0;
      return totals;
    },
    { protein: 0, fat: 0, carbs: 0, fiber: 0, calories: 0 },
  );
}

export function buildDailyAverages(summaryDays) {
  const totalCalories = summaryDays.reduce((sum, day) => sum + (day.total_calories || 0), 0);
  const totalMeals = summaryDays.reduce((sum, day) => sum + (day.meals || 0), 0);
  const activeDays = summaryDays.length || 1;

  return {
    averageCalories: Math.round(totalCalories / activeDays),
    totalCalories,
    totalMeals,
    maxCalories: Math.max(0, ...summaryDays.map((day) => day.total_calories || 0)),
  };
}

export function renderCalorieBars(container, days, targetCalories = null) {
  if (!container) {
    return;
  }

  if (!days.length) {
    container.innerHTML = '<p class="empty-state compact">No meals matched this range.</p>';
    return;
  }

  const maxValue = Math.max(
    ...days.map((day) => day.total_calories || 0),
    targetCalories || 0,
    1,
  );

  container.innerHTML = days
    .map((day) => {
      const height = Math.max(8, Math.round(((day.total_calories || 0) / maxValue) * 100));
      const targetMarker = targetCalories
        ? `<span class="mini-chart-target" style="bottom:${Math.round((targetCalories / maxValue) * 100)}%"></span>`
        : '';

      return `
        <div class="mini-chart-column">
          <div class="mini-chart-track">
            ${targetMarker}
            <span class="mini-chart-fill" style="height:${height}%"></span>
          </div>
          <strong>${day.total_calories}</strong>
          <span>${day.date}</span>
        </div>
      `;
    })
    .join('');
}

export function renderMacroRing(container, totals) {
  if (!container) {
    return;
  }

  const proteinCalories = totals.protein * 4;
  const carbsCalories = totals.carbs * 4;
  const fatCalories = totals.fat * 9;
  const total = proteinCalories + carbsCalories + fatCalories;

  if (!total) {
    container.innerHTML = '<p class="empty-state compact">Macro distribution will appear after you log meals.</p>';
    return;
  }

  const proteinAngle = (proteinCalories / total) * 360;
  const carbAngle = proteinAngle + (carbsCalories / total) * 360;

  container.innerHTML = `
    <div class="macro-ring" style="background: conic-gradient(var(--accent) 0deg ${proteinAngle}deg, var(--sage) ${proteinAngle}deg ${carbAngle}deg, var(--ink) ${carbAngle}deg 360deg);">
      <div class="macro-ring-center">
        <strong>${total}</strong>
        <span>macro kcal</span>
      </div>
    </div>
    <div class="macro-legend">
      <div><span class="legend-swatch protein"></span>Protein ${totals.protein}g</div>
      <div><span class="legend-swatch carbs"></span>Carbs ${totals.carbs}g</div>
      <div><span class="legend-swatch fats"></span>Fat ${totals.fat}g</div>
    </div>
  `;
}
