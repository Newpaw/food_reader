import {
  API,
  apiFetch,
  getJsonOrThrow,
  normalizeOptionalNumber,
  setupPage,
  showStatus,
  t,
} from './common.js?v=20260403-11';


let profileExists = false;
let cachedProfile = null;


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
  if (overrides) {
    overrides.open = hasCustomOverrides(profile);
  }
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
      <div><strong>${t('profile.method')}</strong><span>${targets.calculation_method}</span></div>
    </div>
  `;
}


async function loadTargets() {
  const response = await apiFetch(`${API.profile}/targets`);
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

  await loadProfile();

  window.addEventListener('food-reader:localechange', loadTargets);
});
