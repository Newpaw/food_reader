import { API_BASE_URL, apiFetch, getJsonOrThrow, getLocale, setupPage, showStatus } from './common.js?v=20260403-11';

const strings = {
  cs: {
    brand: 'kouč hubnutí', navCoach: 'Kouč', navAdd: 'Přidat jídlo', navAddShort: 'Přidat', navHistory: 'Historie', navMetrics: 'Přehled', navProfile: 'Profil', logout: 'Odhlásit',
    heroEyebrow: 'Dnešní řízení', heroTitle: 'Co dnes udělat, aby váha šla dolů', heroBody: 'Nejde o co nejnižší příjem. Jde o úplný záznam, rozumný deficit, dost bílkovin a trend, který lze udržet.', logMeal: 'Zapsat jídlo',
    nextStep: 'Nejdůležitější další krok', today: 'Dnes', targets: 'Průběh proti cíli', checkinEyebrow: 'Jak se dnes cítíš', checkinTitle: 'Denní check-in', hunger: 'Hlad 1–5', energy: 'Energie 1–5', sleep: 'Spánek (h)', steps: 'Kroky', trained: 'Dnes jsem trénoval', checkinNote: 'Poznámka', saveCheckin: 'Uložit check-in',
    goalEyebrow: 'Směr', goalTitle: 'Cíl hubnutí', profileMissing: 'Nejdřív vyplň základní profil.', openProfile: 'Otevřít profil', targetWeight: 'Cílová váha (kg)', pace: 'Tempo (% váhy týdně)', saveGoal: 'Nastavit hubnutí',
    weekEyebrow: 'Posledních 7 dní', weekTitle: 'Co skutečně funguje', refresh: 'Obnovit', wins: 'Co se daří', focus: 'Priorita dalšího týdne', applyTarget: 'Použít nový cíl', chatTitle: 'Zeptej se na svůj dnešní plán', chatPlaceholder: 'Co si mám dát večer k vínu?', ask: 'Zeptat se', promptProtein: 'Kolik mi chybí bílkovin?', promptDinner: 'Co si dát k večeři?', promptStall: 'Proč váha stojí?',
    reminderEyebrow: 'Důslednost', reminderTitle: 'Chytré připomenutí', reminderBody: 'Aplikace upozorní nejvýše jednou denně, jen když chybí důležitý krok: záznam jídla, bílkoviny nebo dokončení deníku.', enableReminders: 'Povolit připomenutí', disclaimer: 'Obecné výživové doporučení, nikoli zdravotní péče.',
    calories: 'Kalorie', protein: 'Bílkoviny', fiber: 'Vláknina', meals: 'Jídla', completeness: 'Úplnost', weightTrend: 'Tempo váhy', training: 'Tréninky', weeksToGoal: 'Týdnů do cíle', saved: 'Uloženo.', loading: 'Načítám plán…', noData: 'Zatím bez dat', remindersOn: 'Připomenutí jsou povolená.', remindersOff: 'Připomenutí nejsou povolená.', permissionDenied: 'Oznámení byla v prohlížeči zamítnuta.', chatWelcome: 'Můžeš se ptát na dnešní jídlo, deficit, bílkoviny, víno nebo důvod stagnace.',
  },
  en: {
    brand: 'weight-loss coach', navCoach: 'Coach', navAdd: 'Add meal', navAddShort: 'Add', navHistory: 'History', navMetrics: 'Metrics', navProfile: 'Profile', logout: 'Log out',
    heroEyebrow: "Today's control", heroTitle: 'What to do today so weight keeps moving down', heroBody: 'The goal is not the lowest possible intake. It is a complete log, a reasonable deficit, enough protein and a sustainable trend.', logMeal: 'Log a meal',
    nextStep: 'Most important next step', today: 'Today', targets: 'Progress against target', checkinEyebrow: 'How you feel today', checkinTitle: 'Daily check-in', hunger: 'Hunger 1–5', energy: 'Energy 1–5', sleep: 'Sleep (h)', steps: 'Steps', trained: 'I trained today', checkinNote: 'Note', saveCheckin: 'Save check-in',
    goalEyebrow: 'Direction', goalTitle: 'Weight-loss goal', profileMissing: 'Complete the basic profile first.', openProfile: 'Open profile', targetWeight: 'Target weight (kg)', pace: 'Pace (% body weight/week)', saveGoal: 'Set weight loss',
    weekEyebrow: 'Last 7 days', weekTitle: 'What is actually working', refresh: 'Refresh', wins: 'What is working', focus: 'Next-week priority', applyTarget: 'Apply new target', chatTitle: "Ask about today's plan", chatPlaceholder: 'What should I eat with wine tonight?', ask: 'Ask', promptProtein: 'How much protein is missing?', promptDinner: 'What should I eat for dinner?', promptStall: 'Why has weight stalled?',
    reminderEyebrow: 'Consistency', reminderTitle: 'Smart reminder', reminderBody: 'The app sends at most one reminder a day, only when a critical step is missing: a meal log, protein or completing the diary.', enableReminders: 'Enable reminders', disclaimer: 'General nutrition guidance, not medical care.',
    calories: 'Calories', protein: 'Protein', fiber: 'Fiber', meals: 'Meals', completeness: 'Completeness', weightTrend: 'Weight pace', training: 'Training days', weeksToGoal: 'Weeks to goal', saved: 'Saved.', loading: 'Loading plan…', noData: 'No data yet', remindersOn: 'Reminders are enabled.', remindersOff: 'Reminders are not enabled.', permissionDenied: 'Notifications were denied in the browser.', chatWelcome: 'Ask about today’s meals, deficit, protein, wine or a stalled weight trend.',
  },
};

const state = { today: null, weekly: null, profile: null };
const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Prague';
const tr = (key) => strings[getLocale()]?.[key] || strings.en[key] || key;
const endpoint = (path) => `${API_BASE_URL}${path}`;

function translatePage() {
  document.title = getLocale() === 'cs' ? 'Food Reader | Kouč hubnutí' : 'Food Reader | Weight-loss coach';
  document.querySelectorAll('[data-coach-key]').forEach((node) => { node.textContent = tr(node.dataset.coachKey); });
  document.querySelectorAll('[data-coach-placeholder]').forEach((node) => { node.placeholder = tr(node.dataset.coachPlaceholder); });
}

function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
function textNode(tag, value, className) { const node = document.createElement(tag); node.textContent = value; if (className) node.className = className; return node; }
function listItems(target, items) { clear(target); (items?.length ? items : [tr('noData')]).forEach((item) => target.appendChild(textNode('li', item))); }
function number(value, suffix = '') { return value === null || value === undefined ? '—' : `${Math.round(value * 10) / 10}${suffix}`; }

function metricCard(label, metric, unit) {
  const card = textNode('div', '', 'coach-metric');
  card.append(textNode('span', label), textNode('strong', `${number(metric?.current)}${unit}`));
  const target = metric?.target;
  card.append(textNode('small', target ? `${number(metric.remaining)}${unit} / ${number(target)}${unit}` : tr('noData')));
  const track = textNode('div', '', 'metric-track');
  const fill = document.createElement('i');
  fill.style.setProperty('--progress', `${Math.max(0, Math.min(metric?.percentage || 0, 100))}%`);
  track.appendChild(fill); card.appendChild(track); return card;
}

function simpleMetric(label, value) {
  const card = textNode('div', '', 'coach-metric'); card.append(textNode('span', label), textNode('strong', value)); return card;
}

function renderToday() {
  const data = state.today; if (!data) return;
  document.getElementById('actionTitle').textContent = data.next_action.title;
  document.getElementById('actionBody').textContent = data.next_action.body;
  document.getElementById('scoreBadge').textContent = `${data.adherence_score}%`;
  const foods = document.getElementById('suggestedFoods'); clear(foods);
  data.next_action.suggested_foods.forEach((food) => foods.appendChild(textNode('span', food)));
  const warnings = document.getElementById('warnings'); clear(warnings);
  data.warnings.forEach((warning) => warnings.appendChild(textNode('div', warning, 'coach-warning')));
  const metrics = document.getElementById('todayMetrics'); clear(metrics);
  metrics.append(metricCard(tr('calories'), data.calories, ' kcal'), metricCard(tr('protein'), data.protein, ' g'), metricCard(tr('fiber'), data.fiber, ' g'));
  const form = document.getElementById('checkinForm');
  if (data.checkin) {
    form.hunger.value = data.checkin.hunger ?? ''; form.energy.value = data.checkin.energy ?? ''; form.sleepHours.value = data.checkin.sleep_hours ?? ''; form.steps.value = data.checkin.steps ?? ''; form.trained.checked = data.checkin.trained; form.note.value = data.checkin.note ?? '';
  }
}

function renderWeekly() {
  const data = state.weekly; if (!data) return;
  const metrics = document.getElementById('weeklyMetrics'); clear(metrics);
  metrics.append(
    simpleMetric(tr('completeness'), `${data.logging_completeness_percent}%`),
    simpleMetric(tr('calories'), `${data.average_calories_logged_days} kcal`),
    simpleMetric(tr('protein'), `${data.average_protein_g} g`),
    simpleMetric(tr('weightTrend'), data.weight_trend.weekly_change_percent === null ? '—' : `${data.weight_trend.weekly_change_percent}% / týden`),
    simpleMetric(data.estimated_weeks_to_goal ? tr('weeksToGoal') : tr('training'), data.estimated_weeks_to_goal ?? data.training_days),
  );
  listItems(document.getElementById('winsList'), data.wins); listItems(document.getElementById('focusList'), data.focus_next_week);
  const adaptive = document.getElementById('adaptiveTarget');
  const rec = data.adaptive_target;
  adaptive.hidden = !rec.eligible;
  if (rec.eligible) {
    document.getElementById('adaptiveTitle').textContent = `${rec.current_target ?? '—'} → ${rec.recommended_target ?? '—'} kcal`;
    document.getElementById('adaptiveReason').textContent = rec.reason;
    document.getElementById('applyTargetButton').hidden = !rec.adjustment;
  }
}

function renderProfile() {
  const missing = !state.profile;
  document.getElementById('profileMissing').hidden = !missing;
  document.getElementById('goalFields').hidden = missing;
  document.getElementById('saveGoalButton').hidden = missing;
  if (!missing) {
    const form = document.getElementById('goalForm'); form.targetWeight.value = state.profile.target_weight_kg ?? ''; form.pace.value = state.profile.desired_weekly_loss_percent ?? 0.6;
  }
}

async function fetchOptionalProfile() {
  const response = await apiFetch(endpoint('/profile'));
  if (response.status === 404) return null;
  return getJsonOrThrow(response, 'Unable to load profile');
}

async function loadCoach() {
  const status = document.getElementById('coachStatus'); showStatus(status, tr('loading'), 'info');
  try {
    const params = new URLSearchParams({ timezone });
    const [todayResponse, weeklyResponse, profile] = await Promise.all([
      apiFetch(endpoint(`/coach/today?${params}`)), apiFetch(endpoint(`/coach/weekly?${params}`)), fetchOptionalProfile(),
    ]);
    state.today = await getJsonOrThrow(todayResponse, 'Unable to load today'); state.weekly = await getJsonOrThrow(weeklyResponse, 'Unable to load week'); state.profile = profile;
    renderToday(); renderWeekly(); renderProfile(); showStatus(status, '', 'info'); maybeNotify();
  } catch (error) { showStatus(status, error.message, 'danger'); }
}

async function saveCheckin(event) {
  event.preventDefault(); const form = event.currentTarget;
  const payload = { hunger: form.hunger.value ? Number(form.hunger.value) : null, energy: form.energy.value ? Number(form.energy.value) : null, sleep_hours: form.sleepHours.value ? Number(form.sleepHours.value) : null, steps: form.steps.value ? Number(form.steps.value) : null, trained: form.trained.checked, note: form.note.value.trim() || null, timezone };
  const response = await apiFetch(endpoint('/coach/checkin'), { method: 'PUT', body: payload }); await getJsonOrThrow(response, 'Unable to save check-in'); await loadCoach(); showStatus(document.getElementById('coachStatus'), tr('saved'), 'success');
}

async function saveGoal(event) {
  event.preventDefault(); const form = event.currentTarget;
  const response = await apiFetch(endpoint('/profile'), { method: 'PUT', body: { goal: 'weight_loss', target_weight_kg: form.targetWeight.value ? Number(form.targetWeight.value) : null, desired_weekly_loss_percent: Number(form.pace.value || 0.6) } });
  await getJsonOrThrow(response, 'Unable to save goal'); await loadCoach(); showStatus(document.getElementById('coachStatus'), tr('saved'), 'success');
}

function addChat(role, message) { const target = document.getElementById('chatMessages'); target.appendChild(textNode('div', message, `chat-message ${role}`)); target.scrollTop = target.scrollHeight; }
async function askQuestion(question) {
  if (!question.trim()) return; addChat('user', question.trim());
  const response = await apiFetch(endpoint('/coach/chat'), { method: 'POST', body: { question: question.trim(), timezone } });
  const data = await getJsonOrThrow(response, 'Unable to ask coach'); addChat('assistant', [data.answer, ...(data.actions || []).map((item) => `• ${item}`)].join('\n'));
}

async function applyTarget() {
  const response = await apiFetch(endpoint(`/coach/adaptive-target/apply?timezone=${encodeURIComponent(timezone)}`), { method: 'POST' });
  await getJsonOrThrow(response, 'Unable to apply target'); await loadCoach(); showStatus(document.getElementById('coachStatus'), tr('saved'), 'success');
}

function reminderEnabled() { return localStorage.getItem('food-reader:coach-reminders') === 'on'; }
function renderReminderState() { document.getElementById('reminderState').textContent = reminderEnabled() ? tr('remindersOn') : tr('remindersOff'); }
async function enableReminders() {
  if (!('Notification' in window)) { document.getElementById('reminderState').textContent = tr('permissionDenied'); return; }
  const permission = await Notification.requestPermission();
  if (permission === 'granted') localStorage.setItem('food-reader:coach-reminders', 'on');
  renderReminderState(); maybeNotify();
}
async function maybeNotify() {
  if (!state.today || !reminderEnabled() || Notification.permission !== 'granted' || state.today.next_action.priority === 'low') return;
  const key = `food-reader:coach-notified:${state.today.date}`; if (localStorage.getItem(key)) return;
  const registration = await navigator.serviceWorker?.ready;
  if (registration) await registration.showNotification(state.today.next_action.title, { body: state.today.next_action.body, icon: '/assets/favicon/icon-192.png', tag: 'food-reader-daily-coach', data: { url: '/coach.html' } });
  localStorage.setItem(key, '1');
}

const promptText = (kind) => ({
  cs: { protein: 'Kolik bílkovin mi dnes ještě chybí a čím je nejlépe doplnit?', dinner: 'Co si mám dát dnes k večeři podle zbývajících kalorií?', stall: 'Podle mých dat: proč může váha stát a co mám změnit jako první?' },
  en: { protein: 'How much protein is still missing today and what is the best way to add it?', dinner: 'What should I eat for dinner based on my remaining calories?', stall: 'Based on my data, why may weight be stalled and what should I change first?' },
}[getLocale()]?.[kind]);

document.addEventListener('DOMContentLoaded', async () => {
  await setupPage(); translatePage(); renderReminderState(); addChat('assistant', tr('chatWelcome'));
  document.getElementById('checkinForm').addEventListener('submit', (event) => void saveCheckin(event));
  document.getElementById('goalForm').addEventListener('submit', (event) => void saveGoal(event));
  document.getElementById('refreshCoach').addEventListener('click', () => void loadCoach());
  document.getElementById('applyTargetButton').addEventListener('click', () => void applyTarget());
  document.getElementById('enableReminders').addEventListener('click', () => void enableReminders());
  document.getElementById('chatForm').addEventListener('submit', (event) => { event.preventDefault(); const input = event.currentTarget.question; const question = input.value; input.value = ''; void askQuestion(question); });
  document.querySelectorAll('[data-prompt]').forEach((button) => button.addEventListener('click', () => void askQuestion(promptText(button.dataset.prompt))));
  window.addEventListener('food-reader:localechange', () => { translatePage(); renderReminderState(); renderToday(); renderWeekly(); renderProfile(); });
  await loadCoach();
});
