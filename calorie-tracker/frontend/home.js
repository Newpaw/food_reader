import {
  API,
  apiFetch,
  deleteMealTemplate,
  formatDateTime,
  formatTime,
  getLocalDateKey,
  getMealDisplayName,
  getMealTemplates,
  getPendingMealQueue,
  getJsonOrThrow,
  queuePendingMeal,
  removePendingMeal,
  resolveAssetUrl,
  saveMealTemplate,
  setupPage,
  showStatus,
  showToast,
  t,
  toDateTimeInputValue,
} from './common.js?v=20260402-2';


let currentMeal = null;
let originalMeal = null;
let recentMeals = [];
let dashboardMeals = [];
let dashboardTargets = null;
let voiceRecognition = null;
let isListening = false;
let syncInProgress = false;
let currentPreviewUrl = null;
let photoSubmissionInProgress = false;

const MAX_UPLOAD_DIMENSION = 1600;
const MAX_UPLOAD_BYTES = 1_800_000;
const UPLOAD_QUALITY = 0.82;


export function buildMealUpdatePayload(draft) {
  return {
    calories: Number(draft.calories || 0),
    protein: Number(draft.protein || 0),
    fat: Number(draft.fat || 0),
    carbs: Number(draft.carbs || 0),
    fiber: Number(draft.fiber || 0),
    sugar: Number(draft.sugar || 0),
    sodium: Number(draft.sodium || 0),
    meal_type: draft.mealType,
    consumed_at: new Date(draft.consumedAt).toISOString(),
    notes: draft.notes.trim() || null,
  };
}


export function summarizeTodayState(meals, targets = null, queueCount = 0, templateCount = 0) {
  const todayKey = getLocalDateKey(new Date().toISOString());
  const todayMeals = meals.filter((meal) => getLocalDateKey(meal.consumed_at) === todayKey);
  const totals = todayMeals.reduce(
    (summary, meal) => ({
      calories: summary.calories + (meal.calories ?? 0),
      protein: summary.protein + (meal.protein ?? 0),
      fiber: summary.fiber + (meal.fiber ?? 0),
      meals: summary.meals + 1,
    }),
    { calories: 0, protein: 0, fiber: 0, meals: 0 },
  );

  const loggedDays = new Set(meals.map((meal) => getLocalDateKey(meal.consumed_at)));
  let streak = 0;
  const cursor = new Date();
  while (loggedDays.has(getLocalDateKey(cursor.toISOString()))) {
    streak += 1;
    cursor.setDate(cursor.getDate() - 1);
  }

  const targetCalories = targets?.calories ?? null;
  const remainingCalories = targetCalories === null ? null : targetCalories - totals.calories;

  return {
    ...totals,
    streak,
    targetCalories,
    remainingCalories,
    queueCount,
    templateCount,
  };
}


export function shouldPreferMobileCamera(environment = globalThis) {
  const matchMedia = environment?.matchMedia?.bind(environment);
  const narrow = Boolean(matchMedia?.('(max-width: 820px)')?.matches);
  const coarse = Boolean(matchMedia?.('(pointer: coarse)')?.matches);
  const navigatorLike = environment?.navigator ?? {};
  const touchPoints = Number(navigatorLike.maxTouchPoints || 0);
  const userAgent = String(navigatorLike.userAgent || '');
  const mobileUserAgent = /Android|webOS|iPhone|iPad|iPod|Mobile/i.test(userAgent);
  return narrow && (coarse || touchPoints > 0 || mobileUserAgent);
}


export function planPhotoOptimization(fileLike, options = {}) {
  const maxDimension = options.maxDimension ?? MAX_UPLOAD_DIMENSION;
  const maxBytes = options.maxBytes ?? MAX_UPLOAD_BYTES;
  const quality = options.quality ?? UPLOAD_QUALITY;
  const width = Number(fileLike?.width || 0);
  const height = Number(fileLike?.height || 0);
  const largestSide = Math.max(width, height);
  const scale = largestSide > maxDimension ? maxDimension / largestSide : 1;

  return {
    maxDimension,
    maxBytes,
    quality,
    targetWidth: width ? Math.max(1, Math.round(width * scale)) : 0,
    targetHeight: height ? Math.max(1, Math.round(height * scale)) : 0,
    shouldResize: largestSide > maxDimension,
    shouldOptimize:
      (fileLike?.type || '').startsWith('image/') &&
      fileLike?.type !== 'image/svg+xml' &&
      (Number(fileLike?.size || 0) > maxBytes || largestSide > maxDimension),
  };
}


function getAnalysisFields() {
  return {
    calories: document.getElementById('analysisCalories'),
    protein: document.getElementById('analysisProtein'),
    fat: document.getElementById('analysisFat'),
    carbs: document.getElementById('analysisCarbs'),
    fiber: document.getElementById('analysisFiber'),
    sugar: document.getElementById('analysisSugar'),
    sodium: document.getElementById('analysisSodium'),
    mealType: document.getElementById('analysisMealType'),
    consumedAt: document.getElementById('analysisConsumedAt'),
    notes: document.getElementById('analysisNotes'),
  };
}


function getCaptureStatus() {
  return document.getElementById('captureStatus');
}


function getPhotoInputs() {
  return {
    cameraInput: document.getElementById('mealCameraInput'),
    libraryInput: document.getElementById('mealImage'),
  };
}


function getSelectedPhotoFile() {
  const { cameraInput, libraryInput } = getPhotoInputs();
  return cameraInput?.files?.[0] || libraryInput?.files?.[0] || null;
}


function clearPhotoPreview() {
  const preview = document.getElementById('selectedImagePreview');
  const emptyState = document.getElementById('selectedImageEmpty');
  if (currentPreviewUrl) {
    URL.revokeObjectURL(currentPreviewUrl);
    currentPreviewUrl = null;
  }
  preview.removeAttribute('src');
  preview.hidden = true;
  emptyState.hidden = false;
}


function clearPhotoSelection() {
  const { cameraInput, libraryInput } = getPhotoInputs();
  if (cameraInput) {
    cameraInput.value = '';
  }
  if (libraryInput) {
    libraryInput.value = '';
  }
  clearPhotoPreview();
}


function getPhotoCaptureForm() {
  return document.getElementById('photoMealForm');
}


function isOfflineLike(error) {
  return !navigator.onLine || error instanceof TypeError || /fetch|network/i.test(String(error?.message || ''));
}


function buildTextMealRequest({
  description,
  calories,
  protein,
  fat,
  carbs,
  fiber,
  sugar,
  sodium,
  mealType,
  notes,
  consumedAt,
}) {
  return {
    food_description: description,
    calories,
    protein,
    fat,
    carbs,
    fiber,
    sugar,
    sodium,
    meal_type: mealType,
    consumed_at: consumedAt || new Date().toISOString(),
    notes: notes || null,
  };
}


function buildTemplateFromMeal(meal, extra = {}) {
  const title = getMealDisplayName(meal);
  return {
    title,
    description: title,
    calories: meal.calories ?? 0,
    protein: meal.protein ?? 0,
    fat: meal.fat ?? 0,
    carbs: meal.carbs ?? 0,
    fiber: meal.fiber ?? 0,
    sugar: meal.sugar ?? 0,
    sodium: meal.sodium ?? 0,
    meal_type: meal.meal_type,
    notes: meal.notes ?? null,
    source: extra.source || 'meal',
  };
}


function renderMealEditor(meal) {
  currentMeal = meal;
  originalMeal = { ...meal };
  const imageUrl = resolveAssetUrl(meal.image_url);
  const mealName = getMealDisplayName(meal);

  const panel = document.getElementById('analysisPanel');
  const fields = getAnalysisFields();
  panel.hidden = false;

  fields.calories.value = meal.calories ?? 0;
  fields.protein.value = meal.protein ?? 0;
  fields.fat.value = meal.fat ?? 0;
  fields.carbs.value = meal.carbs ?? 0;
  fields.fiber.value = meal.fiber ?? 0;
  fields.sugar.value = meal.sugar ?? 0;
  fields.sodium.value = meal.sodium ?? 0;
  fields.mealType.value = meal.meal_type;
  fields.consumedAt.value = toDateTimeInputValue(meal.consumed_at);
  fields.notes.value = meal.notes ?? '';

  const preview = document.getElementById('analysisPreview');
  preview.innerHTML = `
    <img src="${imageUrl}" alt="${mealName}" class="analysis-preview-image">
    <div>
      <p class="eyebrow">${t('home.latestEntry')}</p>
      <h3>${mealName}</h3>
      <p>${formatDateTime(meal.consumed_at)}</p>
    </div>
  `;

  document.getElementById('reanalysisBlock').hidden = meal.image_url === '/assets/images/text-meal-placeholder.svg';
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}


function renderRecentMeals(meals) {
  const target = document.getElementById('recentMeals');
  if (!meals.length) {
    target.innerHTML = `<p class="empty-state">${t('home.noMeals')}</p>`;
    return;
  }

  target.innerHTML = meals
    .map(
      (meal) => `
        <article class="meal-card compact">
          <img src="${resolveAssetUrl(meal.image_url)}" alt="${getMealDisplayName(meal)}" class="meal-card-image">
          <div class="meal-card-body">
            <div class="meal-card-heading">
              <h3>${getMealDisplayName(meal)}</h3>
              <span>${formatTime(meal.consumed_at)}</span>
            </div>
            <p>${meal.calories} kcal</p>
            <button class="btn btn-secondary btn-small" data-meal-open="${meal.id}">${t('button.review')}</button>
          </div>
        </article>
      `,
    )
    .join('');

  target.querySelectorAll('[data-meal-open]').forEach((button) => {
    button.addEventListener('click', () => {
      const meal = meals.find((item) => item.id === Number(button.dataset.mealOpen));
      if (meal) {
        renderMealEditor(meal);
      }
    });
  });
}


function renderTodayDashboard() {
  const target = document.getElementById('todayDashboard');
  const summary = summarizeTodayState(
    dashboardMeals,
    dashboardTargets,
    getPendingMealQueue().length,
    getMealTemplates().length,
  );
  const syncButton = document.getElementById('syncQueueButton');
  syncButton.hidden = summary.queueCount === 0;

  const remainingBlock =
    summary.remainingCalories === null
      ? `<p class="panel-note">${t('home.dashboardTargetsMissing')}</p>`
      : `<p class="panel-note">${
          summary.remainingCalories >= 0
            ? t('home.dashboardRemaining', { remaining: summary.remainingCalories })
            : t('home.dashboardOver', { remaining: Math.abs(summary.remainingCalories) })
        }</p>`;

  const queueBlock =
    summary.queueCount === 0
      ? `<p class="panel-note">${t('home.queueReady')}</p>`
      : `<div class="queue-list">${getPendingMealQueue()
          .slice(0, 3)
          .map(
            (entry) =>
              `<div class="daily-row"><span>${entry.label || t(`home.queueKind.${entry.kind}`)}</span><span>${t(`home.queueKind.${entry.kind}`)}</span></div>`,
          )
          .join('')}</div>`;

  target.innerHTML = `
    <div class="stat-grid">
      <article class="stat-card"><span>${t('home.dashboardCalories')}</span><strong>${summary.calories}</strong></article>
      <article class="stat-card"><span>${t('home.dashboardProtein')}</span><strong>${summary.protein}g</strong></article>
      <article class="stat-card"><span>${t('home.dashboardFiber')}</span><strong>${summary.fiber}g</strong></article>
      <article class="stat-card"><span>${t('home.dashboardTarget')}</span><strong>${summary.targetCalories ?? '-'}</strong></article>
    </div>
    ${remainingBlock}
    <div class="detail-list">
      <div><strong>${t('home.dashboardStreak', { days: summary.streak || 0 })}</strong><span>${summary.meals}</span></div>
      <div><strong>${t('home.dashboardTemplates', { count: summary.templateCount })}</strong><span>${summary.templateCount}</span></div>
      <div><strong>${t('home.dashboardQueue', { count: summary.queueCount })}</strong><span>${summary.queueCount}</span></div>
    </div>
    <p class="panel-note">${t('home.dashboardInsights', { meals: summary.meals, calories: summary.calories })}</p>
    <div class="subtle-panel">
      <p class="eyebrow">${t('home.queueHeading')}</p>
      ${queueBlock}
    </div>
  `;
}


function renderTemplates() {
  const target = document.getElementById('templateList');
  const templates = getMealTemplates();

  if (!templates.length) {
    target.innerHTML = `<p class="empty-state">${t('home.templatesEmpty')}</p>`;
    return;
  }

  target.innerHTML = templates
    .map(
      (template) => `
        <article class="template-card">
          <div class="template-card-main">
            <strong>${template.title}</strong>
            <span>${template.calories} kcal</span>
          </div>
          <div class="template-card-actions">
            <button type="button" class="btn btn-secondary btn-small" data-template-log="${template.id}">${t('button.logAgain')}</button>
            <button type="button" class="btn btn-ghost btn-small" data-template-delete="${template.id}">${t('button.remove')}</button>
          </div>
        </article>
      `,
    )
    .join('');

  target.querySelectorAll('[data-template-log]').forEach((button) => {
    button.addEventListener('click', async () => {
      const template = templates.find((item) => item.id === button.dataset.templateLog);
      if (template) {
        await submitTemplateMeal(template);
      }
    });
  });

  target.querySelectorAll('[data-template-delete]').forEach((button) => {
    button.addEventListener('click', () => {
      deleteMealTemplate(button.dataset.templateDelete);
      renderTemplates();
      renderTodayDashboard();
    });
  });
}


function refreshHomePanels() {
  renderTodayDashboard();
  renderTemplates();
  renderRecentMeals(recentMeals);
}


async function loadHomeData() {
  const [recentResponse, mealsResponse, targetsResponse] = await Promise.all([
    apiFetch(`${API.meals}?limit=5`),
    apiFetch(`${API.meals}?limit=120`),
    apiFetch(`${API.profile}/targets`),
  ]);

  recentMeals = await getJsonOrThrow(recentResponse, 'Unable to load recent meals');
  dashboardMeals = await getJsonOrThrow(mealsResponse, 'Unable to load dashboard meals');
  dashboardTargets = targetsResponse.ok ? await targetsResponse.json() : null;
  refreshHomePanels();
}


function handleFileSelection(event) {
  const { cameraInput, libraryInput } = getPhotoInputs();
  const file = event.target.files?.[0];
  const preview = document.getElementById('selectedImagePreview');
  const emptyState = document.getElementById('selectedImageEmpty');

  if (!file) {
    if (!getSelectedPhotoFile()) {
      clearPhotoPreview();
    }
    return;
  }

  if (event.target === cameraInput && libraryInput) {
    libraryInput.value = '';
  }
  if (event.target === libraryInput && cameraInput) {
    cameraInput.value = '';
  }
  if (currentPreviewUrl) {
    URL.revokeObjectURL(currentPreviewUrl);
  }
  currentPreviewUrl = URL.createObjectURL(file);
  preview.src = currentPreviewUrl;
  preview.hidden = false;
  emptyState.hidden = true;

  if (event.target === cameraInput && shouldPreferMobileCamera(window)) {
    const form = getPhotoCaptureForm();
    window.setTimeout(() => {
      if (form && getSelectedPhotoFile()) {
        form.requestSubmit();
      }
    }, 50);
  }
}


async function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('Unable to read image for offline queue'));
    reader.readAsDataURL(file);
  });
}


function dataUrlToBlob(dataUrl) {
  const [header, content] = dataUrl.split(',');
  const mimeType = header.match(/data:(.*?);base64/)?.[1] || 'image/jpeg';
  const bytes = atob(content);
  const array = new Uint8Array(bytes.length);
  for (let index = 0; index < bytes.length; index += 1) {
    array[index] = bytes.charCodeAt(index);
  }
  return new Blob([array], { type: mimeType });
}


function getImageCanvas(width, height) {
  if (typeof OffscreenCanvas !== 'undefined') {
    return new OffscreenCanvas(width, height);
  }
  if (typeof document === 'undefined') {
    return null;
  }
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  return canvas;
}


async function loadImageBitmapOrElement(file) {
  if (typeof createImageBitmap === 'function') {
    try {
      return await createImageBitmap(file);
    } catch (error) {
      // Fall back to an HTMLImageElement when bitmap decoding is unavailable.
    }
  }

  return new Promise((resolve, reject) => {
    const image = new Image();
    const objectUrl = URL.createObjectURL(file);
    image.onload = () => {
      URL.revokeObjectURL(objectUrl);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error('Unable to decode the photo.'));
    };
    image.src = objectUrl;
  });
}


async function canvasToBlob(canvas, type, quality) {
  if ('convertToBlob' in canvas) {
    return canvas.convertToBlob({ type, quality });
  }

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob);
        return;
      }
      reject(new Error('Unable to optimize the photo.'));
    }, type, quality);
  });
}


function renameAsJpeg(filename) {
  return (filename || 'meal-photo').replace(/\.[a-z0-9]+$/i, '') + '.jpg';
}


async function optimizePhotoForUpload(file) {
  const plan = planPhotoOptimization(file);
  if (!plan.shouldOptimize) {
    return file;
  }

  try {
    const source = await loadImageBitmapOrElement(file);
    const sourceWidth = source.width || source.naturalWidth;
    const sourceHeight = source.height || source.naturalHeight;
    const sizedPlan = planPhotoOptimization({
      ...file,
      width: sourceWidth,
      height: sourceHeight,
    });

    if (!sizedPlan.shouldOptimize) {
      return file;
    }

    const canvas = getImageCanvas(sizedPlan.targetWidth, sizedPlan.targetHeight);
    if (!canvas) {
      return file;
    }
    const context = canvas.getContext('2d', { alpha: false });
    if (!context) {
      return file;
    }

    context.drawImage(source, 0, 0, sizedPlan.targetWidth, sizedPlan.targetHeight);
    if (typeof source.close === 'function') {
      source.close();
    }

    const blob = await canvasToBlob(canvas, 'image/jpeg', sizedPlan.quality);
    if (!blob || blob.size >= file.size) {
      return file;
    }

    return new File([blob], renameAsJpeg(file.name), {
      type: 'image/jpeg',
      lastModified: Date.now(),
    });
  } catch (error) {
    return file;
  }
}


async function queueTextLikeMeal(payload, label) {
  queuePendingMeal({ kind: 'text', payload, label });
  renderTodayDashboard();
  showToast(t('home.queueAddedText'));
}


async function queuePhotoMeal(file) {
  const dataUrl = await fileToDataUrl(file);
  queuePendingMeal({
    kind: 'photo',
    label: file.name || t('home.capturePhoto'),
    payload: {
      dataUrl,
      fileName: file.name || 'queued-meal.jpg',
      mimeType: file.type || 'image/jpeg',
    },
  });
  renderTodayDashboard();
  showToast(t('home.queueAddedPhoto'));
}


async function createTextMeal(payload) {
  const response = await apiFetch(`${API.meals}/text`, {
    method: 'POST',
    body: payload,
  });
  return getJsonOrThrow(response, 'Unable to add meal from text');
}


async function submitTemplateMeal(template) {
  const status = getCaptureStatus();
  const payload = buildTextMealRequest({
    description: template.description || template.title,
    calories: template.calories,
    protein: template.protein,
    fat: template.fat,
    carbs: template.carbs,
    fiber: template.fiber,
    sugar: template.sugar,
    sodium: template.sodium,
    mealType: template.meal_type,
    notes: template.notes || `Template: ${template.title}`,
  });

  if (!navigator.onLine) {
    await queueTextLikeMeal(payload, template.title);
    showStatus(status, t('home.queueAddedText'), 'info');
    return;
  }

  try {
    showStatus(status, t('home.textAnalyzing'), 'info');
    const meal = await createTextMeal(payload);
    showStatus(status, t('home.mealAdded'), 'success');
    renderMealEditor(meal);
    await loadHomeData();
  } catch (error) {
    if (isOfflineLike(error)) {
      await queueTextLikeMeal(payload, template.title);
      showStatus(status, t('home.queueAddedText'), 'info');
      return;
    }
    showStatus(status, error.message, 'danger');
  }
}


async function handlePhotoMealSubmit(event) {
  event.preventDefault();
  if (photoSubmissionInProgress) {
    return;
  }
  const file = getSelectedPhotoFile();
  const status = getCaptureStatus();

  if (!file) {
    showStatus(status, t('home.photoRequired'), 'danger');
    return;
  }

  try {
    photoSubmissionInProgress = true;
    showStatus(status, t('home.photoPreparing'), 'info');
    const optimizedFile = await optimizePhotoForUpload(file);

    if (!navigator.onLine) {
      await queuePhotoMeal(optimizedFile);
      clearPhotoSelection();
      showStatus(status, t('home.queueAddedPhoto'), 'info');
      return;
    }

    const formData = new FormData();
    formData.append('image', optimizedFile);
    showStatus(status, t('home.photoAnalyzing'), 'info');

    const response = await apiFetch(API.meals, {
      method: 'POST',
      body: formData,
    });
    const meal = await getJsonOrThrow(response, 'Unable to add meal from photo');
    showStatus(status, t('home.mealAdded'), 'success');
    renderMealEditor(meal);
    clearPhotoSelection();
    await loadHomeData();
  } catch (error) {
    if (isOfflineLike(error)) {
      const queuedFile = await optimizePhotoForUpload(file);
      await queuePhotoMeal(queuedFile);
      clearPhotoSelection();
      showStatus(status, t('home.queueAddedPhoto'), 'info');
      return;
    }
    showStatus(status, error.message, 'danger');
  } finally {
    photoSubmissionInProgress = false;
  }
}


async function handleTextMealSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const status = getCaptureStatus();
  const description = form.foodDescription.value.trim();

  if (!description) {
    showStatus(status, t('home.textRequired'), 'danger');
    return;
  }

  const payload = buildTextMealRequest({
    description,
  });

  if (!navigator.onLine) {
    await queueTextLikeMeal(payload, description);
    form.reset();
    showStatus(status, t('home.queueAddedText'), 'info');
    return;
  }

  showStatus(status, t('home.textAnalyzing'), 'info');

  try {
    const meal = await createTextMeal(payload);
    showStatus(status, t('home.mealAdded'), 'success');
    renderMealEditor(meal);
    form.reset();
    await loadHomeData();
  } catch (error) {
    if (isOfflineLike(error)) {
      await queueTextLikeMeal(payload, description);
      form.reset();
      showStatus(status, t('home.queueAddedText'), 'info');
      return;
    }
    showStatus(status, error.message, 'danger');
  }
}


async function handleSaveMealChanges() {
  if (!currentMeal) {
    return;
  }

  const status = document.getElementById('analysisStatus');
  const fields = getAnalysisFields();
  showStatus(status, t('home.savingAdjustments'), 'info');

  try {
    const response = await apiFetch(`${API.meals}/${currentMeal.id}`, {
      method: 'PUT',
      body: buildMealUpdatePayload({
        calories: fields.calories.value,
        protein: fields.protein.value,
        fat: fields.fat.value,
        carbs: fields.carbs.value,
        fiber: fields.fiber.value,
        sugar: fields.sugar.value,
        sodium: fields.sodium.value,
        mealType: fields.mealType.value,
        consumedAt: fields.consumedAt.value,
        notes: fields.notes.value,
      }),
    });
    currentMeal = await getJsonOrThrow(response, 'Unable to save meal changes');
    originalMeal = { ...currentMeal };
    renderMealEditor(currentMeal);
    showStatus(status, t('home.mealUpdated'), 'success');
    await loadHomeData();
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}


function saveCurrentMealAsTemplate() {
  if (!currentMeal) {
    return;
  }

  saveMealTemplate(buildTemplateFromMeal(currentMeal));
  renderTemplates();
  renderTodayDashboard();
  showToast(t('home.templateSaved'));
}


function resetMealChanges() {
  if (originalMeal) {
    renderMealEditor(originalMeal);
    showStatus(document.getElementById('analysisStatus'), t('home.resetDone'), 'info');
  }
}


async function handleReanalyze() {
  if (!currentMeal) {
    return;
  }

  const corrections = document.getElementById('reanalysisCorrections').value.trim();
  const status = document.getElementById('analysisStatus');

  if (!corrections) {
    showStatus(status, t('home.correctionRequired'), 'danger');
    return;
  }

  showStatus(status, t('home.reanalyzing'), 'info');

  try {
    const response = await apiFetch(`${API.meals}/${currentMeal.id}/reanalyze`, {
      method: 'POST',
      body: { corrections: { note: corrections } },
    });
    currentMeal = await getJsonOrThrow(response, 'Unable to reanalyze meal');
    originalMeal = { ...currentMeal };
    renderMealEditor(currentMeal);
    document.getElementById('reanalysisCorrections').value = '';
    showStatus(status, t('home.reanalysisUpdated'), 'success');
    await loadHomeData();
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}


function initializeModeSwitch() {
  const buttons = document.querySelectorAll('[data-capture-mode]');
  const sections = document.querySelectorAll('[data-mode-panel]');

  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      buttons.forEach((item) => item.classList.toggle('active', item === button));
      sections.forEach((panel) => {
        panel.hidden = panel.dataset.modePanel !== button.dataset.captureMode;
      });
    });
  });
}


function updateCaptureAccessUi() {
  const preferMobileCamera = shouldPreferMobileCamera(window);
  document.body.classList.toggle('mobile-camera-preferred', preferMobileCamera);
  document.querySelectorAll('[data-mobile-camera-only]').forEach((element) => {
    element.hidden = !preferMobileCamera;
  });
  document.querySelectorAll('[data-desktop-photo-only]').forEach((element) => {
    element.hidden = preferMobileCamera;
  });
}


function initializePhotoCapture() {
  const { cameraInput, libraryInput } = getPhotoInputs();
  const takePhotoButton = document.getElementById('takePhotoButton');

  cameraInput?.addEventListener('change', handleFileSelection);
  libraryInput?.addEventListener('change', handleFileSelection);
  takePhotoButton?.addEventListener('click', () => {
    cameraInput?.click();
  });

  updateCaptureAccessUi();
  window.addEventListener('resize', updateCaptureAccessUi);
}


function initializeVoiceInput() {
  const button = document.getElementById('voiceInputButton');
  const textarea = document.querySelector('#textMealForm textarea[name="foodDescription"]');
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!button || !textarea) {
    return;
  }

  if (!SpeechRecognition) {
    button.disabled = true;
    button.title = t('home.voiceUnsupported');
    return;
  }

  voiceRecognition = new SpeechRecognition();
  voiceRecognition.lang = document.documentElement.lang === 'cs' ? 'cs-CZ' : 'en-US';
  voiceRecognition.interimResults = true;
  voiceRecognition.continuous = false;

  voiceRecognition.addEventListener('result', (event) => {
    const transcript = Array.from(event.results)
      .map((result) => result[0]?.transcript || '')
      .join(' ')
      .trim();
    textarea.value = transcript;
  });

  voiceRecognition.addEventListener('start', () => {
    isListening = true;
    button.textContent = t('button.stopVoice');
    showStatus(getCaptureStatus(), t('home.voiceActive'), 'info');
  });

  voiceRecognition.addEventListener('end', () => {
    isListening = false;
    button.textContent = t('button.startVoice');
  });

  button.addEventListener('click', () => {
    if (!voiceRecognition) {
      return;
    }

    if (isListening) {
      voiceRecognition.stop();
      showStatus(getCaptureStatus(), t('home.voiceStopped'), 'info');
      return;
    }

    voiceRecognition.start();
  });
}

function refreshVoiceUi() {
  const button = document.getElementById('voiceInputButton');
  if (!button) {
    return;
  }

  if (button.disabled) {
    button.title = t('home.voiceUnsupported');
    return;
  }

  if (voiceRecognition) {
    voiceRecognition.lang = document.documentElement.lang === 'cs' ? 'cs-CZ' : 'en-US';
  }

  button.textContent = t(isListening ? 'button.stopVoice' : 'button.startVoice');
}


async function syncPendingQueue() {
  if (syncInProgress || !navigator.onLine) {
    return;
  }

  const queue = [...getPendingMealQueue()].reverse();
  if (!queue.length) {
    renderTodayDashboard();
    return;
  }

  syncInProgress = true;
  showStatus(getCaptureStatus(), t('home.queueSyncing'), 'info');

  let syncedAny = false;
  let failed = false;

  for (const entry of queue) {
    try {
      if (entry.kind === 'photo') {
        const blob = dataUrlToBlob(entry.payload.dataUrl);
        const formData = new FormData();
        formData.append('image', new File([blob], entry.payload.fileName, { type: entry.payload.mimeType }));
        const response = await apiFetch(API.meals, { method: 'POST', body: formData });
        await getJsonOrThrow(response, 'Unable to sync queued photo');
      } else {
        await createTextMeal(entry.payload);
      }

      removePendingMeal(entry.id);
      syncedAny = true;
    } catch (error) {
      failed = true;
      if (isOfflineLike(error)) {
        break;
      }
    }
  }

  syncInProgress = false;
  await loadHomeData();
  showStatus(getCaptureStatus(), failed ? t('home.queueSyncError') : t('home.queueSynced'), failed ? 'danger' : 'success');
  if (syncedAny) {
    showToast(failed ? t('home.queueSyncError') : t('home.queueSynced'));
  }
}


document.addEventListener('DOMContentLoaded', async () => {
  await setupPage();

  initializeModeSwitch();
  initializePhotoCapture();
  initializeVoiceInput();

  document.getElementById('photoMealForm').addEventListener('submit', handlePhotoMealSubmit);
  document.getElementById('textMealForm').addEventListener('submit', handleTextMealSubmit);
  document.getElementById('saveAnalysisButton').addEventListener('click', handleSaveMealChanges);
  document.getElementById('saveTemplateButton').addEventListener('click', saveCurrentMealAsTemplate);
  document.getElementById('resetAnalysisButton').addEventListener('click', resetMealChanges);
  document.getElementById('reanalyzeButton').addEventListener('click', handleReanalyze);
  document.getElementById('syncQueueButton').addEventListener('click', syncPendingQueue);

  window.addEventListener('food-reader:templateschange', () => {
    renderTemplates();
    renderTodayDashboard();
  });
  window.addEventListener('food-reader:queuechange', renderTodayDashboard);
  window.addEventListener('food-reader:localechange', () => {
    refreshHomePanels();
    refreshVoiceUi();
  });
  window.addEventListener('online', syncPendingQueue);

  await loadHomeData();
  await syncPendingQueue();
  refreshVoiceUi();
});
