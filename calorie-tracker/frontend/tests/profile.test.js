import { describe, expect, it } from 'vitest';

import { buildProfilePayload } from '../profile.js';


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
});
