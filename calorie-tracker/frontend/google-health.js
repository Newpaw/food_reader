import { apiFetch, getJsonOrThrow, setupPage, showStatus, formatDateTime } from './common.js?v=20260403-11';

const el = (id) => document.getElementById(id);
const cs = () => document.documentElement.lang.startsWith('cs');
const copy = (czech, english) => cs() ? czech : english;
let connection = null;
let payload = { daily: [], records: [] };
let busy = false;
let visibleRecords = 30;
const types = {
  steps: ['Kroky', 'Steps'], sleep: ['Spánek', 'Sleep'], exercise: ['Tréninky', 'Workouts'],
  weight: ['Hmotnost', 'Weight'], 'body-fat': ['Tělesný tuk', 'Body fat'],
  'daily-resting-heart-rate': ['Klidový tep', 'Resting heart rate'],
  'daily-heart-rate-variability': ['Variabilita tepu (HRV)', 'Heart rate variability (HRV)'],
};
const typeName = (key) => types[key] ? copy(...types[key]) : key;
const number = (value, digits = 0) => value == null ? '—' : Number(value).toLocaleString(cs() ? 'cs-CZ' : 'en-US', { maximumFractionDigits: digits });
function element(tag, text) { const node = document.createElement(tag); node.textContent = text; return node; }
function notice(message, tone = 'info') { showStatus(el('ghStatus'), message, tone); }

function errorMessage(reason) {
  const errors = {
    NOT_CONFIGURED: ['Propojení ještě není aktivované. Správce aplikace musí nastavit přístup u Googlu.', 'This integration is not active yet. The app administrator must configure Google access.'],
    ACCOUNT_NOT_LINKED: ['Nejdřív se přihlas do mobilní aplikace Google Health a vytvoř profil nebo převeď účet Fitbit. Potom se vrať a účet propoj.', 'First sign in to the Google Health mobile app and create a profile or migrate your Fitbit account, then return to connect.'],
    MISSING_PERMISSIONS: ['Povol alespoň jeden typ zdravotních dat a zkus propojení znovu.', 'Allow at least one health data permission and reconnect.'],
    RECONNECT_REQUIRED: ['Přístup vypršel nebo byl zrušen. Propoj účet znovu.', 'Access expired or was revoked. Reconnect your account.'],
    access_denied: ['Propojení bylo zrušeno. Můžeš to zkusit znovu.', 'Connection was cancelled. You can try again.'],
    INVALID_STATE: ['Platnost propojení vypršela. Spusť ho prosím znovu.', 'The connection request expired. Please start again.'],
    OFFLINE_ACCESS_REQUIRED: ['Google neposkytl přístup pro opakované stažení. Propoj účet znovu a potvrď souhlas.', 'Google did not grant offline access. Reconnect and confirm consent.'],
    SYNC_TOO_LARGE: ['Dat je příliš mnoho. Zvol kratší období.', 'There is too much data. Choose a shorter period.'],
    REVOCATION_FAILED: ['Odpojení se nepodařilo dokončit. Zkus to znovu za chvíli.', 'Disconnection could not be completed. Please retry shortly.'],
  };
  return errors[reason] ? copy(...errors[reason]) : copy('Operaci se nepodařilo dokončit. Zkontroluj připojení a zkus to znovu.', 'The operation could not be completed. Check your connection and try again.');
}
function updateButtons() {
  el('ghConnect').disabled = busy || !connection?.configured;
  el('ghDisconnect').hidden = !connection?.connected;
  el('ghDisconnect').disabled = busy;
  el('ghSync').disabled = busy || !connection?.connected || !connection?.configured;
  el('ghView').disabled = busy;
  el('ghExport').disabled = busy || !payload.records.length;
}
function renderCopy() {
  const labels = {
    ghTitle: ['Aktivita, spánek a tělesné hodnoty', 'Your activity, sleep and body measurements'],
    ghDisclosure: ['Po propojení uvidíš kroky a tréninky, spánek a tělesné hodnoty z Google Health / Fitbit. Vyžádáme přístup pouze ke čtení těchto tří skupin dat. Souhlas vybereš u Googlu. Data se uloží k tvému účtu ve Food Readeru; odpojením je smažeš.', 'Connect to view activity and workouts, sleep and body measurements from Google Health / Fitbit. We request read-only access to these three data groups. Choose permissions at Google. Data is saved to your Food Reader account; disconnecting deletes it.'],
    ghConnect: [connection?.connected ? 'Upravit souhlas / znovu propojit' : 'Propojit Google Health', connection?.connected ? 'Update consent / reconnect' : 'Connect Google Health'],
    ghDisconnect: ['Odpojit a smazat data', 'Disconnect and delete data'], ghBack: ['Zpět na Zdraví', 'Back to Health'],
    ghRangeTitle: ['Vyber období', 'Choose a period'], ghFromLabel: ['Od', 'From'], ghToLabel: ['Do', 'To'],
    ghView: ['Zobrazit uložená data', 'View saved data'], ghSync: ['Stáhnout z Googlu', 'Download from Google'],
    ghExport: ['Export JSON', 'Export JSON'], ghCaption: ['Denní přehled', 'Daily overview'],
    ghRangeHint: ['Lze vybrat 1 až 90 dní. Zobrazují se hodnoty v místním čase zdroje. Chybějící měření je označeno pomlčkou.', 'Select 1 to 90 days. Values use the source local time. Missing measurements are shown as a dash.'],
    ghDetailsTitle: ['Detail záznamů', 'Record details'], ghTypeLabel: ['Typ dat', 'Data type'],
    ghLinkAccount: ['Nastavit Google Health', 'Set up Google Health'], ghMore: ['Zobrazit další', 'Show more'],
  };
  for (const [id, text] of Object.entries(labels)) el(id).textContent = copy(...text);
  el('ghConnection').textContent = !connection ? copy('Načítání…', 'Loading…') : !connection.configured ? errorMessage('NOT_CONFIGURED') : connection.connected ? `${copy('Propojeno', 'Connected')} · ${copy('Poslední stažení', 'Last download')}: ${formatDateTime(connection.last_sync_at)}` : copy('Účet zatím není propojený.', 'Your account is not connected yet.');
  el('ghPermissions').hidden = !connection?.missing_scopes.length;
  el('ghPermissions').textContent = copy('Některé skupiny dat nejsou povolené. Přehled funguje s uděleným souhlasem; další data zpřístupníš přes „Upravit souhlas“.', 'Some data groups are not allowed. The overview uses granted permissions; enable more through “Update consent”.');
  const selected = el('ghType').value;
  el('ghType').replaceChildren(new Option(copy('Všechny typy', 'All types'), ''), ...Object.keys(types).map((key) => new Option(typeName(key), key)));
  el('ghType').value = selected;
  renderData(); updateButtons();
}
function renderData() {
  const headings = [copy('Den', 'Day'), copy('Kroky', 'Steps'), copy('Spánek (h)', 'Sleep (h)'), copy('Klidový tep', 'Resting HR'), 'HRV (ms)', 'kg', copy('Tuk (%)', 'Fat (%)'), copy('Tréninky', 'Workouts')];
  const head = document.createElement('tr'); headings.forEach((text) => head.append(element('th', text)));
  el('ghTableHead').replaceChildren(head);
  el('ghTableBody').replaceChildren(...payload.daily.slice().reverse().map((day) => {
    const tr = document.createElement('tr');
    [day.day, number(day.steps), number(day.sleep_minutes == null ? null : day.sleep_minutes / 60, 1), number(day.resting_heart_rate_bpm), number(day.hrv_ms, 1), number(day.weight_kg, 1), number(day.body_fat_percent, 1), number(day.workouts)].forEach((value) => tr.append(element('td', value)));
    return tr;
  }));
  const stepDays = payload.daily.filter((day) => day.steps != null);
  const sleepDays = payload.daily.filter((day) => day.sleep_minutes != null);
  const cards = [[copy('Kroky za období', 'Steps in period'), stepDays.length ? number(stepDays.reduce((sum, day) => sum + day.steps, 0)) : '—'],
    [copy('Průměrný spánek', 'Average sleep'), sleepDays.length ? `${number(sleepDays.reduce((sum, day) => sum + day.sleep_minutes, 0) / sleepDays.length / 60, 1)} h` : '—'],
    [copy('Stažené záznamy', 'Downloaded records'), number(payload.records.length)]];
  el('ghCards').replaceChildren(...cards.map(([label, value]) => { const card = element('div', ''); card.className = 'gh-card'; card.append(element('strong', value), element('span', label)); return card; }));
  el('ghEmpty').hidden = !!payload.records.length;
  el('ghEmpty').textContent = copy('Pro toto období zatím nemáš stažená data. Propoj účet a stáhni data z Googlu.', 'No data has been downloaded for this period. Connect your account and download data from Google.');
  renderRecords();
}
function renderRecords() {
  const selected = el('ghType').value;
  const records = payload.records.filter((row) => !selected || row.data_type === selected).slice().reverse();
  el('ghRecords').replaceChildren(...records.slice(0, visibleRecords).map((row) => {
    const details = document.createElement('details');
    details.append(element('summary', `${row.day} · ${typeName(row.data_type)}`), element('pre', JSON.stringify(row.data, null, 2)));
    return details;
  }));
  el('ghMore').hidden = records.length <= visibleRecords;
}
function rangeQuery() {
  const start = el('ghFrom').value; const end = el('ghTo').value;
  const span = (new Date(`${end}T00:00:00Z`) - new Date(`${start}T00:00:00Z`)) / 86400000;
  if (!start || !end || !Number.isFinite(span) || span < 0 || span >= 90) throw new Error('RANGE_INVALID');
  return new URLSearchParams({ start_date: start, end_date: end }).toString();
}
async function loadConnection() { connection = await getJsonOrThrow(await apiFetch('/google-health/status')); renderCopy(); }
async function loadData() { payload = await getJsonOrThrow(await apiFetch(`/google-health/data?${rangeQuery()}`)); visibleRecords = 30; renderData(); }
async function run(action) {
  if (busy) return;
  busy = true; updateButtons();
  try { await action(); } catch (error) {
    notice(error.message === 'RANGE_INVALID' ? copy('Vyber období 1 až 90 dní.', 'Select a period of 1 to 90 days.') : errorMessage(error.message), 'error');
  } finally { busy = false; updateButtons(); }
}

el('ghConnect').addEventListener('click', () => run(async () => {
  const result = await getJsonOrThrow(await apiFetch('/google-health/auth-url', { method: 'POST' }));
  window.location.assign(result.authorization_url);
}));
el('ghRange').addEventListener('submit', (event) => { event.preventDefault(); run(async () => { await loadData(); notice(''); }); });
el('ghSync').addEventListener('click', () => run(async () => {
  notice(copy('Stahuji data…', 'Downloading data…'));
  const result = await getJsonOrThrow(await apiFetch(`/google-health/sync?${rangeQuery()}`, { method: 'POST' }));
  await loadConnection(); await loadData();
  const warnings = Object.entries(result.warnings).map(([key, reason]) => `${typeName(key)}: ${reason === 'MISSING_PERMISSIONS' ? copy('bez souhlasu', 'not permitted') : copy('nepodařilo se stáhnout', 'download failed')}`).join('; ');
  notice(warnings ? `${copy('Stažení dokončeno s omezením', 'Download completed with limitations')}: ${warnings}` : copy('Data jsou stažená a přehled je aktualizovaný.', 'Data downloaded and overview updated.'), warnings ? 'warning' : 'success');
}));
el('ghExport').addEventListener('click', () => run(async () => {
  const response = await apiFetch(`/google-health/export?${rangeQuery()}`);
  if (!response.ok) await getJsonOrThrow(response);
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = `google-health-${el('ghFrom').value}-${el('ghTo').value}.json`; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}));
el('ghDisconnect').addEventListener('click', () => {
  if (!window.confirm(copy('Odpojit Google Health a smazat všechna stažená data z Food Readeru?', 'Disconnect Google Health and delete all downloaded Google Health data from Food Reader?'))) return;
  run(async () => {
    const response = await apiFetch('/google-health/disconnect', { method: 'DELETE' });
    if (!response.ok) await getJsonOrThrow(response);
    payload = { daily: [], records: [] }; await loadConnection(); renderData(); notice(copy('Účet odpojen a data smazána.', 'Account disconnected and data deleted.'), 'success');
  });
});
el('ghType').addEventListener('change', () => { visibleRecords = 30; renderRecords(); });
el('ghMore').addEventListener('click', () => { visibleRecords += 30; renderRecords(); });
window.addEventListener('food-reader:localechange', renderCopy);
function localDay(value) { return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`; }
const today = new Date(); const start = new Date(today); start.setDate(start.getDate() - 6);
el('ghFrom').value = localDay(start); el('ghTo').value = localDay(today);
renderCopy();
const user = await setupPage();
if (user) await run(async () => {
  await loadConnection(); await loadData();
  const result = new URLSearchParams(window.location.search).get('google_health');
  if (result) {
    history.replaceState(null, '', window.location.pathname);
    el('ghLinkAccount').hidden = result !== 'ACCOUNT_NOT_LINKED';
    notice(result === 'connected' ? copy('Účet je propojený. Vyber období a stáhni data.', 'Account connected. Choose a period and download data.') : errorMessage(result), result === 'connected' ? 'success' : 'error');
  }
});
