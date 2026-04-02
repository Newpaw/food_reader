import { describe, expect, it } from 'vitest';

import { buildMealUpdatePayload } from '../home.js';


describe('meal payload builder', () => {
  it('serializes editable meal values for the API', () => {
    const payload = buildMealUpdatePayload({
      calories: '610',
      protein: '35',
      fat: '21',
      carbs: '44',
      fiber: '7',
      sugar: '9',
      sodium: '540',
      mealType: 'dinner',
      consumedAt: '2026-04-02T18:30',
      notes: 'Adjusted after checking the label',
    });

    expect(payload.calories).toBe(610);
    expect(payload.protein).toBe(35);
    expect(payload.meal_type).toBe('dinner');
    expect(payload.consumed_at).toContain('2026-04-02T');
  });
});
