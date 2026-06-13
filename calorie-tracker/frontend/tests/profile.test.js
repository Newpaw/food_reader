import { describe, expect, it } from 'vitest';

import { buildProfilePayload, buildWithingsStatusMarkup, hasCustomOverrides } from '../profile.js';


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
    });

    expect(payload.height_cm).toBe(180);
    expect(payload.custom_calories).toBeNull();
    expect(payload.custom_protein_g).toBe(190);
    expect(payload.custom_fiber_g).toBeNull();
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
});
