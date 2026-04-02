import { expect, test } from '@playwright/test';


const email = process.env.E2E_EMAIL;
const password = process.env.E2E_PASSWORD;

test.beforeEach(async ({ page }) => {
  test.skip(!email || !password, 'E2E_EMAIL and E2E_PASSWORD must be provided.');
});


async function login(page) {
  await page.goto('/login.html');
  await page.getByLabel('Email').first().fill(email);
  await page.getByLabel('Password').first().fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL(/index\.html$/);
  await expect(page.getByRole('heading', { name: /add a meal/i })).toBeVisible();
}


test('user can log in and navigate the main screens', async ({ page }) => {
  await login(page);

  await expect(page.locator('[data-user-greeting]')).not.toHaveText('You');

  await page.goto('/history.html');
  await expect(page.getByRole('heading', { name: /filter history/i })).toBeVisible();

  await page.goto('/metrics.html');
  await expect(page.getByRole('heading', { name: /daily goal status/i })).toBeVisible();

  await page.goto('/profile.html');
  await expect(page.getByRole('heading', { name: /personal settings/i })).toBeVisible();
});


test('user can save profile settings from the frontend', async ({ page }) => {
  await login(page);
  await page.goto('/profile.html');

  await page.locator('#height').fill('182');
  await page.locator('#weight').fill('84');
  await page.locator('#age').fill('35');
  await page.locator('#gender').selectOption('male');
  await page.locator('#activityLevel').selectOption('moderately_active');
  await page.locator('#goal').selectOption('maintenance');
  await page.locator('#dietaryPreference').selectOption('high_protein');
  await page.getByRole('button', { name: 'Save profile' }).click();

  await expect(page.locator('#profileStatus')).toContainText('Profile saved.');
  await expect(page.locator('#profileTargets')).toContainText('Calories');
});


test('user can add a text meal and see it in the review panel and history', async ({ page }) => {
  const uniqueLabel = `e2e meal ${Date.now()}`;

  await login(page);

  await page.locator('[data-capture-mode="text"]').click();
  await page.getByLabel('Describe the meal').fill(`Greek yogurt bowl with berries and oats ${uniqueLabel}`);
  await page.getByRole('button', { name: 'Analyze meal text' }).click();

  await expect(page.locator('#captureStatus')).toContainText('Meal added.');
  await expect(page.locator('#analysisPanel')).toBeVisible();

  await page.locator('#analysisCalories').fill('611');
  await page.locator('#analysisNotes').fill(`Created by playwright ${uniqueLabel}`);
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(page.locator('#analysisStatus')).toContainText('Meal updated.');
  await expect(page.locator('#analysisPanel')).toContainText('611');

  await page.goto('/history.html');
  await page.getByRole('button', { name: 'Today' }).click();
  await expect(page.locator('#historyList')).toContainText(uniqueLabel);
});


test('metrics screen loads without frontend errors after login', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(String(error)));

  await login(page);
  await page.goto('/metrics.html');

  await expect(page.locator('#metricsStatus')).toBeHidden();
  await expect(page.locator('#metricsStats')).toBeVisible();
  await expect(page.locator('#dailyList')).toBeVisible();
  expect(errors).toEqual([]);
});
