import {
  API,
  apiFetch,
  formatDateTime,
  getBrowserTimeZone,
  getJsonOrThrow,
  normalizeOptionalNumber,
  setupPage,
  showStatus,
  t,
} from './common.js?v=20260809-adaptive-1';


let profileExists = false;
let cachedProfile = null;
let cachedWithingsStatus = null;


export function buildProfilePayload(form) {
  return {
    height_cm: normalizeOptionalNumber(form.height.value),
    weight_kg: normalizeOptionalNumber(form.weight.value),
    age: normalizeOptionalNumber(form.age.value),
    gender: form.gender.value || null,
    activity_level: form.activityLevel.value || null,
    goal: form.goal.value || null,
    dietary_preference: form.dietaryPreference.value || null,
    custom_calories: normalizeOptionalNumber(form.customCalories.value),
    custom_protein_g: normalizeOptionalNumber(form.customProtein.value),
    custom_carbs_g: normalizeOptionalNumber(form.customCarbs.value),
    custom_fats_g: normalizeOptionalNumber(form.customFats.value),
    custom_fiber_g: normalizeOptionalNumber(form.customFiber.value),
    adaptive_calories_enabled: Boolean(form.adaptiveCaloriesEnabled?.checked),
  };
}

export function hasCustomOverrides(profile) {
  return [
    profile?.custom_calories,
    profile?.custom_protein_g,
    profile?.custom_carbs_g,
    profile?.custom_fats_g,
    profile?.custom_fiber_g,
  ].some((value) => value !== null && value !== undefined && value !== '');
}


function fillForm(profile) {
  const form = document.getElementById('profileForm');
  const overrides = document.getElementById('profileOverrides');
  const weightSource = document.getElementById('profileWeightSource');
  form.height.value = profile?.height_cm ?? '';
  form.weight.value = profile?.weight_kg ?? '';
  form.age.value = profile?.age ?? '';
  form.gender.value = profile?.gender ?? '';
  form.activityLevel.value = profile?.activity_level ?? 'sedentary';
  form.goal.value = profile?.goal ?? 'maintenance';
  form.dietaryPreference.value = profile?.dietary_preference ?? 'none';
  form.customCalories.value = profile?.custom_calories ?? '';
  form.customProtein.value = profile?.custom_protein_g ?? '';
  form.customCarbs.value = profile?.custom_carbs_g ?? '';
  form.customFats.value = profile?.custom_fats_g ?? '';
  form.customFiber.value = profile?.custom_fiber_g ?? '';
  form.adaptiveCaloriesEnabled.checked = Boolean(profile?.adaptive_calories_enabled);
  if (overrides) {
    overrides.open = hasCustomOverrides(profile);
  }
  if (weightSource) {
    if (profile?.weight_source === 'withings' && profile?.weight_measured_at) {
      weightSource.textContent = t('profile.weightSourceWithings', { date: formatDateTime(profile.weight_measured_at) });
    } else if (profile?.weight_kg !== null && profile?.weight_kg !== undefined) {
      weightSource.textContent = t('profile.weightSourceManual');
    } else {
      weightSource.textContent = t('profile.weightSourceEmpty');
    }
  }
}


function adaptiveStatusCopy(adaptive) {
  const status = adaptive?.status || 'disabled';
  const titles = {
    disabled: 'profile.adaptiveStatusDisabled',
    not_connected: 'profile.adaptiveStatusNotConnected',
    warming_up: 'profile.adaptiveStatusWarmingUp',
    stale: 'profile.adaptiveStatusStale',
    custom_override: 'profile.adaptiveStatusCustom',
    active: 'profile.adaptiveStatusActive',
  };
  const details = {
    disabled: 'profile.adaptiveDetailDisabled',
    not_connected: 'profile.adaptiveDetailNotConnected',
    warming_up: 'profile.adaptiveDetailWarmingUp',
    stale: 'profile.adaptiveDetailStale',
    custom_override: 'profile.adaptiveDetailCustom',
    active: 'profile.adaptiveDetailActive',
  };
  return {
    status,
    title: t(titles[status] || titles.disabled),
    detail: t(details[status] || details.disabled, { days: adaptive?.data_days ?? 0 }),
  };
}


export function buildAdaptiveTargetMarkup(targets) {
  const adaptive = targets?.adaptive || { status: 'disabled', enabled: false, applied: false };
  const copy = adaptiveStatusCopy(adaptive);
  const signedAdjustment = adaptive.adjustment_kcal > 0
    ? `+${adaptive.adjustment_kcal}`
    : `${adaptive.adjustment_kcal || 0}`;
  const activeBreakdown = adaptive.applied
    ? `
      <div class="adaptive-breakdown">
        <div><span>${t('profile.adaptiveBase')}</span><strong>${targets.base_calories} kcal</strong></div>
        <div><span>${t('profile.adaptiveBurn')}</span><strong>${adaptive.burn_baseline} kcal</strong></div>
        <div><span>${t('profile.adaptiveAdjustment')}</span><strong>${signedAdjustment} kcal</strong></div>
        <div><span>${t('profile.adaptiveRange')}</span><strong>${adaptive.recommended_min_calories}–${adaptive.recommended_max_calories} kcal</strong></div>
      </div>
    `
    : '';

  return `
    <section class="adaptive-target-card" data-status="${copy.status}">
      <div class="adaptive-target-heading">
        <span class="adaptive-status-dot" aria-hidden="true"></span>
        <div>
          <strong>${copy.title}</strong>
          <p>${copy.detail}</p>
        </div>
      </div>
      ${activeBreakdown}
    </section>
  `;
}


function localizedCalculationMethod(targets) {
  const methods = {
    profile: 'profile.methodProfile',
    custom: 'profile.methodCustom',
    adaptive: 'profile.methodAdaptive',
  };
  const key = methods[targets?.calculation_method_code];
  return key ? t(key) : targets.calculation_method;
}


function renderTargets(targets) {
  const target = document.getElementById('profileTargets');
  if (!targets) {
    target.innerHTML = `<p class="empty-state compact">${t('profile.targetsEmpty')}</p>`;
    return;
  }

  target.innerHTML = `
    <div class="stat-grid">
      <article class="stat-card"><span>${t('profile.calories')}</span><strong>${targets.calories}</strong></article>
      <article class="stat-card"><span>${t('profile.protein')}</span><strong>${targets.protein_g}g</strong></article>
      <article class="stat-card"><span>${t('profile.carbs')}</span><strong>${targets.carbs_g}g</strong></article>
      <article class="stat-card"><span>${t('profile.fat')}</span><strong>${targets.fats_g}g</strong></article>
      <article class="stat-card"><span>${t('profile.fiber')}</span><strong>${targets.fiber_g}g</strong></article>
    </div>
    <div class="detail-list">
      <div><strong>${t('profile.bmr')}</strong><span>${targets.bmr ? Math.round(targets.bmr) : '-'}</span></div>
      <div><strong>${t('profile.tdee')}</strong><span>${targets.tdee ? Math.round(targets.tdee) : '-'}</span></div>
      <div><strong>${t('profile.method')}</strong><span>${localizedCalculationMethod(targets)}</span></div>
    </div>
    ${buildAdaptiveTargetMarkup(targets)}
  `;
}


async function loadTargets() {
  const timezone = encodeURIComponent(getBrowserTimeZone());
  const response = await apiFetch(`${API.profile}/targets?timezone=${timezone}`);
  if (!response.ok) {
    renderTargets(null);
    return;
  }

  renderTargets(await response.json());
}


async function loadProfile() {
  const response = await apiFetch(API.profile);
  if (!response.ok) {
    profileExists = false;
    cachedProfile = null;
    fillForm(null);
    renderTargets(null);
    return;
  }

  cachedProfile = await response.json();
  profileExists = true;
  fillForm(cachedProfile);
  await loadTargets();
}


export function buildWithingsStatusMarkup(status) {
  if (!status?.configured) {
    return `<div class="empty-state compact">${t('profile.withingsNotConfigured')}</div>`;
  }

  if (!status.connected) {
    return `
      <div class="empty-state compact">
        <p>${t('profile.withingsDisconnected')}</p>
        <button id="connectWithingsButton" type="button" class="btn btn-secondary">${t('button.connectWithings')}</button>
      </div>
    `;
  }

  const latestWeight = status.latest_weight_kg
    ? t('profile.withingsLatestWeight', { weight: Number(status.latest_weight_kg).toFixed(1) })
    : t('profile.withingsNoWeight');
  const lastSync = status.last_sync_at
    ? t('profile.withingsLastSync', { date: formatDateTime(status.last_sync_at) })
    : t('profile.withingsNeverSynced');

  return `
    <div class="detail-list">
      <div><strong>${t('profile.withingsConnected')}</strong><span>${lastSync}</span></div>
      <div><strong>${latestWeight}</strong><span>${status.scope || 'user.metrics'}</span></div>
    </div>
    <div class="button-row">
      <button id="syncWithingsButton" type="button" class="btn btn-primary">${t('button.syncWithings')}</button>
      <button id="disconnectWithingsButton" type="button" class="btn btn-secondary">${t('button.disconnectWithings')}</button>
    </div>
  `;
}


function bindWithingsActions() {
  document.getElementById('connectWithingsButton')?.addEventListener('click', connectWithings);
  document.getElementById('syncWithingsButton')?.addEventListener('click', syncWithings);
  document.getElementById('disconnectWithingsButton')?.addEventListener('click', disconnectWithings);
}


function renderWithingsStatus(status) {
  const panel = document.getElementById('withingsPanel');
  if (!panel) {
    return;
  }
  panel.innerHTML = buildWithingsStatusMarkup(status);
  bindWithingsActions();
}


async function loadWithingsStatus() {
  const response = await apiFetch(`${API.withings}/status`);
  if (!response.ok) {
    cachedWithingsStatus = { configured: false, connected: false };
    renderWithingsStatus(cachedWithingsStatus);
    return;
  }
  cachedWithingsStatus = await response.json();
  renderWithingsStatus(cachedWithingsStatus);
}


async function connectWithings() {
  const status = document.getElementById('withingsStatus');
  showStatus(status, t('profile.withingsConnecting'), 'info');
  try {
    const response = await apiFetch(`${API.withings}/auth-url`, { method: 'POST' });
    const payload = await getJsonOrThrow(response, 'Unable to start Withings authorization');
    window.location.href = payload.authorization_url;
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}


async function syncWithings() {
  const status = document.getElementById('withingsStatus');
  showStatus(status, t('profile.withingsSyncing'), 'info');
  try {
    const response = await apiFetch(`${API.withings}/sync`, { method: 'POST' });
    await getJsonOrThrow(response, 'Unable to sync Withings measurements');
    await loadProfile();
    await loadWithingsStatus();
    showStatus(status, t('profile.withingsSynced'), 'success');
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}


async function disconnectWithings() {
  if (!window.confirm(t('profile.withingsDisconnectConfirm'))) {
    return;
  }

  const status = document.getElementById('withingsStatus');
  try {
    const response = await apiFetch(`${API.withings}/disconnect`, { method: 'DELETE' });
    if (!response.ok) {
      await getJsonOrThrow(response, 'Unable to disconnect Withings');
    }
    await loadWithingsStatus();
    showStatus(status, t('profile.withingsDisconnectedMessage'), 'success');
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}


function showWithingsCallbackResult() {
  const params = new URLSearchParams(window.location.search);
  const result = params.get('withings');
  if (!result) {
    return;
  }

  const status = document.getElementById('withingsStatus');
  if (result === 'connected') {
    showStatus(status, t('profile.withingsConnectedMessage'), 'success');
  } else if (result === 'error') {
    showStatus(status, t('profile.withingsConnectionFailed'), 'danger');
  }

  params.delete('withings');
  params.delete('reason');
  const nextSearch = params.toString();
  const nextUrl = `${window.location.pathname}${nextSearch ? `?${nextSearch}` : ''}${window.location.hash}`;
  window.history.replaceState({}, '', nextUrl);
}


async function saveProfile(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const status = document.getElementById('profileStatus');
  showStatus(status, t('profile.saving'), 'info');

  try {
    const response = await apiFetch(API.profile, {
      method: profileExists ? 'PUT' : 'POST',
      body: buildProfilePayload(form),
    });
    cachedProfile = await getJsonOrThrow(response, 'Unable to save profile');
    profileExists = true;
    fillForm(cachedProfile);
    await loadTargets();
    showStatus(status, t('profile.saved'), 'success');
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}


document.addEventListener('DOMContentLoaded', async () => {
  await setupPage();

  document.getElementById('profileForm').addEventListener('submit', saveProfile);
  document.getElementById('resetProfileButton').addEventListener('click', () => fillForm(cachedProfile));
  showWithingsCallbackResult();

  await loadProfile();
  await loadWithingsStatus();

  window.addEventListener('food-reader:localechange', () => {
    loadTargets();
    renderWithingsStatus(cachedWithingsStatus);
    fillForm(cachedProfile);
  });
});
