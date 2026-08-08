import {
  apiFetch,
  formatDateTime,
  getJsonOrThrow,
  setupPage,
  showStatus,
} from './common.js?v=20260403-11';

let ouraStatus = null;
let healthSummary = null;

function isCzech() {
  return (document.documentElement.lang || '').toLowerCase().startsWith('cs');
}

function copy(cs, en) {
  return isCzech() ? cs : en;
}

function localDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function setRange(daysBack) {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - daysBack);
  document.getElementById('healthFrom').value = localDateKey(start);
  document.getElementById('healthTo').value = localDateKey(end);
}

function applyStaticCopy() {
  document.getElementById('healthEyebrow').textContent = copy('Osobní health OS', 'Personal health OS');
  document.getElementById('healthHeading').textContent = copy('Jídlo + Oura + tělesná data', 'Food + Oura + body data');
  document.getElementById('healthSupport').textContent = copy(
    'Rozhoduj se podle vlastních dlouhodobých dat, ne podle obecných pouček.',
    'Use your own longitudinal data instead of generic nutrition advice.',
  );
  document.getElementById('syncOuraButton').textContent = copy('Synchronizovat Ouru', 'Sync Oura');
  document.getElementById('connectOuraButton').textContent = copy('Připojit Ouru', 'Connect Oura');
  document.getElementById('rangeEyebrow').textContent = copy('Období', 'Range');
  document.getElementById('rangeHeading').textContent = copy('Okno pro analýzu', 'Analysis window');
  document.getElementById('healthFromLabel').textContent = copy('Od', 'From');
  document.getElementById('healthToLabel').textContent = copy('Do', 'To');
  document.getElementById('healthApplyButton').textContent = copy('Přepočítat', 'Refresh');
  document.getElementById('summaryEyebrow').textContent = copy('Signály', 'Signals');
  document.getElementById('summaryHeading').textContent = copy('Souhrn období', 'Period summary');
  document.getElementById('insightsEyebrow').textContent = copy('Osobní vzorce', 'Personal patterns');
  document.getElementById('insightsHeading').textContent = copy('Co říkají tvoje data', 'What your data says');
  document.getElementById('correlationWarning').textContent = copy(
    'Jde o korelace ve tvých datech, ne o lékařské závěry ani důkaz příčiny.',
    'These are correlations in your own data, not medical conclusions or proof of causality.',
  );
  document.getElementById('dailyEyebrow').textContent = copy('Po dnech', 'Daily view');
  document.getElementById('dailyHeading').textContent = copy('Jídlo vs. výdej a regenerace', 'Food vs expenditure and recovery');
}

function renderConnection() {
  const target = document.getElementById('ouraConnectionSummary');
  const syncButton = document.getElementById('syncOuraButton');
  const connectButton = document.getElementById('connectOuraButton');

  if (!ouraStatus?.configured) {
    target.innerHTML = `<div class="empty-state compact">${copy(
      'Oura není na serveru nakonfigurovaná. Doplň OURA_CLIENT_ID, OURA_CLIENT_SECRET a OURA_REDIRECT_URI.',
      'Oura is not configured on the server. Set OURA_CLIENT_ID, OURA_CLIENT_SECRET and OURA_REDIRECT_URI.',
    )}</div>`;
    syncButton.hidden = true;
    connectButton.hidden = true;
    return;
  }

  if (!ouraStatus.connected) {
    target.innerHTML = `<div class="empty-state compact">${copy(
      'Oura účet zatím není připojený. OAuth přístup drží tokeny pouze na backendu.',
      'Oura is not connected yet. OAuth keeps tokens on the backend only.',
    )}</div>`;
    syncButton.hidden = true;
    connectButton.hidden = false;
    return;
  }

  syncButton.hidden = false;
  connectButton.hidden = true;
  const lastSync = ouraStatus.last_sync_at ? formatDateTime(ouraStatus.last_sync_at) : '-';
  target.innerHTML = `
    <div><strong>${copy('Stav', 'Status')}</strong><span>${copy('Připojeno', 'Connected')}</span></div>
    <div><strong>${copy('Poslední sync', 'Last sync')}</strong><span>${lastSync}</span></div>
    <div><strong>${copy('Uložené dny', 'Stored days')}</strong><span>${ouraStatus.synced_days ?? 0}</span></div>
    <div><strong>${copy('Poslední readiness', 'Latest readiness')}</strong><span>${ouraStatus.latest_readiness ?? '-'}</span></div>
  `;
}

function fmt(value, suffix = '') {
  return value === null || value === undefined ? '-' : `${value}${suffix}`;
}

function renderSummary() {
  const cards = document.getElementById('healthSummaryCards');
  const note = document.getElementById('healthCoverageNote');
  const summary = healthSummary?.summary;
  if (!summary) {
    cards.innerHTML = '';
    note.textContent = '';
    return;
  }
  const balance = summary.average_energy_balance_kcal;
  cards.innerHTML = `
    <article class="stat-card"><span>${copy('Prům. bilance', 'Avg balance')}</span><strong>${balance === null ? '-' : `${balance > 0 ? '+' : ''}${balance} kcal`}</strong></article>
    <article class="stat-card"><span>${copy('Prům. readiness', 'Avg readiness')}</span><strong>${fmt(summary.average_readiness)}</strong></article>
    <article class="stat-card"><span>${copy('Prům. sleep score', 'Avg sleep score')}</span><strong>${fmt(summary.average_sleep_score)}</strong></article>
    <article class="stat-card"><span>${copy('Poslední váha', 'Latest weight')}</span><strong>${fmt(summary.latest_weight_kg, ' kg')}</strong></article>
  `;
  note.textContent = copy(
    `Pokrytí: jídlo ${summary.days_with_food} dní, Oura ${summary.days_with_oura} dní. Energetická bilance = zaznamenaný příjem − Oura total calories.`,
    `Coverage: food ${summary.days_with_food} days, Oura ${summary.days_with_oura} days. Energy balance = logged intake − Oura total calories.`,
  );
}

function renderInsights() {
  const target = document.getElementById('healthInsights');
  const insights = healthSummary?.insights || [];
  if (!insights.length) {
    target.innerHTML = `<div class="empty-state compact">${copy('Zatím není dost dat pro osobní insighty.', 'Not enough data for personal insights yet.')}</div>`;
    return;
  }
  target.innerHTML = insights
    .map(
      (insight) => `
        <article class="subtle-panel">
          <strong>${insight.title}</strong>
          <p class="panel-note">${insight.detail}</p>
        </article>
      `,
    )
    .join('');
}

function renderDaily() {
  const target = document.getElementById('healthDailyList');
  const rows = [...(healthSummary?.days || [])].reverse().slice(0, 31);
  if (!rows.length) {
    target.innerHTML = `<div class="empty-state compact">${copy('Žádná data v období.', 'No data in this range.')}</div>`;
    return;
  }
  target.innerHTML = rows
    .map((row) => {
      const nutrition = row.nutrition || {};
      const oura = row.oura || {};
      const balance = row.energy_balance_kcal;
      const balanceText = balance === null || balance === undefined ? '-' : `${balance > 0 ? '+' : ''}${balance} kcal`;
      return `
        <div class="daily-row">
          <div>
            <strong>${row.day}</strong>
            <span>${copy('Příjem', 'Intake')} ${nutrition.calories || 0} kcal · ${copy('Výdej', 'Burn')} ${fmt(oura.total_calories, ' kcal')} · ${copy('Bilance', 'Balance')} ${balanceText}</span>
          </div>
          <div>
            <strong>R ${fmt(oura.readiness_score)}</strong>
            <span>S ${fmt(oura.sleep_score)} · HRV ${fmt(oura.average_hrv_ms, ' ms')} · ${fmt(oura.steps, ' steps')}</span>
          </div>
        </div>
      `;
    })
    .join('');
}

async function loadStatus() {
  const response = await apiFetch('/oura/status');
  ouraStatus = response.ok ? await response.json() : { configured: false, connected: false };
  renderConnection();
}

async function loadHealthSummary() {
  if (!ouraStatus?.connected) {
    healthSummary = null;
    renderSummary();
    renderInsights();
    renderDaily();
    return;
  }
  const from = document.getElementById('healthFrom').value;
  const to = document.getElementById('healthTo').value;
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Prague';
  const locale = isCzech() ? 'cs' : 'en';
  const response = await apiFetch(
    `/oura/health-summary?start_date=${encodeURIComponent(from)}&end_date=${encodeURIComponent(to)}&timezone=${encodeURIComponent(timezone)}&locale=${locale}`,
  );
  healthSummary = await getJsonOrThrow(response, copy('Nepodařilo se načíst health summary', 'Unable to load health summary'));
  renderSummary();
  renderInsights();
  renderDaily();
}

async function connectOura() {
  const status = document.getElementById('ouraHealthStatus');
  showStatus(status, copy('Otevírám Oura autorizaci…', 'Opening Oura authorization…'), 'info');
  try {
    const response = await apiFetch('/oura/auth-url', { method: 'POST' });
    const payload = await getJsonOrThrow(response, copy('Nepodařilo se spustit Oura OAuth', 'Unable to start Oura OAuth'));
    window.location.href = payload.authorization_url;
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}

async function syncOura() {
  const status = document.getElementById('ouraHealthStatus');
  showStatus(status, copy('Synchronizuji Oura data…', 'Syncing Oura data…'), 'info');
  try {
    const response = await apiFetch('/oura/sync', { method: 'POST' });
    const payload = await getJsonOrThrow(response, copy('Synchronizace Oury selhala', 'Oura sync failed'));
    await loadStatus();
    await loadHealthSummary();
    const warning = payload.warnings?.length ? ` ${copy('Částečné upozornění:', 'Partial warning:')} ${payload.warnings.join('; ')}` : '';
    showStatus(status, `${copy('Synchronizováno dní:', 'Synced days:')} ${payload.synced_days}.${warning}`, payload.warnings?.length ? 'info' : 'success');
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}

function showCallbackResult() {
  const params = new URLSearchParams(window.location.search);
  const result = params.get('oura');
  if (!result) {
    return;
  }
  const status = document.getElementById('ouraHealthStatus');
  if (result === 'connected') {
    showStatus(status, copy('Oura je připojená a první historie byla synchronizovaná.', 'Oura is connected and initial history was synced.'), 'success');
  } else {
    showStatus(status, copy('Připojení Oury se nepodařilo.', 'Oura connection failed.'), 'danger');
  }
  params.delete('oura');
  params.delete('reason');
  const search = params.toString();
  window.history.replaceState({}, '', `${window.location.pathname}${search ? `?${search}` : ''}`);
}

async function init() {
  await setupPage();
  applyStaticCopy();
  setRange(29);
  showCallbackResult();

  document.getElementById('connectOuraButton').addEventListener('click', connectOura);
  document.getElementById('syncOuraButton').addEventListener('click', syncOura);
  document.getElementById('healthFilters').addEventListener('submit', async (event) => {
    event.preventDefault();
    await loadHealthSummary();
  });
  document.querySelectorAll('[data-health-days]').forEach((button) => {
    button.addEventListener('click', async () => {
      setRange(Number(button.dataset.healthDays));
      await loadHealthSummary();
    });
  });

  await loadStatus();
  await loadHealthSummary();

  window.addEventListener('food-reader:localechange', async () => {
    applyStaticCopy();
    renderConnection();
    await loadHealthSummary();
  });
}

document.addEventListener('DOMContentLoaded', init);
