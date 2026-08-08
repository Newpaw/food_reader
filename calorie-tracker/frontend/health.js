import {
  apiFetch,
  formatDateTime,
  getJsonOrThrow,
  setupPage,
  showStatus,
} from './common.js?v=20260403-11';

let ouraStatus = null;
let healthSummary = null;

const CHART_COLORS = {
  intake: '#d96b3b',
  burn: '#5e7a66',
  readiness: '#2f6f62',
  sleep: '#7c6aa6',
  hrv: '#c47b2c',
};

function isCzech() {
  return (document.documentElement.lang || '').toLowerCase().startsWith('cs');
}

function copy(cs, en) {
  return isCzech() ? cs : en;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
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
  document.getElementById('energyChartEyebrow').textContent = copy('Energie', 'Energy');
  document.getElementById('energyChartHeading').textContent = copy('Příjem vs. výdej', 'Intake vs expenditure');
  document.getElementById('recoveryChartEyebrow').textContent = copy('Regenerace', 'Recovery');
  document.getElementById('recoveryChartHeading').textContent = copy('Readiness & spánek', 'Readiness & sleep');
  document.getElementById('hrvChartEyebrow').textContent = copy('Hloubka regenerace', 'Recovery depth');
  document.getElementById('hrvChartHeading').textContent = copy('Trend HRV', 'HRV trend');
  document.getElementById('coachEyebrow').textContent = copy('AI interpretace', 'AI interpretation');
  document.getElementById('coachHeading').textContent = copy('Health Coach', 'Health Coach');
  document.getElementById('coachSupport').textContent = copy(
    'Jedno praktické doporučení opřené o zvolené období a tvoje vlastní data.',
    'One practical recommendation grounded in the selected period and your own data.',
  );
  document.getElementById('generateCoachButton').textContent = copy('Vygenerovat doporučení', 'Generate recommendation');
  const coachEmpty = document.getElementById('coachEmpty');
  if (coachEmpty) {
    coachEmpty.textContent = copy(
      'Po připojení Oury si nech vygenerovat doporučení pro dnešek.',
      'After connecting Oura, generate a recommendation for today.',
    );
  }
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
  const coachButton = document.getElementById('generateCoachButton');

  if (!ouraStatus?.configured) {
    target.innerHTML = `<div class="health-connection-message">${copy(
      'Oura není nakonfigurovaná. Doplň serverové OAuth proměnné.',
      'Oura is not configured. Add the server OAuth variables.',
    )}</div>`;
    syncButton.hidden = true;
    connectButton.hidden = true;
    coachButton.disabled = true;
    return;
  }

  if (!ouraStatus.connected) {
    target.innerHTML = `<div class="health-connection-message">${copy(
      'Oura účet zatím není připojený.',
      'Oura account is not connected yet.',
    )}</div>`;
    syncButton.hidden = true;
    connectButton.hidden = false;
    coachButton.disabled = true;
    return;
  }

  syncButton.hidden = false;
  connectButton.hidden = true;
  coachButton.disabled = false;
  const lastSync = ouraStatus.last_sync_at ? formatDateTime(ouraStatus.last_sync_at) : '-';
  target.innerHTML = `
    <div class="health-connection-item"><span>${copy('Oura', 'Oura')}</span><strong class="health-connected-dot">${copy('Připojeno', 'Connected')}</strong></div>
    <div class="health-connection-item"><span>${copy('Sync', 'Sync')}</span><strong>${escapeHtml(lastSync)}</strong></div>
    <div class="health-connection-item"><span>${copy('Historie', 'History')}</span><strong>${ouraStatus.synced_days ?? 0} ${copy('dní', 'days')}</strong></div>
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
  const balanceClass = balance === null ? '' : balance < 0 ? 'health-stat-negative' : 'health-stat-positive';
  cards.innerHTML = `
    <article class="health-stat-card ${balanceClass}">
      <span>${copy('Prům. bilance', 'Avg balance')}</span>
      <strong>${balance === null ? '-' : `${balance > 0 ? '+' : ''}${balance}`}</strong>
      <small>kcal / ${copy('den', 'day')}</small>
    </article>
    <article class="health-stat-card">
      <span>${copy('Readiness', 'Readiness')}</span>
      <strong>${fmt(summary.average_readiness)}</strong>
      <small>${copy('průměr', 'average')}</small>
    </article>
    <article class="health-stat-card">
      <span>${copy('Sleep score', 'Sleep score')}</span>
      <strong>${fmt(summary.average_sleep_score)}</strong>
      <small>${copy('průměr', 'average')}</small>
    </article>
    <article class="health-stat-card">
      <span>${copy('Poslední váha', 'Latest weight')}</span>
      <strong>${fmt(summary.latest_weight_kg)}</strong>
      <small>kg</small>
    </article>
  `;
  note.textContent = copy(
    `Pokrytí dat: jídlo ${summary.days_with_food} dní · Oura ${summary.days_with_oura} dní`,
    `Data coverage: food ${summary.days_with_food} days · Oura ${summary.days_with_oura} days`,
  );
}

function chartLegend(targetId, items) {
  const target = document.getElementById(targetId);
  target.innerHTML = items
    .map((item) => `<span><i style="--legend-color:${item.color}"></i>${escapeHtml(item.label)}</span>`)
    .join('');
}

function chartEmpty(targetId) {
  document.getElementById(targetId).innerHTML = `<div class="health-chart-empty">${copy(
    'Pro tento graf zatím nejsou data.',
    'No data for this chart yet.',
  )}</div>`;
}

function renderLineChart(targetId, rows, series, options = {}) {
  const target = document.getElementById(targetId);
  const width = 800;
  const height = 260;
  const padding = { top: 18, right: 18, bottom: 38, left: 54 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const values = [];
  rows.forEach((row) => {
    series.forEach((item) => {
      const value = item.value(row);
      if (Number.isFinite(value)) values.push(Number(value));
    });
  });

  if (!rows.length || !values.length) {
    chartEmpty(targetId);
    return;
  }

  let min = Number.isFinite(options.min) ? options.min : Math.min(...values);
  let max = Number.isFinite(options.max) ? options.max : Math.max(...values);
  if (options.includeZero) min = Math.min(0, min);
  if (min === max) {
    min -= 1;
    max += 1;
  }
  if (!Number.isFinite(options.min) && !options.includeZero) {
    const spread = max - min;
    min = Math.max(0, min - spread * 0.12);
    max += spread * 0.12;
  }

  const x = (index) => padding.left + (rows.length === 1 ? plotWidth / 2 : (index / (rows.length - 1)) * plotWidth);
  const y = (value) => padding.top + ((max - value) / (max - min)) * plotHeight;
  const gridLines = 4;
  const grid = [];
  for (let i = 0; i <= gridLines; i += 1) {
    const value = max - ((max - min) * i) / gridLines;
    const yy = padding.top + (plotHeight * i) / gridLines;
    grid.push(`<line x1="${padding.left}" y1="${yy}" x2="${width - padding.right}" y2="${yy}" class="chart-grid-line" />`);
    grid.push(`<text x="${padding.left - 10}" y="${yy + 4}" text-anchor="end" class="chart-axis-label">${Math.round(value)}</text>`);
  }

  const paths = series.map((item) => {
    const points = rows
      .map((row, index) => {
        const value = item.value(row);
        return Number.isFinite(value) ? `${x(index).toFixed(1)},${y(Number(value)).toFixed(1)}` : null;
      })
      .filter(Boolean)
      .join(' ');

    const dots = rows.length <= 35
      ? rows.map((row, index) => {
          const value = item.value(row);
          if (!Number.isFinite(value)) return '';
          const day = row.day || '';
          return `<circle cx="${x(index)}" cy="${y(Number(value))}" r="3.2" fill="${item.color}" class="chart-dot"><title>${escapeHtml(day)} · ${escapeHtml(item.label)}: ${Math.round(Number(value) * 10) / 10}${item.suffix || ''}</title></circle>`;
        }).join('')
      : '';

    return `<polyline points="${points}" fill="none" stroke="${item.color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" class="chart-line" />${dots}`;
  }).join('');

  const labelIndexes = rows.length <= 2 ? rows.map((_, index) => index) : [0, Math.floor((rows.length - 1) / 2), rows.length - 1];
  const xLabels = [...new Set(labelIndexes)].map((index) => {
    const day = rows[index]?.day || '';
    const shortDay = day.length >= 10 ? `${day.slice(8, 10)}.${day.slice(5, 7)}.` : day;
    return `<text x="${x(index)}" y="${height - 12}" text-anchor="middle" class="chart-axis-label">${escapeHtml(shortDay)}</text>`;
  }).join('');

  target.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" class="health-chart-svg" aria-hidden="true">
      ${grid.join('')}
      ${paths}
      ${xLabels}
    </svg>
  `;
}

function renderCharts() {
  const rows = healthSummary?.days || [];

  chartLegend('energyChartLegend', [
    { label: copy('Příjem', 'Intake'), color: CHART_COLORS.intake },
    { label: copy('Výdej', 'Expenditure'), color: CHART_COLORS.burn },
  ]);
  renderLineChart('energyChart', rows, [
    { label: copy('Příjem', 'Intake'), color: CHART_COLORS.intake, suffix: ' kcal', value: (row) => Number(row.nutrition?.calories) || null },
    { label: copy('Výdej', 'Expenditure'), color: CHART_COLORS.burn, suffix: ' kcal', value: (row) => Number(row.oura?.total_calories) || null },
  ], { includeZero: true });

  chartLegend('recoveryChartLegend', [
    { label: 'Readiness', color: CHART_COLORS.readiness },
    { label: copy('Spánek', 'Sleep'), color: CHART_COLORS.sleep },
  ]);
  renderLineChart('recoveryChart', rows, [
    { label: 'Readiness', color: CHART_COLORS.readiness, value: (row) => Number(row.oura?.readiness_score) || null },
    { label: copy('Spánek', 'Sleep'), color: CHART_COLORS.sleep, value: (row) => Number(row.oura?.sleep_score) || null },
  ], { min: 0, max: 100 });

  chartLegend('hrvChartLegend', [
    { label: 'HRV', color: CHART_COLORS.hrv },
  ]);
  renderLineChart('hrvChart', rows, [
    { label: 'HRV', color: CHART_COLORS.hrv, suffix: ' ms', value: (row) => Number(row.oura?.average_hrv_ms) || null },
  ]);
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
        <article class="subtle-panel health-insight-card">
          <strong>${escapeHtml(insight.title)}</strong>
          <p class="panel-note">${escapeHtml(insight.detail)}</p>
        </article>
      `,
    )
    .join('');
}

function renderCoach(payload) {
  const target = document.getElementById('healthCoach');
  const evidence = Array.isArray(payload?.evidence) ? payload.evidence : [];
  const evidenceHtml = evidence.length
    ? `<ul class="health-coach-evidence">${evidence.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`
    : '';
  target.innerHTML = `
    <article class="health-coach-card">
      <p class="eyebrow">${copy('Doporučení pro dnešek', 'Recommendation for today')} · ${copy('jistota', 'confidence')}: ${escapeHtml(payload?.confidence || 'low')}</p>
      <h3>${escapeHtml(payload?.headline || 'Health Coach')}</h3>
      <p>${escapeHtml(payload?.recommendation || '')}</p>
      ${evidenceHtml}
    </article>
  `;
}

function resetCoach() {
  const target = document.getElementById('healthCoach');
  target.innerHTML = `<div class="empty-state compact" id="coachEmpty">${copy(
    'Po připojení Oury si nech vygenerovat doporučení pro dnešek.',
    'After connecting Oura, generate a recommendation for today.',
  )}</div>`;
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
      const balanceClass = Number(balance) < 0 ? 'daily-balance-negative' : Number(balance) > 0 ? 'daily-balance-positive' : '';
      return `
        <div class="daily-row health-daily-row">
          <div class="health-daily-date">
            <strong>${escapeHtml(row.day)}</strong>
            <span>${copy('Protein', 'Protein')} ${fmt(nutrition.protein_g, ' g')}</span>
          </div>
          <div class="health-daily-energy">
            <span>${copy('Příjem', 'Intake')} <strong>${nutrition.calories || 0}</strong></span>
            <span>${copy('Výdej', 'Burn')} <strong>${fmt(oura.total_calories)}</strong></span>
            <span class="${balanceClass}">${copy('Bilance', 'Balance')} <strong>${balanceText}</strong></span>
          </div>
          <div class="health-daily-recovery">
            <strong>R ${fmt(oura.readiness_score)} · S ${fmt(oura.sleep_score)}</strong>
            <span>HRV ${fmt(oura.average_hrv_ms, ' ms')} · ${fmt(oura.steps, copy(' kroků', ' steps'))}</span>
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
  resetCoach();
  if (!ouraStatus?.connected) {
    healthSummary = null;
    renderSummary();
    renderCharts();
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
  renderCharts();
  renderInsights();
  renderDaily();
}

function analysisParams() {
  const from = document.getElementById('healthFrom').value;
  const to = document.getElementById('healthTo').value;
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Prague';
  const locale = isCzech() ? 'cs' : 'en';
  return `start_date=${encodeURIComponent(from)}&end_date=${encodeURIComponent(to)}&timezone=${encodeURIComponent(timezone)}&locale=${locale}`;
}

async function generateCoach() {
  const status = document.getElementById('coachStatus');
  const button = document.getElementById('generateCoachButton');
  if (!ouraStatus?.connected) {
    showStatus(status, copy('Nejdřív připoj Ouru.', 'Connect Oura first.'), 'info');
    return;
  }
  button.disabled = true;
  showStatus(status, copy('Analyzuji tvoje vlastní trendy…', 'Analyzing your personal trends…'), 'info');
  try {
    const response = await apiFetch(`/oura/coach?${analysisParams()}`, { method: 'POST' });
    const payload = await getJsonOrThrow(response, copy('Health Coach selhal', 'Health Coach failed'));
    renderCoach(payload);
    showStatus(
      status,
      payload.available
        ? copy('Doporučení vychází z aktuálně zvolených dat.', 'Recommendation is grounded in the selected data.')
        : payload.recommendation,
      payload.available ? 'success' : 'info',
    );
  } catch (error) {
    showStatus(status, error.message, 'danger');
  } finally {
    button.disabled = !ouraStatus?.connected;
  }
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
  const syncResult = params.get('sync');
  if (!result) {
    return;
  }
  const status = document.getElementById('ouraHealthStatus');
  if (result === 'connected' && syncResult === 'warning') {
    showStatus(
      status,
      copy(
        'Oura je připojená, ale první synchronizace nedoběhla. Použij tlačítko Synchronizovat Ouru.',
        'Oura is connected, but the initial sync did not complete. Use Sync Oura.',
      ),
      'info',
    );
  } else if (result === 'connected') {
    showStatus(status, copy('Oura je připojená a první historie byla synchronizovaná.', 'Oura is connected and initial history was synced.'), 'success');
  } else {
    showStatus(status, copy('Připojení Oury se nepodařilo.', 'Oura connection failed.'), 'danger');
  }
  params.delete('oura');
  params.delete('reason');
  params.delete('sync');
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
  document.getElementById('generateCoachButton').addEventListener('click', generateCoach);
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
