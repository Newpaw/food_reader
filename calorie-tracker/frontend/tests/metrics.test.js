import { describe, expect, it } from 'vitest';

import { summarizeBodyMetrics, summarizeMeals, summarizeTodayGoal } from '../metrics.js';


describe('metrics summarizer', () => {
  it('computes aggregate and average macro values', () => {
    const summary = summarizeMeals([
      { consumed_at: '2026-04-01T10:00:00Z', calories: 500, protein: 30, carbs: 40, fat: 12, fiber: 5 },
      { consumed_at: '2026-04-02T11:00:00Z', calories: 600, protein: 40, carbs: 50, fat: 18, fiber: 7 },
    ]);

    expect(summary.protein).toBe(70);
    expect(summary.carbs).toBe(90);
    expect(summary.fat).toBe(30);
    expect(summary.averageProtein).toBe(35);
  });

  it('summarizes today against the daily calorie target', () => {
    const summary = summarizeTodayGoal(
      [
        { calories: 700, protein: 45, carbs: 50, fat: 20, fiber: 8 },
        { calories: 650, protein: 30, carbs: 60, fat: 18, fiber: 6 },
      ],
      { calories: 2200 },
    );

    expect(summary.calories).toBe(1350);
    expect(summary.mealCount).toBe(2);
    expect(summary.remainingCalories).toBe(850);
    expect(summary.tone).toBe('success');
  });

  it('summarizes Withings body metric trends', () => {
    const summary = summarizeBodyMetrics([
      { measured_at: '2026-05-10T08:00:00Z', weight_kg: 81.1, fat_ratio: 22.1 },
      { measured_at: '2026-05-01T08:00:00Z', weight_kg: 82.3, fat_ratio: 22.3 },
      { measured_at: '2026-05-04T08:00:00Z', weight_kg: null, muscle_mass_kg: 61 },
    ]);

    expect(summary.hasData).toBe(true);
    expect(summary.latest.weight_kg).toBe(81.1);
    expect(summary.first.weight_kg).toBe(82.3);
    expect(summary.weightDelta).toBe(-1.2);
  });

  it('returns an empty Withings body summary without weight measurements', () => {
    const summary = summarizeBodyMetrics([{ measured_at: '2026-05-10T08:00:00Z', weight_kg: null }]);

    expect(summary.hasData).toBe(false);
    expect(summary.latest).toBeNull();
    expect(summary.weightDelta).toBeNull();
  });
});
