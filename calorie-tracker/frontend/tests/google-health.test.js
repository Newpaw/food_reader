import { readFileSync } from 'node:fs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

let configured = false;
let records = [];
let daily = [];
const calls = [];
vi.mock('../common.js?v=20260403-11', () => ({
  setupPage: vi.fn(async () => ({ id: 1 })),
  apiFetch: vi.fn(async (url) => {
    calls.push(url);
    return { ok: true, json: async () => url.startsWith('/google-health/status') ? {
      configured, connected: configured, missing_scopes: [], last_sync_at: null,
    } : { records, daily } };
  }),
  getJsonOrThrow: async (response) => response.json(),
  showStatus: (target, message) => { target.textContent = message; },
  formatDateTime: () => 'Unknown',
}));

beforeEach(() => {
  vi.resetModules(); configured = false; records = []; daily = []; calls.length = 0;
  const html = readFileSync(`${process.cwd()}/google-health.html`, 'utf8');
  document.body.innerHTML = html.slice(html.indexOf('<body'), html.indexOf('</body>') + 7);
  document.documentElement.lang = 'en';
});

describe('Google Health screen', () => {
  it('shows inactive integration without offering a broken connection', async () => {
    await import('../google-health.js');
    expect(document.getElementById('ghConnect').disabled).toBe(true);
    expect(document.getElementById('ghSync').disabled).toBe(true);
    expect(document.getElementById('ghConnection').textContent).toContain('not active');
  });
  it('renders real zero, missing values and escaped provider details', async () => {
    configured = true;
    daily = [{ day: '2026-10-08', steps: 0, sleep_minutes: 450, weight_kg: 81.2 }];
    records = [{ day: '2026-10-08', data_type: 'exercise', data: { exercise: { notes: '<img src=x onerror=alert(1)>' } } }];
    await import('../google-health.js');
    expect(document.getElementById('ghTableBody').textContent).toContain('0');
    expect(document.getElementById('ghTableBody').textContent).toContain('7.5');
    expect(document.getElementById('ghTableBody').textContent).toContain('—');
    expect(document.getElementById('ghRecords').querySelector('img')).toBeNull();
    expect(document.getElementById('ghRecords').textContent).toContain('<img');
    expect(document.getElementById('ghExport').disabled).toBe(false);
  });
  it('rejects reversed periods before requesting data', async () => {
    await import('../google-health.js');
    calls.length = 0;
    document.getElementById('ghFrom').value = '2026-10-08';
    document.getElementById('ghTo').value = '2026-10-01';
    document.getElementById('ghRange').dispatchEvent(new Event('submit', { cancelable: true }));
    await Promise.resolve(); await Promise.resolve();
    expect(calls).toHaveLength(0);
    expect(document.getElementById('ghStatus').textContent).toContain('1 to 90 days');
  });
});
