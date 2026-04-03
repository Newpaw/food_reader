import {
  API,
  apiFetch,
  getJsonOrThrow,
  isAuthenticated,
  setAuthToken,
  setupPage,
  showStatus,
  t,
} from './common.js?v=20260403-8';

export function applyAuthMode(mode) {
  const normalizedMode = mode === 'register' ? 'register' : 'signin';
  const introEyebrow = document.querySelector('.auth-intro .eyebrow');
  const introHeading = document.querySelector('.auth-intro h1');
  const introSupport = document.querySelector('.auth-intro .panel-note');

  document.querySelectorAll('[data-auth-mode-toggle]').forEach((button) => {
    const isActive = button.dataset.authModeToggle === normalizedMode;
    button.classList.toggle('active', isActive);
    button.setAttribute('aria-selected', String(isActive));
  });

  document.querySelectorAll('[data-auth-mode-panel]').forEach((panel) => {
    panel.hidden = panel.dataset.authModePanel !== normalizedMode;
  });

  const activeToggle = document.querySelector(`[data-auth-mode-toggle="${normalizedMode}"]`);
  if (activeToggle && introEyebrow && introHeading && introSupport) {
    introEyebrow.textContent = t(activeToggle.dataset.authEyebrow);
    introHeading.textContent = t(activeToggle.dataset.authHeading);
    introSupport.textContent = t(activeToggle.dataset.authSupport);
  }

  return normalizedMode;
}

function bindAuthModeControls() {
  document.querySelectorAll('[data-auth-mode-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      applyAuthMode(button.dataset.authModeToggle);
    });
  });

  document.querySelectorAll('[data-auth-mode-link]').forEach((button) => {
    button.addEventListener('click', () => {
      applyAuthMode(button.dataset.authModeLink);
    });
  });

  applyAuthMode('signin');
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const status = document.getElementById('loginStatus');
  const submitButton = form.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  showStatus(status, t('login.signingIn'), 'info');

  try {
    const response = await apiFetch(API.login, {
      method: 'POST',
      auth: false,
      body: {
        email: form.email.value.trim(),
        password: form.password.value,
      },
    });
    const data = await getJsonOrThrow(response, 'Unable to sign in');
    setAuthToken(data.access_token);
    window.location.href = 'index.html';
  } catch (error) {
    showStatus(status, error.message, 'danger');
    submitButton.disabled = false;
  }
}


async function handleRegisterSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const status = document.getElementById('registerStatus');
  const submitButton = form.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  showStatus(status, t('login.registering'), 'info');

  try {
    const response = await apiFetch(API.register, {
      method: 'POST',
      auth: false,
      body: {
        name: form.name.value.trim(),
        email: form.email.value.trim(),
        password: form.password.value,
      },
    });
    await getJsonOrThrow(response, 'Unable to register');
    form.reset();
    showStatus(status, t('login.registered'), 'success');
  } catch (error) {
    showStatus(status, error.message, 'danger');
  } finally {
    submitButton.disabled = false;
  }
}


document.addEventListener('DOMContentLoaded', async () => {
  await setupPage({ requiresAuth: false });

  if (isAuthenticated()) {
    window.location.href = 'index.html';
    return;
  }

  bindAuthModeControls();
  document.getElementById('loginForm').addEventListener('submit', handleLoginSubmit);
  document.getElementById('registerForm').addEventListener('submit', handleRegisterSubmit);
});
