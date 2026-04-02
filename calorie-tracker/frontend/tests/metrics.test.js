import { describe, expect, it } from 'vitest';

import { summarizeMeals } from '../metrics.js';


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
});
