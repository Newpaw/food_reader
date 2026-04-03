import {
  API,
  apiFetch,
  formatDateTime,
  getLocalDateKey,
  getMealDisplayName,
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
} from './common.js?v=20260403-11';


let currentMeal = null;
let originalMeal = null;
let voiceRecognition = null;
let isListening = false;
let syncInProgress = false;
let currentPreviewUrl = null;
let photoSubmissionInProgress = false;
let isAnalysisEditing = false;
let activeVoiceButton = null;
let activeVoiceTextarea = null;
let activeVoiceBaseText = '';

const MAX_UPLOAD_DIMENSION = 1600;
const MAX_UPLOAD_BYTES = 1_800_000;
const UPLOAD_QUALITY = 0.82;
const MIN_UPLOAD_DIMENSION = 960;
const MIN_UPLOAD_QUALITY = 0.55;
const UPLOAD_QUALITY_STEP = 0.08;
const UPLOAD_SCALE_STEP = 0.85;
const BROWSER_SAFE_UPLOAD_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);
const ANALYSIS_LOADING_ROTATION_MS = 1800;
const ANALYSIS_LOADING_LONG_WAIT_MS = 5200;

let captureLoadingRotationId = null;
let captureLoadingLongWaitId = null;


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
      (
        Number(fileLike?.size || 0) > maxBytes ||
        largestSide > maxDimension ||
        !BROWSER_SAFE_UPLOAD_TYPES.has(fileLike?.type || '')
      ),
  };
}


export function scaleImageDimensions(width, height, maxDimension) {
  const safeWidth = Math.max(1, Math.round(Number(width) || 0));
  const safeHeight = Math.max(1, Math.round(Number(height) || 0));
  const safeMaxDimension = Math.max(1, Math.round(Number(maxDimension) || 0));
  const largestSide = Math.max(safeWidth, safeHeight);
  if (!largestSide || largestSide <= safeMaxDimension) {
    return { width: safeWidth, height: safeHeight };
  }

  const scale = safeMaxDimension / largestSide;
  return {
    width: Math.max(1, Math.round(safeWidth * scale)),
    height: Math.max(1, Math.round(safeHeight * scale)),
  };
}


export function buildPhotoOptimizationPasses(width, height, options = {}) {
  const maxDimension = options.maxDimension ?? MAX_UPLOAD_DIMENSION;
  const startingQuality = options.quality ?? UPLOAD_QUALITY;
  const minimumDimension = options.minDimension ?? MIN_UPLOAD_DIMENSION;
  const minimumQuality = options.minQuality ?? MIN_UPLOAD_QUALITY;
  const qualityStep = options.qualityStep ?? UPLOAD_QUALITY_STEP;
  const scaleStep = options.scaleStep ?? UPLOAD_SCALE_STEP;

  const passes = [];
  let currentSize = scaleImageDimensions(width, height, maxDimension);

  while (true) {
    let quality = startingQuality;
    while (true) {
      passes.push({
        width: currentSize.width,
        height: currentSize.height,
        quality: Number(quality.toFixed(2)),
      });
      if (quality <= minimumQuality) {
        break;
      }
      quality = Math.max(minimumQuality, quality - qualityStep);
    }

    const largestSide = Math.max(currentSize.width, currentSize.height);
    if (largestSide <= minimumDimension) {
      break;
    }

    const nextLargestSide = Math.max(minimumDimension, Math.round(largestSide * scaleStep));
    const nextSize = scaleImageDimensions(currentSize.width, currentSize.height, nextLargestSide);
    if (nextSize.width === currentSize.width && nextSize.height === currentSize.height) {
      break;
    }
    currentSize = nextSize;
  }

  return passes;
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


function getPhotoAnalysisContext() {
  return document.getElementById('photoAnalysisContext')?.value.trim() || '';
}


function clearPhotoAnalysisContext() {
  const contextField = document.getElementById('photoAnalysisContext');
  if (contextField) {
    contextField.value = '';
  }
}


function stopCaptureLoadingTimers() {
  window.clearInterval(captureLoadingRotationId);
  window.clearTimeout(captureLoadingLongWaitId);
  captureLoadingRotationId = null;
  captureLoadingLongWaitId = null;
}


function getAnalysisLoadingSequence(mode) {
  if (mode === 'text') {
    return [
      t('home.loadingStageTextRead'),
      t('home.loadingStageEstimate'),
      t('home.loadingStageReview'),
    ];
  }

  return [
    t('home.loadingStageUpload'),
    t('home.loadingStageDetect'),
    t('home.loadingStageEstimate'),
  ];
}


function getCurrentPreviewSource() {
  const preview = document.getElementById('selectedImagePreview');
  if (preview?.getAttribute('src')) {
    return preview.getAttribute('src');
  }
  return currentPreviewUrl;
}


function setCaptureLoading(active, options = {}) {
  const loading = document.getElementById('captureLoading');
  const loadingTitle = document.getElementById('captureLoadingTitle');
  const loadingMessage = document.getElementById('captureLoadingMessage');
  const loadingDetail = document.getElementById('captureLoadingDetail');
  const loadingMedia = document.getElementById('captureLoadingMedia');
  const loadingThumb = document.getElementById('captureLoadingThumb');
  if (!loading || !loadingTitle || !loadingMessage || !loadingDetail || !loadingMedia || !loadingThumb) {
    return;
  }

  stopCaptureLoadingTimers();

  if (!active) {
    loading.hidden = true;
    document.body.classList.remove('modal-open');
  } else {
    const mode = options.mode === 'text' ? 'text' : 'photo';
    const primaryMessage = options.message || (mode === 'text' ? t('home.textAnalyzing') : t('home.photoAnalyzing'));
    const thumbnailSrc = mode === 'photo' ? getCurrentPreviewSource() : '';
    const sequence = getAnalysisLoadingSequence(mode).filter((entry) => entry && entry !== primaryMessage);

    loadingTitle.textContent = t('home.analysisLoadingTitle');
    loadingMessage.textContent = primaryMessage;
    loadingDetail.textContent = t('home.analysisLoadingBody');
    loading.dataset.mode = mode;
    loading.hidden = false;
    document.body.classList.add('modal-open');

    if (thumbnailSrc) {
      loadingThumb.src = thumbnailSrc;
      loadingMedia.hidden = false;
    } else {
      loadingThumb.removeAttribute('src');
      loadingMedia.hidden = true;
    }

    if (sequence.length) {
      let rotationIndex = 0;
      captureLoadingRotationId = window.setInterval(() => {
        loadingMessage.textContent = sequence[rotationIndex % sequence.length];
        rotationIndex += 1;
      }, ANALYSIS_LOADING_ROTATION_MS);
    }

    captureLoadingLongWaitId = window.setTimeout(() => {
      loadingDetail.textContent = t('home.analysisLoadingLongWait');
    }, ANALYSIS_LOADING_LONG_WAIT_MS);
  }

  const analyzeButton = document.getElementById('analyzePhotoButton');
  const stickyAnalyzeButton = document.getElementById('analyzePhotoStickyButton');
  const takePhotoButton = document.getElementById('takePhotoButton');
  const chooseGalleryButton = document.getElementById('chooseGalleryButton');
  const uploadPreviewButton = document.getElementById('uploadPreviewButton');
  const photoContext = document.getElementById('photoAnalysisContext');
  const photoContextVoiceButton = document.getElementById('photoContextVoiceButton');
  const textDescription = document.getElementById('textMealDescription');
  const textVoiceButton = document.getElementById('voiceInputButton');
  const textSubmitButton = document.querySelector('#textMealForm button[type="submit"]');
  if (analyzeButton) {
    analyzeButton.disabled = active || !getSelectedPhotoFile();
  }
  if (stickyAnalyzeButton) {
    stickyAnalyzeButton.disabled = active || !getSelectedPhotoFile();
  }
  if (takePhotoButton) {
    takePhotoButton.disabled = active;
  }
  if (chooseGalleryButton) {
    chooseGalleryButton.disabled = active;
  }
  if (uploadPreviewButton) {
    uploadPreviewButton.disabled = active;
  }
  if (photoContext) {
    photoContext.disabled = active;
  }
  if (photoContextVoiceButton) {
    photoContextVoiceButton.disabled = active;
  }
  if (textDescription) {
    textDescription.disabled = active;
  }
  if (textVoiceButton) {
    textVoiceButton.disabled = active;
  }
  if (textSubmitButton) {
    textSubmitButton.disabled = active;
  }
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


function updatePhotoSubmitState() {
  const analyzeButton = document.getElementById('analyzePhotoButton');
  const stickyBar = document.getElementById('analyzePhotoStickyBar');
  const stickyButton = document.getElementById('analyzePhotoStickyButton');
  const photoForm = document.getElementById('photoMealForm');
  const previewButton = document.getElementById('uploadPreviewButton');
  if (!analyzeButton || !photoForm) {
    return;
  }

  const hasPhoto = Boolean(getSelectedPhotoFile());
  const isPhotoModeVisible = !photoForm.hidden;
  const disabled = photoSubmissionInProgress || !hasPhoto;

  analyzeButton.disabled = disabled;
  if (stickyButton) {
    stickyButton.disabled = disabled;
  }
  if (stickyBar) {
    stickyBar.hidden = !hasPhoto || !isPhotoModeVisible;
  }
  if (previewButton) {
    previewButton.classList.toggle('has-image', hasPhoto);
  }
  document.body.classList.toggle('capture-photo-ready', hasPhoto && isPhotoModeVisible);
}


function openPrimaryPhotoPicker() {
  const { cameraInput, libraryInput } = getPhotoInputs();
  cameraInput?.click();
  if (!cameraInput) {
    libraryInput?.click();
  }
}


function openGalleryPicker() {
  const { libraryInput } = getPhotoInputs();
  libraryInput?.click();
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
  updatePhotoSubmitState();
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

function formatMetricValue(value, unit = '') {
  const numeric = Number(value || 0);
  const rounded = Number.isInteger(numeric) ? numeric : Math.round(numeric * 10) / 10;
  return unit ? `${rounded} ${unit}` : `${rounded}`;
}


export function summarizeMealHighlight(meal) {
  const calories = Number(meal?.calories || 0);
  const protein = Number(meal?.protein || 0);
  const fat = Number(meal?.fat || 0);
  const carbs = Number(meal?.carbs || 0);
  const fiber = Number(meal?.fiber || 0);

  if (protein >= 35) {
    return {
      title: t('home.insightHighProteinTitle'),
      body: t('home.insightHighProteinBody'),
    };
  }

  if (fiber >= 8) {
    return {
      title: t('home.insightHighFiberTitle'),
      body: t('home.insightHighFiberBody'),
    };
  }

  if (calories >= 850 || (fat >= 30 && carbs >= 45)) {
    return {
      title: t('home.insightRichTitle'),
      body: t('home.insightRichBody'),
    };
  }

  return {
    title: t('home.insightBalancedTitle'),
    body: t('home.insightBalancedBody'),
  };
}


function scrollToAnalysisPanel() {
  const panel = document.getElementById('analysisPanel');
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => {
      panel?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}


function scrollToCapturePanel() {
  const panel = document.querySelector('.primary-capture-panel');
  window.requestAnimationFrame(() => {
    panel?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
}


function setAnalysisEditing(editing) {
  isAnalysisEditing = editing;
  const viewActions = document.getElementById('analysisViewActions');
  const editPanel = document.getElementById('analysisEditPanel');

  if (viewActions) {
    viewActions.hidden = editing;
  }
  if (editPanel) {
    editPanel.hidden = !editing;
  }
}


function toggleRefineAnalysisPanel(open) {
  const panel = document.getElementById('refineAnalysisPanel');
  const textarea = document.getElementById('reanalysisCorrections');
  if (!panel) {
    return;
  }

  panel.hidden = !open;
  if (open) {
    textarea?.focus();
  }
}


function renderMealInsight(meal) {
  const highlight = document.getElementById('analysisHighlight');
  if (!highlight) {
    return;
  }

  const insight = summarizeMealHighlight(meal);
  highlight.hidden = false;
  highlight.innerHTML = `
    <p class="eyebrow">${insight.title}</p>
    <p>${insight.body}</p>
  `;
}


function renderMealSummary(meal) {
  const primaryMetrics = document.getElementById('analysisPrimaryMetrics');
  const detailRows = document.getElementById('analysisDetailRows');
  const details = document.getElementById('analysisNutritionDetails');
  if (!primaryMetrics || !detailRows || !details) {
    return;
  }

  primaryMetrics.innerHTML = `
    <article class="analysis-metric-card analysis-metric-card-featured">
      <span>${t('label.calories')}</span>
      <strong>${formatMetricValue(meal.calories)}</strong>
      <small>kcal</small>
    </article>
    <article class="analysis-metric-card">
      <span>${t('label.protein')}</span>
      <strong>${formatMetricValue(meal.protein)}</strong>
      <small>g</small>
    </article>
    <article class="analysis-metric-card">
      <span>${t('label.carbs')}</span>
      <strong>${formatMetricValue(meal.carbs)}</strong>
      <small>g</small>
    </article>
    <article class="analysis-metric-card">
      <span>${t('label.fat')}</span>
      <strong>${formatMetricValue(meal.fat)}</strong>
      <small>g</small>
    </article>
  `;

  const secondaryRows = [
    [t('label.fiber'), formatMetricValue(meal.fiber, 'g')],
    [t('label.sugar'), formatMetricValue(meal.sugar, 'g')],
    [t('label.sodium'), formatMetricValue(meal.sodium, 'mg')],
    [t('label.mealType'), t(`option.${meal.meal_type}`)],
    [t('label.notes'), meal.notes?.trim() || t('history.noNotes')],
  ];

  detailRows.innerHTML = secondaryRows
    .map(
      ([label, value]) => `
        <div class="analysis-detail-row">
          <span>${label}</span>
          <strong>${value}</strong>
        </div>
      `,
    )
    .join('');
  details.open = false;
  renderMealInsight(meal);
}


function hideMealEditor() {
  currentMeal = null;
  originalMeal = null;
  isAnalysisEditing = false;
  const panel = document.getElementById('analysisPanel');
  const status = document.getElementById('analysisStatus');
  const reanalysis = document.getElementById('reanalysisCorrections');
  const details = document.getElementById('analysisNutritionDetails');
  if (panel) {
    panel.hidden = true;
  }
  if (status) {
    showStatus(status, '', 'info');
  }
  if (reanalysis) {
    reanalysis.value = '';
  }
  if (details) {
    details.open = false;
  }
  toggleRefineAnalysisPanel(false);
  setAnalysisEditing(false);
}


function renderMealEditor(meal, { scroll = true, editing = false } = {}) {
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
    <div class="analysis-preview-media">
      <img src="${imageUrl}" alt="${mealName}" class="analysis-preview-image">
    </div>
    <div class="analysis-preview-copy">
      <p class="eyebrow">${t('home.latestEntry')}</p>
      <h2>${mealName}</h2>
      <p class="analysis-preview-meta">${formatDateTime(meal.consumed_at)}</p>
    </div>
  `;

  renderMealSummary(meal);
  const isImageMeal = meal.image_url !== '/assets/images/text-meal-placeholder.svg';
  const refineButton = document.getElementById('toggleRefineAnalysisButton');
  if (refineButton) {
    refineButton.hidden = !isImageMeal;
  }
  toggleRefineAnalysisPanel(false);
  setAnalysisEditing(editing);
  if (scroll) {
    scrollToAnalysisPanel();
  }
}


function renderCaptureQueueNotice() {
  const wrapper = document.getElementById('captureQueueNotice');
  const label = document.getElementById('captureQueueLabel');
  const syncButton = document.getElementById('syncQueueButton');
  if (!wrapper || !label || !syncButton) {
    return;
  }

  const queueCount = getPendingMealQueue().length;
  wrapper.hidden = queueCount === 0;
  syncButton.hidden = queueCount === 0;
  if (!queueCount) {
    return;
  }

  label.textContent = t('home.queueCompact', { count: queueCount });
}


async function loadHomeData() {
  renderCaptureQueueNotice();
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
  updatePhotoSubmitState();
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


function fileFromBlob(blob, originalFilename) {
  return new File([blob], renameAsJpeg(originalFilename), {
    type: 'image/jpeg',
    lastModified: Date.now(),
  });
}


async function optimizePhotoForUpload(file) {
  const plan = planPhotoOptimization(file);
  if (!plan.shouldOptimize) {
    return file;
  }

  let source = null;
  try {
    source = await loadImageBitmapOrElement(file);
    const sourceWidth = source.width || source.naturalWidth;
    const sourceHeight = source.height || source.naturalHeight;
    if (!sourceWidth || !sourceHeight) {
      return file;
    }

    const sizedPlan = planPhotoOptimization({ ...file, width: sourceWidth, height: sourceHeight });
    const optimizationPasses = buildPhotoOptimizationPasses(sourceWidth, sourceHeight, {
      maxDimension: sizedPlan.maxDimension,
      quality: sizedPlan.quality,
    });

    let bestBlob = null;

    for (const pass of optimizationPasses) {
      const canvas = getImageCanvas(pass.width, pass.height);
      if (!canvas) {
        continue;
      }
      const context = canvas.getContext('2d', { alpha: false });
      if (!context) {
        continue;
      }

      // JPEG strips transparency, so fill the background explicitly first.
      context.fillStyle = '#ffffff';
      context.fillRect(0, 0, pass.width, pass.height);
      context.drawImage(source, 0, 0, pass.width, pass.height);

      const blob = await canvasToBlob(canvas, 'image/jpeg', pass.quality);
      if (!blob) {
        continue;
      }
      if (!bestBlob || blob.size < bestBlob.size) {
        bestBlob = blob;
      }
      if (blob.size <= sizedPlan.maxBytes) {
        return fileFromBlob(blob, file.name);
      }
    }

    if (bestBlob && bestBlob.size < file.size) {
      return fileFromBlob(bestBlob, file.name);
    }

    return file;
  } catch (error) {
    return file;
  } finally {
    if (typeof source?.close === 'function') {
      source.close();
    }
  }
}


async function queueTextLikeMeal(payload, label) {
  queuePendingMeal({ kind: 'text', payload, label });
  renderCaptureQueueNotice();
  showToast(t('home.queueAddedText'));
}


async function queuePhotoMeal(file) {
  const dataUrl = await fileToDataUrl(file);
  const analysisContext = getPhotoAnalysisContext();
  queuePendingMeal({
    kind: 'photo',
    label: file.name || t('home.capturePhoto'),
    payload: {
      dataUrl,
      fileName: file.name || 'queued-meal.jpg',
      mimeType: file.type || 'image/jpeg',
      analysisContext,
    },
  });
  renderCaptureQueueNotice();
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
    setCaptureLoading(true, { mode: 'text', message: t('home.textAnalyzing') });
    showStatus(status, t('home.textAnalyzing'), 'info');
    const meal = await createTextMeal(payload);
    await loadHomeData();
    showStatus(status, t('home.mealAdded'), 'success');
    renderMealEditor(meal);
  } catch (error) {
    if (isOfflineLike(error)) {
      await queueTextLikeMeal(payload, template.title);
      showStatus(status, t('home.queueAddedText'), 'info');
      return;
    }
    showStatus(status, error.message, 'danger');
  } finally {
    setCaptureLoading(false);
  }
}


async function handlePhotoMealSubmit(event) {
  event.preventDefault();
  if (photoSubmissionInProgress) {
    return;
  }
  const file = getSelectedPhotoFile();
  const status = getCaptureStatus();
  const analysisContext = getPhotoAnalysisContext();

  if (!file) {
    showStatus(status, t('home.photoRequired'), 'danger');
    return;
  }

  try {
    photoSubmissionInProgress = true;
    setCaptureLoading(true, { mode: 'photo', message: t('home.photoPreparing') });
    showStatus(status, t('home.photoPreparing'), 'info');
    const optimizedFile = await optimizePhotoForUpload(file);

    if (!navigator.onLine) {
      await queuePhotoMeal(optimizedFile);
      clearPhotoSelection();
      clearPhotoAnalysisContext();
      showStatus(status, t('home.queueAddedPhoto'), 'info');
      return;
    }

    const formData = new FormData();
    formData.append('image', optimizedFile);
    if (analysisContext) {
      formData.append('analysis_context', analysisContext);
    }
    setCaptureLoading(true, { mode: 'photo', message: t('home.photoAnalyzing') });
    showStatus(status, t('home.photoAnalyzing'), 'info');

    const response = await apiFetch(API.meals, {
      method: 'POST',
      body: formData,
    });
    const meal = await getJsonOrThrow(response, 'Unable to add meal from photo');
    clearPhotoSelection();
    clearPhotoAnalysisContext();
    await loadHomeData();
    showStatus(status, t('home.mealAdded'), 'success');
    renderMealEditor(meal);
  } catch (error) {
    if (isOfflineLike(error)) {
      const queuedFile = await optimizePhotoForUpload(file);
      await queuePhotoMeal(queuedFile);
      clearPhotoSelection();
      clearPhotoAnalysisContext();
      showStatus(status, t('home.queueAddedPhoto'), 'info');
      return;
    }
    showStatus(status, error.message, 'danger');
  } finally {
    photoSubmissionInProgress = false;
    setCaptureLoading(false);
    updatePhotoSubmitState();
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

  try {
    setCaptureLoading(true, { mode: 'text', message: t('home.textAnalyzing') });
    showStatus(status, t('home.textAnalyzing'), 'info');
    const meal = await createTextMeal(payload);
    await loadHomeData();
    showStatus(status, t('home.mealAdded'), 'success');
    renderMealEditor(meal);
    form.reset();
  } catch (error) {
    if (isOfflineLike(error)) {
      await queueTextLikeMeal(payload, description);
      form.reset();
      showStatus(status, t('home.queueAddedText'), 'info');
      return;
    }
    showStatus(status, error.message, 'danger');
  } finally {
    setCaptureLoading(false);
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
    await loadHomeData();
    renderMealEditor(currentMeal);
    showStatus(status, t('home.mealUpdated'), 'success');
  } catch (error) {
    showStatus(status, error.message, 'danger');
  }
}


async function handleDeleteMeal() {
  if (!currentMeal || !window.confirm(t('home.deleteConfirm'))) {
    return;
  }

  const status = document.getElementById('analysisStatus');
  showStatus(status, t('button.delete'), 'info');

  try {
    const response = await apiFetch(`${API.meals}/${currentMeal.id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      await getJsonOrThrow(response, 'Unable to delete meal');
    }
    hideMealEditor();
    await loadHomeData();
    showStatus(getCaptureStatus(), t('home.mealDeleted'), 'success');
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
    renderMealEditor(originalMeal, { scroll: false, editing: true });
    showStatus(document.getElementById('analysisStatus'), t('home.resetDone'), 'info');
  }
}


function startAnotherMeal() {
  hideMealEditor();
  showStatus(getCaptureStatus(), '', 'info');
  scrollToCapturePanel();
}


function beginMealEditing() {
  if (!currentMeal) {
    return;
  }

  renderMealEditor(currentMeal, { scroll: false, editing: true });
}


function cancelMealEditing() {
  if (!originalMeal) {
    return;
  }

  renderMealEditor(originalMeal, { scroll: false, editing: false });
}


function beginMealRefinement() {
  if (!currentMeal) {
    return;
  }

  toggleRefineAnalysisPanel(true);
}


function cancelMealRefinement() {
  const reanalysis = document.getElementById('reanalysisCorrections');
  if (reanalysis) {
    reanalysis.value = '';
  }
  toggleRefineAnalysisPanel(false);
  showStatus(document.getElementById('analysisStatus'), t('home.refineCancelled'), 'info');
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
      body: { refinement_context: corrections },
    });
    currentMeal = await getJsonOrThrow(response, 'Unable to reanalyze meal');
    originalMeal = { ...currentMeal };
    await loadHomeData();
    renderMealEditor(currentMeal);
    document.getElementById('reanalysisCorrections').value = '';
    toggleRefineAnalysisPanel(false);
    showStatus(status, t('home.reanalysisUpdated'), 'success');
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
      updatePhotoSubmitState();
    });
  });
}


function updateCaptureAccessUi() {
  document.body.classList.toggle('mobile-camera-preferred', shouldPreferMobileCamera(window));
}


function initializePhotoCapture() {
  const { cameraInput, libraryInput } = getPhotoInputs();
  const photoMealForm = document.getElementById('photoMealForm');
  const takePhotoButton = document.getElementById('takePhotoButton');
  const uploadPreviewButton = document.getElementById('uploadPreviewButton');
  const chooseGalleryButton = document.getElementById('chooseGalleryButton');
  const stickyAnalyzeButton = document.getElementById('analyzePhotoStickyButton');

  cameraInput?.addEventListener('change', handleFileSelection);
  libraryInput?.addEventListener('change', handleFileSelection);
  takePhotoButton?.addEventListener('click', openPrimaryPhotoPicker);
  uploadPreviewButton?.addEventListener('click', openPrimaryPhotoPicker);
  chooseGalleryButton?.addEventListener('click', openGalleryPicker);
  stickyAnalyzeButton?.addEventListener('click', () => {
    photoMealForm?.requestSubmit();
  });

  updateCaptureAccessUi();
  updatePhotoSubmitState();
  window.addEventListener('resize', updateCaptureAccessUi);
}


function setVoiceButtonsIdle() {
  document.querySelectorAll('[data-voice-target]').forEach((button) => {
    button.textContent = t('button.startVoice');
  });
}


function initializeVoiceInput() {
  const buttons = Array.from(document.querySelectorAll('[data-voice-target]'));
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!buttons.length) {
    return;
  }

  if (!SpeechRecognition) {
    buttons.forEach((button) => {
      button.disabled = true;
      button.title = t('home.voiceUnsupported');
    });
    return;
  }

  voiceRecognition = new SpeechRecognition();
  voiceRecognition.lang = document.documentElement.lang === 'cs' ? 'cs-CZ' : 'en-US';
  voiceRecognition.interimResults = true;
  voiceRecognition.continuous = false;

  voiceRecognition.addEventListener('result', (event) => {
    if (!activeVoiceTextarea) {
      return;
    }

    const transcript = Array.from(event.results)
      .map((result) => result[0]?.transcript || '')
      .join(' ')
      .trim();
    activeVoiceTextarea.value = [activeVoiceBaseText, transcript].filter(Boolean).join(' ').trim();
  });

  voiceRecognition.addEventListener('start', () => {
    isListening = true;
    if (activeVoiceButton) {
      activeVoiceButton.textContent = t('button.stopVoice');
    }
    showStatus(getCaptureStatus(), t('home.voiceActive'), 'info');
  });

  voiceRecognition.addEventListener('end', () => {
    isListening = false;
    activeVoiceButton = null;
    activeVoiceTextarea = null;
    activeVoiceBaseText = '';
    setVoiceButtonsIdle();
  });

  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      if (!voiceRecognition) {
        return;
      }

      if (isListening && activeVoiceButton === button) {
        voiceRecognition.stop();
        showStatus(getCaptureStatus(), t('home.voiceStopped'), 'info');
        return;
      }

      if (isListening) {
        voiceRecognition.stop();
      }

      activeVoiceButton = button;
      activeVoiceTextarea = document.getElementById(button.dataset.voiceTarget);
      activeVoiceBaseText = activeVoiceTextarea?.value.trim() || '';
      voiceRecognition.start();
    });
  });
}

function refreshVoiceUi() {
  const buttons = Array.from(document.querySelectorAll('[data-voice-target]'));
  if (!buttons.length) {
    return;
  }

  if (buttons[0].disabled) {
    buttons.forEach((button) => {
      button.title = t('home.voiceUnsupported');
    });
    return;
  }

  if (voiceRecognition) {
    voiceRecognition.lang = document.documentElement.lang === 'cs' ? 'cs-CZ' : 'en-US';
  }

  setVoiceButtonsIdle();
  if (isListening && activeVoiceButton) {
    activeVoiceButton.textContent = t('button.stopVoice');
  }
}


async function syncPendingQueue() {
  if (syncInProgress || !navigator.onLine) {
    return;
  }

  const queue = [...getPendingMealQueue()].reverse();
  if (!queue.length) {
    renderCaptureQueueNotice();
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
        if (entry.payload.analysisContext) {
          formData.append('analysis_context', entry.payload.analysisContext);
        }
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
  document.getElementById('editAnalysisButton').addEventListener('click', beginMealEditing);
  document.getElementById('toggleRefineAnalysisButton').addEventListener('click', beginMealRefinement);
  document.getElementById('addAnotherMealButton').addEventListener('click', startAnotherMeal);
  document.getElementById('saveAnalysisButton').addEventListener('click', handleSaveMealChanges);
  document.getElementById('saveTemplateButton').addEventListener('click', saveCurrentMealAsTemplate);
  document.getElementById('resetAnalysisButton').addEventListener('click', resetMealChanges);
  document.getElementById('cancelAnalysisEditButton').addEventListener('click', cancelMealEditing);
  document.getElementById('cancelRefineAnalysisButton').addEventListener('click', cancelMealRefinement);
  document.getElementById('deleteAnalysisButton').addEventListener('click', handleDeleteMeal);
  document.getElementById('reanalyzeButton').addEventListener('click', handleReanalyze);
  document.getElementById('syncQueueButton').addEventListener('click', syncPendingQueue);
  document.querySelectorAll('[data-language-select]').forEach((control) => {
    control.addEventListener('change', () => {
      if (currentMeal) {
        renderMealEditor(currentMeal, { scroll: false, editing: isAnalysisEditing });
      }
      refreshVoiceUi();
    });
  });

  window.addEventListener('food-reader:templateschange', () => {
    renderCaptureQueueNotice();
  });
  window.addEventListener('food-reader:queuechange', renderCaptureQueueNotice);
  window.addEventListener('food-reader:localechange', () => {
    renderCaptureQueueNotice();
    refreshVoiceUi();
  });
  window.addEventListener('online', syncPendingQueue);

  await loadHomeData();
  await syncPendingQueue();
  refreshVoiceUi();
});
