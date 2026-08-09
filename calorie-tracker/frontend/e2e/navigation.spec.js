import { expect, test } from '@playwright/test';


test.use({ serviceWorkers: 'block' });

const PAGES = [
  ['index.html', 'add'],
  ['history.html', 'history'],
  ['metrics.html', 'metrics'],
  ['health.html', 'health'],
  ['assistant.html', 'assistant'],
  ['profile.html', 'profile'],
];

async function mockAuthenticatedApi(page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('token', 'navigation-regression-test');
    window.localStorage.setItem('food-reader:locale', 'cs');
  });

  await page.route('http://localhost:8000/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/users/me') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ name: 'Tester', email: 'tester@example.com' }),
      });
      return;
    }

    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Navigation test API stub' }),
    });
  });
}

test('mobile navigation stays fixed and visible on every main page', async ({ page }) => {
  await mockAuthenticatedApi(page);

  for (const [filename, pageId] of PAGES) {
    await page.goto(`/${filename}`);

    const navigation = page.locator('.bottom-nav');
    await expect(navigation).toBeVisible();
    await expect(navigation.locator('a')).toHaveCount(6);
    await expect(navigation.locator(`[data-nav="${pageId}"]`)).toHaveAttribute('aria-current', 'page');

    const layout = await navigation.evaluate((element) => {
      const rect = element.getBoundingClientRect();
      return {
        parentClass: element.parentElement?.className,
        position: window.getComputedStyle(element).position,
        left: rect.left,
        right: rect.right,
        bottom: rect.bottom,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
        documentWidth: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
      };
    });

    expect(layout.parentClass).toContain('app-shell');
    expect(layout.position).toBe('fixed');
    expect(layout.left).toBeGreaterThanOrEqual(0);
    expect(layout.right).toBeLessThanOrEqual(layout.viewportWidth);
    expect(layout.bottom).toBeLessThanOrEqual(layout.viewportHeight);
    expect(layout.documentWidth).toBe(layout.viewportWidth);
  }
});

test('desktop navigation does not clip the brand near its breakpoint', async ({ page }) => {
  await mockAuthenticatedApi(page);
  await page.setViewportSize({ width: 1024, height: 800 });
  await page.goto('/health.html');

  await expect(page.locator('.desktop-nav')).toBeVisible();
  await expect(page.locator('.bottom-nav')).toBeHidden();
  await expect(page.locator('.brand-mark')).toBeVisible();
  await expect(page.locator('.brand-copy')).toBeHidden();

  await page.setViewportSize({ width: 1100, height: 800 });
  await expect(page.locator('.brand-copy')).toBeVisible();

  const brandFits = await page.locator('.brand').evaluate((element) =>
    element.scrollWidth <= element.clientWidth,
  );
  expect(brandFits).toBe(true);
});

test('assistant top bar follows the selected locale', async ({ page }) => {
  await mockAuthenticatedApi(page);
  await page.goto('/assistant.html');

  await expect(page.locator('[data-logout]')).toHaveText('Odhlásit');
});
