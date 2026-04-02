import { describe, expect, it } from 'vitest';

import { buildDailyAverages, calculateMacroTotals } from '../charts.js';


describe('chart data helpers', () => {
  it('sums macro totals across meals', () => {
    const totals = calculateMacroTotals([
      { calories: 500, protein: 30, carbs: 40, fat: 20, fiber: 5 },
      { calories: 450, protein: 20, carbs: 55, fat: 15, fiber: 8 },
    ]);

    expect(totals).toEqual({
      calories: 950,
      protein: 50,
      carbs: 95,
      fat: 35,
      fiber: 13,
    });
  });

  it('calculates daily summary averages', () => {
    const result = buildDailyAverages([
      { total_calories: 2000, meals: 3 },
      { total_calories: 1800, meals: 2 },
    ]);

    expect(result).toEqual({
      averageCalories: 1900,
      totalCalories: 3800,
      totalMeals: 5,
      maxCalories: 2000,
    });
  });
});
