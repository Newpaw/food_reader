import { describe, expect, it } from 'vitest';

import {
  buildAdaptiveTargetMarkup,
  buildProfilePayload,
  buildWithingsStatusMarkup,
  hasCustomOverrides,
} from '../profile.js';


describe('profile payload builder', () => {
  it('converts blank values to null while preserving selected targets', () => {
    const payload = buildProfilePayload({
      height: { value: '180' },
      weight: { value: '82' },
      age: { value: '31' },
      gender: { value: 'male' },
      activityLevel: { value: 'moderately_active' },
      goal: { value: 'maintenance' },
      dietaryPreference: { value: 'high_protein' },
      customCalories: { value: '' },
      customProtein: { value: '190' },
      customCarbs: { value: '' },
      customFats: { value: '80' },
      customFiber: { value: '' },
      adaptiveCaloriesEnabled: { checked: true },
    });

    expect(payload.height_cm).toBe(180);
    expect(payload.custom_calories).toBeNull();
    expect(payload.custom_protein_g).toBe(190);
    expect(payload.custom_fiber_g).toBeNull();
    expect(payload.adaptive_calories_enabled).toBe(true);
  });

  it('detects whether advanced override fields should open', () => {
    expect(hasCustomOverrides({ custom_calories: null, custom_protein_g: null })).toBe(false);
    expect(hasCustomOverrides({ custom_calories: 2400, custom_protein_g: null })).toBe(true);
  });

  it('renders Withings disconnected and connected states', () => {
    expect(buildWithingsStatusMarkup({ configured: true, connected: false })).toContain('Connect Withings');

    const connected = buildWithingsStatusMarkup({
      configured: true,
      connected: true,
      latest_weight_kg: 81.14,
      latest_measured_at: '2026-05-10T08:00:00Z',
      last_sync_at: '2026-05-10T09:00:00Z',
      scope: 'user.metrics',
    });

    expect(connected).toContain('Withings scale is connected.');
    expect(connected).toContain('81.1 kg');
    expect(connected).toContain('Sync Withings');
  });

  it('renders Withings configuration errors', () => {
    expect(buildWithingsStatusMarkup({ configured: false, connected: false })).toContain('not configured');
  });

  it('renders adaptive target states and active breakdown', () => {
    expect(buildAdaptiveTargetMarkup({
      base_calories: 2200,
      adaptive: { status: 'not_connected', enabled: true, applied: false, data_days: 0 },
    })).toContain('Oura is not connected');

    expect(buildAdaptiveTargetMarkup({
      base_calories: 2200,
      adaptive: { status: 'warming_up', enabled: true, applied: false, data_days: 7 },
    })).toContain('7 of 10 complete days');

    const active = buildAdaptiveTargetMarkup({
      base_calories: 2200,
      adaptive: {
        status: 'active',
        enabled: true,
        applied: true,
        data_days: 12,
        burn_baseline: 2450,
        adjustment_kcal: 75,
        recommended_min_calories: 2175,
        recommended_max_calories: 2375,
      },
    });
    expect(active).toContain('Adaptive target is active');
    expect(active).toContain('+75 kcal');
    expect(active).toContain('2175–2375 kcal');

    expect(buildAdaptiveTargetMarkup({
      base_calories: 2200,
      adaptive: { status: 'custom_override', enabled: true, applied: false },
    })).toContain('Custom calorie target is active');
  });
});
