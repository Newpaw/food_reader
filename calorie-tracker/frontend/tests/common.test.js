import { describe, expect, it, vi } from 'vitest';

import {
  getMealDisplayName,
  getLocale,
  localDateRangeToUtc,
  normalizeOptionalNumber,
  setLocale,
  setupInstallPrompt,
  shouldAutoShowInstallPrompt,
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

    expect(
      getMealDisplayName({
        meal_type: 'dinner',
        notes: 'AI Analysis: cheeseburger with bacon\nUser context: I only ate half the fries',
      }),
    ).toBe('Cheeseburger with bacon');
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

  it('suppresses install auto-show when recently dismissed', () => {
    const now = Date.now();

    expect(
      shouldAutoShowInstallPrompt({
        dismissedAt: new Date(now - 60 * 60 * 1000).toISOString(),
        installedAt: null,
        lastShownAt: null,
      }, now),
    ).toBe(false);

    expect(
      shouldAutoShowInstallPrompt({
        dismissedAt: new Date(now - 5 * 24 * 60 * 60 * 1000).toISOString(),
        installedAt: null,
        lastShownAt: null,
      }, now),
    ).toBe(true);
  });

  it('shows the branded install prompt and triggers the browser prompt', async () => {
    vi.useFakeTimers();
    window.localStorage.clear();
    document.body.innerHTML = '<button data-install-button hidden>Install</button>';
    document.body.dataset.page = 'add';
    window.matchMedia = vi.fn().mockImplementation(() => ({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));

    setupInstallPrompt();

    const prompt = vi.fn().mockResolvedValue(undefined);
    const installEvent = new Event('beforeinstallprompt');
    installEvent.prompt = prompt;
    installEvent.userChoice = Promise.resolve({ outcome: 'accepted' });
    window.dispatchEvent(installEvent);

    await vi.advanceTimersByTimeAsync(1900);

    const banner = document.getElementById('installPromptBanner');
    expect(banner.hidden).toBe(false);
    expect(document.querySelector('[data-install-button]').hidden).toBe(false);

    banner.querySelector('[data-install-cta]').click();
    await Promise.resolve();
    await Promise.resolve();

    expect(prompt).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });
});
