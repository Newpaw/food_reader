import { describe, expect, it } from 'vitest';

import { buildMealUpdatePayload, planPhotoOptimization, shouldPreferMobileCamera, summarizeTodayState } from '../home.js';


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

describe('today dashboard summary', () => {
  it('summarizes today totals, streak, queue, and templates', () => {
    const now = new Date();
    const todayIso = now.toISOString();
    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);

    const summary = summarizeTodayState(
      [
        { consumed_at: todayIso, calories: 500, protein: 30, fiber: 8 },
        { consumed_at: todayIso, calories: 450, protein: 20, fiber: 4 },
        { consumed_at: yesterday.toISOString(), calories: 700, protein: 40, fiber: 5 },
      ],
      { calories: 2200 },
      2,
      3,
    );

    expect(summary.calories).toBe(950);
    expect(summary.protein).toBe(50);
    expect(summary.fiber).toBe(12);
    expect(summary.meals).toBe(2);
    expect(summary.streak).toBeGreaterThanOrEqual(2);
    expect(summary.remainingCalories).toBe(1250);
    expect(summary.queueCount).toBe(2);
    expect(summary.templateCount).toBe(3);
  });
});

describe('mobile camera preference', () => {
  it('prefers the direct camera path on phone-like devices', () => {
    const environment = {
      matchMedia: (query) => ({
        matches: query === '(max-width: 820px)' || query === '(pointer: coarse)',
      }),
      navigator: {
        maxTouchPoints: 5,
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)',
      },
    };

    expect(shouldPreferMobileCamera(environment)).toBe(true);
    expect(
      shouldPreferMobileCamera({
        matchMedia: () => ({ matches: false }),
        navigator: { maxTouchPoints: 0, userAgent: 'Mozilla/5.0 (X11; Linux x86_64)' },
      }),
    ).toBe(false);
  });
});

describe('photo optimization plan', () => {
  it('shrinks large mobile photos before upload', () => {
    const plan = planPhotoOptimization({
      type: 'image/jpeg',
      size: 5_200_000,
      width: 4032,
      height: 3024,
    });

    expect(plan.shouldOptimize).toBe(true);
    expect(plan.shouldResize).toBe(true);
    expect(plan.targetWidth).toBe(1600);
    expect(plan.targetHeight).toBe(1200);
  });

  it('forces conversion for unsupported mobile image formats', () => {
    const plan = planPhotoOptimization({
      type: 'image/heic',
      size: 420_000,
      width: 1200,
      height: 1600,
    });

    expect(plan.shouldOptimize).toBe(true);
    expect(plan.shouldResize).toBe(false);
  });
});
