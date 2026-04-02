import { describe, expect, it } from 'vitest';

import {
  getMealDisplayName,
  getLocale,
  localDateRangeToUtc,
  normalizeOptionalNumber,
  setLocale,
  shouldUseSplitLocalApi,
  t,
} from '../common.js';


describe('common helpers', () => {
  it('converts a local date range to an inclusive-exclusive UTC range', () => {
    const range = localDateRangeToUtc('2026-04-01', '2026-04-02');

    const from = new Date(range.from);
    const to = new Date(range.to);

    expect(to.getTime() - from.getTime()).toBe(48 * 60 * 60 * 1000);
    expect(to.getTime()).toBeGreaterThan(from.getTime());
  });

  it('normalizes optional numbers', () => {
    expect(normalizeOptionalNumber('')).toBeNull();
    expect(normalizeOptionalNumber(undefined)).toBeNull();
    expect(normalizeOptionalNumber('42')).toBe(42);
  });

  it('only forces split local API mode for known static dev ports', () => {
    expect(shouldUseSplitLocalApi({ port: '8080' })).toBe(true);
    expect(shouldUseSplitLocalApi({ port: '5173' })).toBe(true);
    expect(shouldUseSplitLocalApi({ port: '18080' })).toBe(false);
    expect(shouldUseSplitLocalApi({ port: '' })).toBe(false);
  });

  it('derives a short dish name from meal notes', () => {
    expect(
      getMealDisplayName({
        meal_type: 'lunch',
        notes: 'Text description: burger with fries and cola',
      }),
    ).toBe('Burger with fries and cola');

    expect(
      getMealDisplayName({
        meal_type: 'dinner',
        notes: 'Burger with fries. Estimated from image with moderate confidence.',
      }),
    ).toBe('Burger with fries');
  });

  it('falls back to meal type when notes are generic', () => {
    expect(
      getMealDisplayName({
        meal_type: 'snack',
        notes: 'Unknown food. Could not analyze the image properly.',
      }),
    ).toBe('Snack');
  });

  it('switches translations when locale changes', () => {
    setLocale('cs');

    expect(getLocale()).toBe('cs');
    expect(t('nav.metrics')).toBe('Přehled');

    setLocale('en');
  });
});
