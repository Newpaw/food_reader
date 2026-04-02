function normalizeBaseUrl(value) {
  return value ? value.replace(/\/+$/, '') : '';
}

export function shouldUseSplitLocalApi(locationLike) {
  const port = String(locationLike?.port || '');
  const likelyStaticDevPorts = new Set(['8080', '4173', '5173', '5500']);
  return likelyStaticDevPorts.has(port);
}

function resolveApiBaseUrl() {
  if (typeof window === 'undefined') {
    return '';
  }

  const { protocol, hostname, port } = window.location;
  const locationLike = { protocol, hostname, port };
  const storedBaseUrl = window.localStorage.getItem('food-reader-api-base');
  const runtimeBaseUrl =
    window.FOOD_READER_API_BASE ||
    document.querySelector('meta[name="food-reader-api-base"]')?.content;
  const splitLocalBaseUrl = `${protocol}//${hostname}:8000`;

  if (storedBaseUrl) {
    const normalizedStoredBaseUrl = normalizeBaseUrl(storedBaseUrl);

    // Ignore the old split-dev override when the app is served by Nginx on 18080.
    if (shouldUseSplitLocalApi(locationLike) || normalizedStoredBaseUrl !== splitLocalBaseUrl) {
      return normalizedStoredBaseUrl;
    }
  }

  if (runtimeBaseUrl) {
    return normalizeBaseUrl(runtimeBaseUrl);
  }

  if (shouldUseSplitLocalApi(locationLike)) {
    return splitLocalBaseUrl;
  }

  return '';
}

export const API_BASE_URL = resolveApiBaseUrl();

export const API = {
  login: `${API_BASE_URL}/auth/login`,
  register: `${API_BASE_URL}/auth/register`,
  currentUser: `${API_BASE_URL}/users/me`,
  meals: `${API_BASE_URL}/me/meals`,
  summary: `${API_BASE_URL}/me/summary`,
  profile: `${API_BASE_URL}/profile`,
};

export function resolveAssetUrl(url) {
  if (!url) {
    return url;
  }

  if (/^https?:\/\//i.test(url) || url.startsWith('data:') || url.startsWith('blob:')) {
    return url;
  }

  if (url.startsWith('/uploads/')) {
    return `${API_BASE_URL}${url}`;
  }

  return url;
}

function capitalizeLabel(value) {
  if (!value) {
    return '';
  }

  return value.charAt(0).toUpperCase() + value.slice(1);
}

function truncateLabel(value, maxLength = 40) {
  if (value.length <= maxLength) {
    return value;
  }

  const truncated = value.slice(0, maxLength).trim();
  const lastSpace = truncated.lastIndexOf(' ');
  return `${(lastSpace > 12 ? truncated.slice(0, lastSpace) : truncated).trim()}...`;
}

export function getMealDisplayName(meal) {
  const fallback = capitalizeLabel(meal?.meal_type || 'Meal');
  const notes = String(meal?.notes || '').trim();

  if (!notes) {
    return fallback;
  }

  const prefixes = [
    /^ai analysis:\s*/i,
    /^updated ai analysis:\s*/i,
    /^reanalysis with corrections:\s*/i,
    /^text description:\s*/i,
    /^estimated from:\s*/i,
  ];
  const genericNames = new Set([
    'unknown food',
    'could not analyze the image properly',
    'could not analyze the food description properly',
    'openai api key is not configured',
  ]);

  const segments = notes
    .split(/\n+/)
    .map((segment) => segment.trim())
    .filter(Boolean);

  for (const segment of segments) {
    const cleanedSegment = prefixes.reduce(
      (value, pattern) => value.replace(pattern, ''),
      segment,
    );
    const candidate = cleanedSegment
      .split(/[.!?](?:\s|$)/)[0]
      .replace(/\s+/g, ' ')
      .replace(/^[:\-–\s]+|[:\-–\s]+$/g, '')
      .trim();

    if (!candidate || genericNames.has(candidate.toLowerCase())) {
      continue;
    }

    return truncateLabel(capitalizeLabel(candidate));
  }

  return fallback;
}

const INSTALL_MESSAGE = 'Use your browser menu to install this app if the prompt is not available.';
let deferredInstallPrompt = null;

export function getAuthToken() {
  return window.localStorage.getItem('token');
}

export function setAuthToken(token) {
  window.localStorage.setItem('token', token);
}

export function clearAuthToken() {
  window.localStorage.removeItem('token');
}

export function isAuthenticated() {
  return Boolean(getAuthToken());
}

export function logout() {
  clearAuthToken();
  if (typeof window !== 'undefined') {
    window.location.href = 'login.html';
  }
}

export function authHeaders(headers = {}) {
  const token = getAuthToken();
  return token ? { ...headers, Authorization: `Bearer ${token}` } : headers;
}

export async function apiFetch(url, options = {}) {
  const {
    auth = true,
    redirectOnAuthError = true,
    headers = {},
    body,
    ...rest
  } = options;

  const resolvedHeaders = new Headers(auth ? authHeaders(headers) : headers);
  const requestOptions = { ...rest, headers: resolvedHeaders };

  if (body !== undefined) {
    if (body instanceof FormData) {
      requestOptions.body = body;
    } else if (typeof body === 'string') {
      requestOptions.body = body;
    } else {
      if (!resolvedHeaders.has('Content-Type')) {
        resolvedHeaders.set('Content-Type', 'application/json');
      }
      requestOptions.body = JSON.stringify(body);
    }
  }

  const response = await fetch(url, requestOptions);
  if (response.status === 401 && redirectOnAuthError) {
    clearAuthToken();
    if (!window.location.pathname.endsWith('login.html')) {
      window.location.href = 'login.html';
    }
  }

  return response;
}

export async function getJsonOrThrow(response, fallbackMessage = 'Request failed') {
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.detail || fallbackMessage);
  }
  return data;
}

export async function fetchCurrentUser() {
  const response = await apiFetch(API.currentUser);
  if (!response.ok) {
    return null;
  }
  return response.json();
}

export function showStatus(target, message = '', tone = 'info') {
  if (!target) {
    return;
  }

  target.textContent = message;
  target.dataset.tone = tone;
  target.hidden = !message;
}

export function formatDateTime(value) {
  if (!value) {
    return 'Unknown';
  }

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value));
}

export function formatTime(value) {
  if (!value) {
    return 'Unknown';
  }

  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value));
}

export function formatDayLabel(value) {
  return new Intl.DateTimeFormat(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  }).format(new Date(value));
}

export function getLocalDateKey(value) {
  const date = new Date(value);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function getDefaultDateRange(daysBack = 6) {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - daysBack);

  return {
    from: toDateInputValue(start),
    to: toDateInputValue(end),
  };
}

export function toDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function toDateTimeInputValue(value) {
  const date = new Date(value);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

export function localDateRangeToUtc(fromDate, toDate) {
  const from = fromDate ? new Date(`${fromDate}T00:00:00`) : null;
  const to = toDate ? new Date(`${toDate}T00:00:00`) : null;

  if (to) {
    to.setDate(to.getDate() + 1);
  }

  return {
    from: from ? from.toISOString() : null,
    to: to ? to.toISOString() : null,
  };
}

export function normalizeOptionalNumber(value) {
  if (value === '' || value === null || value === undefined) {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function bindQuickRangeButtons(buttons, onSelect) {
  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      const days = Number(button.dataset.days || 0);
      const range = getDefaultDateRange(days);
      onSelect(range);
    });
  });
}

export function setActiveNavLink() {
  const page = document.body.dataset.page;
  document.querySelectorAll('[data-nav]').forEach((link) => {
    link.classList.toggle('active', link.dataset.nav === page);
  });
}

export function toggleModal(modal, shouldOpen) {
  if (!modal) {
    return;
  }
  modal.hidden = !shouldOpen;
  document.body.classList.toggle('modal-open', shouldOpen);
}

export async function registerServiceWorker() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
    return;
  }

  try {
    await navigator.serviceWorker.register('/service-worker.js');
  } catch (error) {
    console.error('Service worker registration failed:', error);
  }
}

export function setupInstallPrompt() {
  const installButton = document.querySelector('[data-install-button]');
  if (!installButton) {
    return;
  }

  installButton.addEventListener('click', async () => {
    if (!deferredInstallPrompt) {
      showToast(INSTALL_MESSAGE);
      return;
    }

    deferredInstallPrompt.prompt();
    await deferredInstallPrompt.userChoice;
    deferredInstallPrompt = null;
    installButton.hidden = true;
  });

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    installButton.hidden = false;
  });

  window.addEventListener('appinstalled', () => {
    installButton.hidden = true;
    deferredInstallPrompt = null;
  });
}

export function showToast(message) {
  let toast = document.getElementById('appToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'appToast';
    toast.className = 'app-toast';
    document.body.appendChild(toast);
  }

  toast.textContent = message;
  toast.classList.add('visible');
  window.clearTimeout(showToast.timeoutId);
  showToast.timeoutId = window.setTimeout(() => {
    toast.classList.remove('visible');
  }, 3200);
}

showToast.timeoutId = null;

export async function setupPage({ requiresAuth = true } = {}) {
  setActiveNavLink();
  setupInstallPrompt();
  await registerServiceWorker();

  const logoutButtons = document.querySelectorAll('[data-logout]');
  logoutButtons.forEach((button) => button.addEventListener('click', logout));

  if (!requiresAuth) {
    return null;
  }

  if (!isAuthenticated()) {
    window.location.href = 'login.html';
    return null;
  }

  const user = await fetchCurrentUser();
  const greeting = document.querySelector('[data-user-greeting]');
  if (greeting && user) {
    greeting.textContent = user.name;
  }
  return user;
}
