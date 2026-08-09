const MOBILE_QUERY = '(max-width: 979px)';
const mobileMedia = window.matchMedia(MOBILE_QUERY);
let copyApplyScheduled = false;

function isCzech() {
  return (document.documentElement.lang || '').toLowerCase().startsWith('cs');
}

function setButtonText(button, text, ariaLabel = text) {
  if (!button) return;
  if (button.textContent !== text) button.textContent = text;
  if (button.getAttribute('aria-label') !== ariaLabel) button.setAttribute('aria-label', ariaLabel);
}

function applyCompactRangeCopy() {
  const mobile = mobileMedia.matches;
  const cs = isCzech();

  document.querySelectorAll('[data-days]').forEach((button) => {
    // Shared mobile copy owns these labels so common.js cannot expand them again
    // after setupPage() applies the generic desktop translations.
    button.removeAttribute('data-i18n');
    const days = button.dataset.days;
    const shortLabels = cs
      ? { '0': 'Dnes', '6': '7 dní', '29': '30 dní', '89': '90 dní' }
      : { '0': 'Today', '6': '7 days', '29': '30 days', '89': '90 days' };
    const longLabels = cs
      ? { '0': 'Dnes', '6': 'Posledních 7 dní', '29': 'Posledních 30 dní', '89': 'Posledních 90 dní' }
      : { '0': 'Today', '6': 'Last 7 days', '29': 'Last 30 days', '89': 'Last 90 days' };
    const label = mobile ? shortLabels[days] : longLabels[days];
    if (label) setButtonText(button, label, longLabels[days] || label);
  });

  const historyCustom = document.getElementById('historyToggleCustomRange');
  const metricsCustom = document.getElementById('metricsToggleCustomRange');
  historyCustom?.removeAttribute('data-i18n');
  metricsCustom?.removeAttribute('data-i18n');

  if (mobile) {
    setButtonText(historyCustom, cs ? 'Vlastní' : 'Custom', cs ? 'Vlastní datumy' : 'Custom dates');
    setButtonText(metricsCustom, cs ? 'Vlastní' : 'Custom', cs ? 'Vlastní datumy' : 'Custom dates');
  } else {
    setButtonText(historyCustom, cs ? 'Vlastní datumy' : 'Custom dates');
    setButtonText(metricsCustom, cs ? 'Vlastní datumy' : 'Custom dates');
  }
}

function applyHealthMobileCopy() {
  const cs = isCzech();
  const mobile = mobileMedia.matches;
  const coachHeading = document.getElementById('coachHeading');
  const refreshButton = document.getElementById('generateCoachButton');

  if (coachHeading) {
    const label = mobile
      ? (cs ? 'Co teď?' : 'What now?')
      : (cs ? 'Co mám udělat teď?' : 'What should I do now?');
    if (coachHeading.textContent !== label) coachHeading.textContent = label;
  }

  if (refreshButton) {
    setButtonText(
      refreshButton,
      mobile ? (cs ? 'Obnovit' : 'Refresh') : (cs ? 'Obnovit radu' : 'Refresh advice'),
    );
  }

  document.querySelectorAll('[data-health-days]').forEach((button) => {
    const raw = Number(button.dataset.healthDays || 0) + 1;
    setButtonText(button, cs ? `${raw} dní` : `${raw} days`);
  });
}

function applyResponsiveCopy() {
  applyCompactRangeCopy();
  applyHealthMobileCopy();
}

function scheduleResponsiveCopy() {
  if (copyApplyScheduled) return;
  copyApplyScheduled = true;
  requestAnimationFrame(() => {
    copyApplyScheduled = false;
    applyResponsiveCopy();
  });
}

function setupCopyGuard() {
  if (!document.body || !['history', 'metrics', 'health'].includes(document.body.dataset.page)) return;
  const observer = new MutationObserver(scheduleResponsiveCopy);
  observer.observe(document.body, { childList: true, subtree: true });
}

function syncAssistantViewport() {
  if (document.body?.dataset.page !== 'assistant') return;
  const viewport = window.visualViewport;
  const height = viewport?.height || window.innerHeight;
  const top = viewport?.offsetTop || 0;
  document.documentElement.style.setProperty('--assistant-vv-height', `${Math.round(height)}px`);
  document.documentElement.style.setProperty('--assistant-vv-top', `${Math.round(top)}px`);
}

function setupAssistantViewport() {
  if (document.body?.dataset.page !== 'assistant') return;

  const input = document.getElementById('assistantInput');
  if (!input) return;

  const markFocused = () => {
    document.body.classList.add('assistant-input-focused');
    requestAnimationFrame(syncAssistantViewport);
  };
  const markBlurred = () => {
    window.setTimeout(() => {
      document.body.classList.remove('assistant-input-focused');
      syncAssistantViewport();
    }, 120);
  };

  input.addEventListener('focus', markFocused);
  input.addEventListener('blur', markBlurred);
  window.visualViewport?.addEventListener('resize', syncAssistantViewport);
  window.visualViewport?.addEventListener('scroll', syncAssistantViewport);
  window.addEventListener('resize', syncAssistantViewport);
  syncAssistantViewport();
}

function init() {
  applyResponsiveCopy();
  setupCopyGuard();
  setupAssistantViewport();
  // Page modules call setupPage() asynchronously and may localize after DOMContentLoaded.
  // Re-apply once the initial render settles; the observer handles later dynamic updates.
  requestAnimationFrame(() => requestAnimationFrame(applyResponsiveCopy));
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init, { once: true });
} else {
  init();
}

window.addEventListener('food-reader:localechange', scheduleResponsiveCopy);

mobileMedia.addEventListener?.('change', () => {
  applyResponsiveCopy();
  syncAssistantViewport();
});
