import { expect, test } from '@playwright/test';


test.use({ serviceWorkers: 'block' });

const profile = {
  id: 1,
  user_id: 1,
  height_cm: 180,
  weight_kg: 82,
  age: 31,
  gender: 'male',
  activity_level: 'moderately_active',
  goal: 'maintenance',
  dietary_preference: 'none',
  custom_calories: null,
  custom_protein_g: null,
  custom_carbs_g: null,
  custom_fats_g: null,
  custom_fiber_g: null,
  bmr: 1800,
  tdee: 2400,
  target_calories: 2400,
  target_protein_g: 180,
  target_carbs_g: 240,
  target_fats_g: 80,
  target_fiber_g: 34,
  adaptive_calories_enabled: true,
  adaptive_target_calories: 2475,
  adaptive_target_updated_on: '2026-08-09',
  weight_source: 'manual',
  weight_measured_at: null,
  created_at: '2026-08-01T10:00:00Z',
  updated_at: '2026-08-09T10:00:00Z',
};

const targets = {
  calories: 2475,
  base_calories: 2400,
  protein_g: 180,
  carbs_g: 251,
  fats_g: 84,
  fiber_g: 34,
  calculation_method: 'Adaptive target',
  calculation_method_code: 'adaptive',
  bmr: 1800,
  tdee: 2400,
  last_updated: '2026-08-09T10:00:00Z',
  adaptive: {
    enabled: true,
    applied: true,
    status: 'active',
    source: 'oura',
    data_days: 12,
    burn_baseline: 2650,
    adjustment_kcal: 75,
    recommended_min_calories: 2375,
    recommended_max_calories: 2575,
  },
};

async function mockApi(page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('token', 'adaptive-layout-test');
    window.localStorage.setItem('food-reader:locale', 'cs');
  });

  await page.route('http://localhost:8000/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    const responses = {
      '/users/me': { name: 'Tester', email: 'tester@example.com' },
      '/profile': profile,
      '/profile/targets': targets,
      '/withings/status': { configured: true, connected: false },
      '/me/summary': { days: [] },
      '/me/meals': [],
      '/withings/measurements': [],
    };
    const body = responses[path];
    await route.fulfill({
      status: body === undefined ? 503 : 200,
      contentType: 'application/json',
      body: JSON.stringify(body ?? { detail: 'Unexpected adaptive layout request' }),
    });
  });
}

for (const width of [320, 390, 768, 979, 980, 1440]) {
  test(`adaptive profile and metrics fit at ${width}px`, async ({ page }) => {
    await mockApi(page);
    await page.setViewportSize({ width, height: 900 });

    await page.goto('/profile.html');
    await expect(page.locator('.adaptive-target-card[data-status="active"]')).toBeVisible();
    await expect(page.locator('#adaptiveCaloriesEnabled')).toBeChecked();
    const toggle = await page.locator('.adaptive-toggle-card').boundingBox();
    expect(toggle.height).toBeGreaterThanOrEqual(44);
    const profileWidth = await page.evaluate(() => Math.max(document.body.scrollWidth, document.documentElement.scrollWidth));
    expect(profileWidth).toBe(width);

    const profilePanels = page.locator('.profile-page-layout > .panel');
    const inputPanel = await profilePanels.nth(0).boundingBox();
    const targetPanel = await profilePanels.nth(1).boundingBox();
    const devicesPanel = await profilePanels.nth(2).boundingBox();
    expect(inputPanel).not.toBeNull();
    expect(targetPanel).not.toBeNull();
    expect(devicesPanel).not.toBeNull();

    if (width < 980) {
      expect(Math.abs(targetPanel.x - inputPanel.x)).toBeLessThanOrEqual(2);
      expect(targetPanel.y).toBeGreaterThan(inputPanel.y);
      expect(Math.abs(devicesPanel.x - inputPanel.x)).toBeLessThanOrEqual(2);
    } else {
      expect(targetPanel.x).toBeGreaterThan(inputPanel.x);
      expect(Math.abs(devicesPanel.x - targetPanel.x)).toBeLessThanOrEqual(2);
      expect(devicesPanel.y).toBeGreaterThan(targetPanel.y);
    }

    if (width < 980) {
      await expect(page.locator('.bottom-nav')).toBeVisible();
    } else {
      await expect(page.locator('.desktop-nav')).toBeVisible();
      await expect(page.locator('.bottom-nav')).toBeHidden();
    }

    await page.goto('/metrics.html');
    await expect(page.locator('.adaptive-goal-chip').first()).toBeVisible();
    const metricsWidth = await page.evaluate(() => Math.max(document.body.scrollWidth, document.documentElement.scrollWidth));
    expect(metricsWidth).toBe(width);
    if (width < 980) {
      await expect(page.locator('.bottom-nav')).toBeVisible();
    }
  });
}
